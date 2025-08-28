import admin
import os
from flask import Flask, render_template, request, redirect, url_for, Response, send_from_directory, jsonify, flash
from flask_login import LoginManager, current_user, login_user, logout_user
import psycopg2.extras
try:
    import config
except ImportError:
    class config:
        DATABASE_URL = os.environ["DATABASE_URL"]
        SECRET_KEY = os.environ["SECRET_KEY"]

app = Flask(__name__)


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
    contacts=[]
    with _conn, _conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT id, fullname, email, phone FROM contacts ORDER BY fullname")
        contacts=cur.fetchall()
    return render_template("contacts.html", user=current_user, contacts=[dict(c) for c in contacts])

if __name__ == '__main__':
    app.debug = True
    app.run(port=8900)
