import admin
import collections
import datetime
import json
import os
import sys
try:
    import config
except ImportError:
    class config:
        DATABASE_URL = os.environ["DATABASE_URL"]
        SECRET_KEY = os.environ["SECRET_KEY"]
from gevent import monkey; monkey.patch_all(subprocess=True)
from flask import Flask, render_template, request, redirect, url_for, Response, send_from_directory, jsonify, flash
from flask_login import LoginManager, current_user, login_user, logout_user
import psycopg2.extras
from flask_sockets import Sockets
# Flask_Sockets 0.2.1 with Werkzeug 2.0.0+ breaks on all websocket connections due to
# a mismatch of routing rules. The websocket rules need to be identified correctly.
from werkzeug.routing import Rule

class Sockets(Sockets):
    def add_url_rule(self, rule, _, f, **options):
        self.url_map.add(Rule(rule, endpoint=f, websocket=True))

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.isoformat()

app = Flask(__name__)

sockets = Sockets(app)
ws_groups = collections.defaultdict(list)

socket_commands = {}

def socket_command(f):
    socket_commands[f.__name__] = f
    return f

def cache_bust(filename):
    stat = os.stat('static/' + filename)
    return f"{filename}?mtime={stat.st_mtime}"

app.jinja_env.globals.update(cache_bust=cache_bust)

login_manager = LoginManager()
login_manager.init_app(app)
app.config["SECRET_KEY"] = config.SECRET_KEY

@login_manager.user_loader
def load_user(id):
    return admin.User.from_id(int(id))

_conn = psycopg2.connect(config.DATABASE_URL)

@app.route("/")
def login_get():
    return render_template("login.html", user=current_user)

@app.route("/login", methods=["POST"])
def login_post():
    user = admin.User.from_credentials(
        request.form["email"],
        request.form["password"]
    )
    if user:
        login_user(user)
        return redirect('/contacts')
    else:
        flash("Invalid email or password")
        return redirect("/")

@app.route("/logout")
def logout():
    logout_user()
    return redirect("/")

@app.route("/contacts")
def contacts():
    if not (current_user and hasattr(current_user, 'user_level')):
        return redirect("/")
    if current_user.user_level == 3:
        ws_group = "mkcontacts"
    else:
        ws_group = "guest"# + str(current_user)
    state={}
    with _conn, _conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT id, fullname, email, phone FROM contacts ORDER BY fullname")
        state['contacts'] = [dict(c) for c in cur.fetchall()],
    return render_template("contacts.html", state=state, user=current_user, ws_group=ws_group)


@app.route('/deletecontact', methods=['POST'])
def deletecontact():
    if (current_user.user_level != 3):
        return "Unauthorized", 401
    data = request.json
    state = {}
    print("data is {0} and id is {1}".format(data, data['id']))
    with _conn, _conn.cursor() as cur:
        cur.execute("DELETE FROM contacts WHERE id = %s", (data['id'],))
    with _conn, _conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT id, fullname, email, phone FROM contacts ORDER BY fullname")
        state['contacts'] = cur.fetchall()
    update_sockets("mkcontacts")
    return jsonify(state)

@app.route('/newcontact', methods=['POST'])
def newcontact():
    if (current_user.user_level != 3):
        return "Unauthorized", 401
    data = request.json
    contact = json.loads(data['form'])
    #if not json['name'] in ['fullname','email', 'phone']: return
    # for now ignore other values
    # TODO maybe sanitize https://pathvalidate.readthedocs.io is one way
    #we don't want to create multiple contacts for each field
    #probably want to create the contact no matter which field received
    #first. also how do you deal with overlapping requests?
    #the cheap way is to just use a submit button. Let's
    #start with that.
    state = {}
    try:
        with _conn, _conn.cursor() as cur:
            cur.execute("""INSERT INTO contacts (fullname, email, phone, web)
            VALUES (%s, %s, %s, %s) RETURNING id""", (contact['fullname'], contact['email'], contact['phone'], contact['web']))
            state['item_id'] = cur.fetchone()[0]
    except psycopg2.errors.CheckViolation as e:
        state["error"] = str(e)
        message = str(e)
        if "at_least_one_contact_point" in message:
            message = "Enter at least one contact method."
        update_sockets("mkcontacts", {"error": message, "cmd": "update"})
        return jsonify(state)
    with _conn, _conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT id, fullname, email, phone, web FROM contacts ORDER BY fullname")
        state['contacts'] = cur.fetchall()
    update_sockets("mkcontacts")
    return jsonify(state)

def get_state(group):
    state = {}
    with _conn, _conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT id, fullname, email, phone, web FROM contacts ORDER BY fullname")
        state['contacts'] = cur.fetchall()
    return state

def update_sockets(group, state = None):
    if state is None:
        try:
          state = { **get_state(group), "cmd": "update" } # "unpack" (spread) and add "cmd"
        except Exception as e:
          state = { "error": str(e) }
    state = json.dumps(state, cls=DateTimeEncoder)
    for ws in ws_groups[group][:]:
        # [:] "slice" makes a copy of the list so we can iterate
        # over it without getting errors when we modify the original.
        try:
            ws.send(state)
        except flask_sock.ConnectionClosed:
            ws_groups[group].remove(ws)

@sockets.route("/ws")
def websocket(ws):
    """
    Websocket endpoint to continuously listen for and emit data.
    "ws" is an http websocket request (continuous bidirectional messaging)
    ws://
    """
    # A ws group is a collection of sockets that get
    # the same information. In this case...
    group = None
    try:
        while True:
            message = ws.receive()
            if type(message) is not str:
                continue  # Be VERY strict here, for safety
            try:
                message = json.loads(message)
            except json.JSONDecodeError:
                continue
            if type(message) is not dict:
                continue  # Again, very strict
            if "cmd" not in message:
                continue
            # Init is called automatically on connection
            if message["cmd"] == "init":  # Initialize a new socket
                if message["type"] != "mkcontacts":
                    continue
                if "group" not in message:
                    continue
                group = message["group"]
                ws_groups[group].append(ws)
            if message["cmd"] == "init" or message["cmd"] == "refresh":
                state = { "cmd": "update",
                    **get_state(group)
                }
                ws.send(json.dumps(state, cls=DateTimeEncoder))
            if message["cmd"] in socket_commands:
                socket_commands[message["cmd"]](message)
    finally:
        if group is not None:
            ws_groups[group].remove(ws)

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)
    # Load us up using gunicorn, configured via the Procfile
    with open("Procfile") as f: cmd = f.read().strip().replace("web: ", "")
    if "PORT" not in os.environ: os.environ["PORT"] = "8900" # hack - pick a different default port
    sys.argv = cmd.split(" ")[1:] # TODO: Split more smartly
    from gunicorn.app.wsgiapp import run; run()
    # # If we're running with gunicorn, we need to start the websocket server
    # # So swap comment on previous block with the next one

    # import logging
    # logging.basicConfig(level=logging.INFO)
    # # Load us up using gunicorn, configured via the Procfile
    # with open("Procfile") as f: cmd = f.read().strip().replace("web: ", "")
    # if "PORT" not in os.environ: os.environ["PORT"] = "5000" # hack - pick a different default port
    # sys.argv = cmd.split(" ")[1:] # TODO: Split more smartly
    # from gunicorn.app.wsgiapp import run; run()

    # Test mode, when not running with gunicorn
    # app.run(debug=True)
    app.run(debug=True, port=8900)
    # # If we're running with gunicorn, we need to start the websocket server
    # # So swap comment on following block with the next one
