# I borrowed the format for this file from Finance. However, I used a different database, added new routes, and edited the index and register routes.
# The only routes I kept unchanged from Finance are login and logout.

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
import datetime
import requests
import yagmail

from helpers import apology, login_required

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///cryptopulse.db")

# Configure yagmail to use CryptoPulse's Gmail accout
yag = yagmail.SMTP('cryptopulse.updates@gmail.com', 'cs50finalproject')

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    """Display current queries and allow user to delete each query"""
    
    # User reached route via POST (as by submitting a form via POST), remove the query the user requested to remove
    if request.method == "POST":

        # Select id of the query from the request
        id = request.form.get("delete")

        # Confirm that query is user's query before deleting
        user_id = db.execute("SELECT user_id FROM queries WHERE id=?", id)
        user_id = user_id[0]["user_id"]
        if user_id != session["user_id"]:
            return apology("cannot delete other users' queries", 400)
        
        # Delete query from the database
        db.execute("DELETE FROM queries WHERE id=?", id)

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        # Get all of the user's queries from the queries table
        queryInfo = db.execute(
            "SELECT server, channel, keyword, id FROM queries WHERE user_id = ?", session["user_id"])
        
        # Create a list of dictionaries, where each dictionary represents the information for each of the user's queries
        queries = []
        for query in range(len(queryInfo)):
            # Get server name
            server = queryInfo[query]["server"]

            # Get channel name
            channel = queryInfo[query]["channel"]

            # Get the keyword
            keyword = queryInfo[query]["keyword"]

            # Get the id of the query
            id = queryInfo[query]["id"]

            # Add dictionary with information to the list
            queries.append({"server": server, "channel": channel, "keyword": keyword, "id": id})
        
        # Display current user's queries
        return render_template("/index.html", queries=queries)
    

@app.route("/add", methods=["GET", "POST"])
@login_required
def add():
    """Add a query for updates"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure the user submitted a channel id, keyword, server name, and channel name
        if not request.form.get("channel_id") or not request.form.get("keyword") or not request.form.get("server") or not request.form.get("channel"):
            return apology("must provide a channel id, keyword, server name, and channel name", 400)

        # Ensure the channel id is valid (18 characters and are digits)
        channel_id = request.form.get("channel_id")
        id_length = len(channel_id)
        if id_length != 18 or not channel_id.isdigit():
            return apology("valid channel ids have 18 digits", 400)

        # Ensure user actually has access to channel (authorization token and channel ID return something)
        token = db.execute("SELECT token FROM users WHERE id=?", session["user_id"])
        token = token[0]["token"]
        headers = {'authorization': token}
        try:
            r = requests.get(f"https://discord.com/api/v9/channels/{channel_id}/messages?limit=1", headers=headers)
        except:
            return apology("an error has occurred, please try again", 400)
        r = str(r)
        if r != "<Response [200]>":
            # Alert the user if they do not have access
            return apology("channel id invalid or you do not have access to this channel", 400)

        # Add the query to the database
        db.execute("INSERT INTO queries (user_id, channel_id, keyword, server, channel) VALUES (?, ?, ?, ?, ?)", session["user_id"], 
                   channel_id, request.form.get("keyword"), request.form.get("server"), request.form.get("channel"))

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("add_query.html")


@app.route("/update_contact", methods=["GET", "POST"])
@login_required
def update_contact():
    """Update a user's contact information"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure email was submitted
        if not request.form.get("email"):
            return apology("must provide email", 400)

        # Ensure email isn't already in use
        email = request.form.get("email")
        emails = db.execute("SELECT email FROM users")
        for user in range(len(emails)):
            if email.lower() == emails[user]["email"].lower():
                return apology("sorry, that email is already in use", 400)

        # Validate email address is valid by sending welcome email
        try:
            # Get current email
            old_email = db.execute("SELECT email FROM users WHERE id=?", session["user_id"])
            old_email = old_email[0]["email"]
            yag.send(email, 'Updating Your Contact Information', f"You have updated your email from {old_email} to {email}.")
        except:
            return apology("enter a valid email address", 400)

        # Update user's email
        db.execute("UPDATE users SET email=? WHERE id=?", email, session["user_id"]) 

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        # Retrieve the user's current contact information
        current_email = db.execute("SELECT email FROM users WHERE id=?", session["user_id"])
        current_email = current_email[0]["email"]
        return render_template("update_contact.html", current_email = current_email)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username, password, Discord token, and email were submitted
        if not request.form.get("username") or not request.form.get("password") or not request.form.get("token") or not request.form.get("email"):
            return apology("must provide a username, password, discord token, and email", 400)

        # Ensure username doesn't already exist
        username = request.form.get("username")
        usernames = db.execute("SELECT username FROM users")
        for user in range(len(usernames)):
            if username.lower() == usernames[user]["username"].lower():
                return apology("sorry, that username already exists", 400)
        
        # Ensure password and confirmation match
        if request.form.get("password") != request.form.get("confirmation"):
            return apology("password and confirmation must match", 400)

        # Ensure email isn't already in use
        email = request.form.get("email")
        emails = db.execute("SELECT email FROM users")
        for user in range(len(emails)):
            if email.lower() == emails[user]["email"].lower():
                return apology("sorry, that email is already in use", 400)

        # Ensure Discord token is not already in use
        token = request.form.get("token").replace(" ", "") # Removes all whitespaces - prevents users from adding spaces to tokens already in use to bypass this check
        usernames = db.execute("SELECT token FROM users")
        for user in range(len(usernames)):
            if token == usernames[user]["token"]:
                return apology("sorry, that token is already in use", 400)

        # Validate Discord token by using Discord's API to make sure user has joined the verification server
        headers = {'authorization': token}
        verification_channel = 916150524519264339
        try:
            r = requests.get(f"https://discord.com/api/v9/channels/{verification_channel}/messages?limit=1", headers=headers)
        except:
            return apology("an error has occurred, please try again", 400)
        r = str(r)
        if r != "<Response [200]>":
            # If the token is not a valid token, alert the user
            if r == "<Response [401]>":
                return apology("invalid discord token", 400)
            # If the token is valid, but the user has not joined the verification server, alert the user
            elif r == "<Response [403]>":
                return apology("valid discord token, but associated account has not joined the verification server", 400)
            # Some other error
            else:
                return apology("unable to validate token, make sure you are using a valid token and have joined the verification server", 400)

        # Validate email address is valid by sending welcome email
        try:
            yag.send(email, 'Welcome to CryptoPulse!', f"Welcome to CryptoPulse, {username}!")
        except:
            return apology("enter a valid email address", 400)

        # Add user to the database
        hashed_password = generate_password_hash(request.form.get("password"))
        id = db.execute("INSERT INTO users (username, hash, token, email) VALUES (?, ?, ?, ?)", username, hashed_password, token, email)

        # Log the user in
        session["user_id"] = id

        # Redirect user to home page
        return redirect("/")
    
    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
    