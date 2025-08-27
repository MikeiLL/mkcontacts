import psycopg2
import clize
import utils
import os
from flask_login import UserMixin
from dataclasses import dataclass

try:
    import config
except ImportError:
    class config:
        DATABASE_URL = os.environ["DATABASE_URL"]

_conn = psycopg2.connect(config.DATABASE_URL)

_commands = []
def cmdline(f):
    _commands.append(f)
    return f



@dataclass
class User(UserMixin):
    id: int
    displayname: str
    email: str
    user_level: int

    @classmethod
    def from_id(cls, id, password=None):
        with _conn, _conn.cursor() as cur:
            cur.execute("SELECT " + ", ".join(cls.__dataclass_fields__) + " FROM users WHERE id=%s", (id,))
            data = cur.fetchone()
        if not data: return None
        return cls(*data)

    @classmethod
    def from_credentials(cls, login, password):
        with _conn, _conn.cursor() as cur:
            cur.execute("SELECT " + ", ".join(cls.__dataclass_fields__) + ", password FROM users WHERE email=%s", (login.lower(),),)
            data = cur.fetchone()
        if not data: return None
        if not utils.check_password(password, data[-1]):
            # Passwords do not match. Pretend the user doesn't exist.
            # Note that even if the user _really_ doesn't exist, we still
            # do a password verification. This helps protect against
            # timing-based attacks.
            return None
        return cls(*data[:-1])

@cmdline
def create_user(displayname, email, password):
    """Create a new user, return the newly-created ID

    username: Name for the new user

    email: Email address (must be unique)

    password: Clear-text password
    """
    email = email.lower()
    with _conn, _conn.cursor() as cur:
        pwd = utils.hash_password(password)
        try:
            cur.execute("INSERT INTO users (displayname, email, password) VALUES (%s, %s, %s) RETURNING id", \
                                            (displayname, email, pwd))
            return cur.fetchone()
        except psycopg2.IntegrityError as e:
            return "That didn't work too well because: %s Maybe you already have an account or \
                    someone else is using the name you requested."%e

@cmdline
def set_user_password(email, password):
    """Change a user's password (administratively) - returns None on success, or error message

    email: User email address

    password: New password
    """
    email = email.lower()
    with _conn, _conn.cursor() as cur:
        pwd = utils.hash_password(password)
        cur.execute("SELECT id FROM users WHERE email=%s", (email, ),)
        rows=cur.fetchall()
        if not rows:
            print("No such user")
        else:
            cur.execute("update users set password=%s where id=%s", (pwd, rows[0][0]))

@cmdline
def tables(*, confirm=False):
    """Update tables based on create_table.sql

    confirm: If omitted, will do a dry run.
    """
    tb = None; cols = {}; coldefs = []
    with _conn, _conn.cursor() as cur:
        def finish():
            if tb and (coldefs or cols):
                if is_new == "": query = "create table "+tb+" ("+", ".join(coldefs)+")"
                else:
                    parts = coldefs + ["drop "+c for c in cols]
                    query = "alter table "+tb+" "+", ".join(parts)
                if confirm: cur.execute(query)
                else: print(query)
        for line in open("create_table.sql"):
            line = line.rstrip()
            if line == "" or line.startswith("--"): continue
            # Flush-left lines are table names
            if line == line.lstrip():
                finish()
                tb = line; coldefs = []
                cur.execute("select column_name, data_type from information_schema.columns where table_name=%s", (tb,))
                cols = {row[0]:row[1] for row in cur}
                # New tables want a series of column definitions; altered tables want any added
                # columns prefixed with the command "add".
                is_new = "add" if cols else ""
                continue
            # Otherwise, it should be a column definition, starting (after whitespace) with the column name.
            colname, defn = line.strip().split(" ", 1)
            if colname in cols:
                # Column already exists. Check its data type.
                # Assume that all data types are unique within one space-delimited word. For example,
                # the data type "double precision" will be treated as "double".
                # NOTE: You may not be able to use this to change a data type to or from 'serial',
                # since that's not (strictly speaking) a data type.
                want_type = defn.split(" ", 1)[0]
                want_type = {
                    "double": "double precision",
                    "serial": "integer", "int": "integer",
                    "varchar": "character varying",
                    "timestamptz": "timestamp with time zone",
                }.get(want_type, want_type)
                have_type = cols[colname]
                if want_type != have_type:
                    coldefs.append("alter %s set data type %s" % (colname, want_type))
                del cols[colname]
            else:
                # Column doesn't exist. Add it!
                # Note that we include a newline here so that a comment will be properly terminated.
                # If you look at the query, it'll have all its commas oddly placed, but that's okay.
                coldefs.append("%s %s %s\n" % (is_new, colname, defn))
        finish()
    if not confirm: print("Add --confirm to actually make the changes.")

if __name__ == "__main__":
    clize.run(*_commands, description="Coming soon... from utils.py")
