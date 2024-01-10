import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

from datetime import datetime

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""

    # Query database for which stocks the user owns, the numbers of shares owned
    rows = db.execute("SELECT stock_symbol, SUM(shares) AS total_shares FROM transactions WHERE id = ? GROUP BY stock_symbol", int(session["user_id"]))

    # Create an empty list
    my_list = []

    # The user’s current cash balance along with a grand total (i.e., stocks’ total value plus cash).
    total_value = 0

    for i in range(len(rows)):
        symbol = rows[i]["stock_symbol"]
        shares = int(rows[i]["total_shares"])

        # Find the current price of the stock
        value = lookup(symbol)
        unit_price = float(value["price"])
        unit_price_formatted = usd(unit_price)

        # Calculate the total price and round to two decimal places
        total_price = round(unit_price * shares, 2)

        total_price_formatted = usd(total_price)

        # Add the total_price to total_value
        total_value += total_price

        # Create an empty dictionary
        my_dict = {}

        # Add values to the dictionary
        my_dict['symbol'] = symbol
        my_dict['shares'] = shares
        my_dict['price'] = unit_price_formatted
        my_dict['total_price'] = total_price_formatted

        # Add the dictionary to the list
        my_list.append(my_dict)

    # Query database for cash
    rows = db.execute("SELECT * FROM users WHERE id = ?", int(session["user_id"]))
    cash_value = float(rows[0]["cash"])

    # Add the cash_value to total_value
    total_value += cash_value

    return render_template("index.html", values=my_list, cash=usd(cash_value), total=usd(total_value))


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure symbol was submitted
        if not request.form.get("symbol"):
            return apology("missing symbol", 400)

        # Ensure shares was submitted
        elif not request.form.get("shares"):
            return apology("missing shares", 400)

        # Ensure shares was a positive integer or 0
        # isdigit() returns true if a string contains a positive integer or 0
        elif (not request.form.get("shares").isdigit()):
            return apology("shares must be a positive inteegr", 400)

        # Ensure shares was a positive integer
        elif int(request.form.get("shares")) == 0:
            return apology("shares must be a positive inteegr", 400)

        # Ensure symbol was valid
        elif lookup(request.form.get("symbol")) is None:
            return apology("invalid symbol", 400)

        else:
            value = lookup(request.form.get("symbol"))
            unit_price = float(value["price"])
            shares = int(request.form.get("shares"))
            total_price = unit_price * shares

            # Query database for cash
            rows = db.execute("SELECT * FROM users WHERE id = ?", int(session["user_id"]))

            cash = rows[0]["cash"]

            if cash < total_price:
                return apology("can't afford", 400)

            else:
                cash_left = cash - total_price

                # Get the current date and time
                current_datetime = datetime.now()

                # INSERT the new transaction into transactions
                db.execute("INSERT INTO transactions VALUES (?)", (session["user_id"], "buy", value["symbol"], shares, unit_price, total_price, current_datetime.year, current_datetime.month, current_datetime.day, current_datetime.hour, current_datetime.minute, current_datetime.second))

                # UPDATE the cash value in users
                update_query = f"UPDATE users SET cash = '{cash_left}' WHERE id = {session['user_id']}"
                db.execute(update_query)

                # Redirect the user to the home page
                return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("buy.html")

@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    # Query database for history of transactions
    rows = db.execute("SELECT stock_symbol, shares, price, year, month, day, hour, minute, second FROM transactions WHERE id = ?", int(session["user_id"]))

    # Create an empty list
    my_list = []

    for i in range(len(rows)):
        symbol = rows[i]["stock_symbol"]
        shares = rows[i]["shares"]
        price_formatted = usd(rows[i]["price"])
        year = rows[i]["year"]
        month = rows[i]["month"]
        day = rows[i]["day"]
        hour = rows[i]["hour"]
        minute = rows[i]["minute"]
        second = rows[i]["second"]

        time_transacted = str(year) + "-" + str(month) + "-" + str(day) + " " + str(hour) + ":" + str(minute) + ":" + str(second)

        # Convert the string to a datetime object
        datetime_object = datetime.strptime(time_transacted, "%Y-%m-%d %H:%M:%S")

        # Format the datetime object as a string with leading zeros
        time_transacted_formatted = datetime_object.strftime("%Y-%m-%d %H:%M:%S")

        # Create an empty dictionary
        my_dict = {}

        # Add values to the dictionary
        my_dict['symbol'] = symbol
        my_dict['shares'] = shares
        my_dict['price'] = price_formatted
        my_dict['transacted'] = time_transacted_formatted

        # Add the dictionary to the list
        my_list.append(my_dict)

    return render_template("history.html", values=my_list)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

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


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure symbol was submitted
        if not request.form.get("symbol"):
            return apology("missing symbol", 400)

        else:
            value = lookup(request.form.get("symbol"))

            if value is None:
                return apology("invalid symbol", 400)
            else:
                price_formatted = usd(value["price"])

                return render_template("quoted.html", name=value["name"], symbol=value["symbol"], price=price_formatted)

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("quote.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        else:
            # Query database for username
            rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

            # Ensure the username is not already exists
            if len(rows) == 1:
                return apology("Username is not available", 400)

            # Ensure password was submitted
            elif not request.form.get("password"):
                return apology("missing password", 400)

            # Ensure passwords were matched
            elif (request.form.get("password")) != (request.form.get("confirmation")):
                return apology("passwords don't match", 400)

            else:
                # INSERT the new user into users
                db.execute("INSERT INTO users (username, hash) VALUES (?)", (request.form.get("username"), generate_password_hash(request.form.get("password"), method='pbkdf2', salt_length=16)))

                # Query database for username
                rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

                # Log User In
                session["user_id"] = rows[0]["id"]

                return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure symbol was submitted
        if not request.form.get("symbol"):
            return apology("missing symbol", 400)

        # Ensure shares was submitted
        elif not request.form.get("shares"):
            return apology("missing shares", 400)

        # Ensure shares was a positive integer or 0
        # isdigit() returns true if a string contains a positive integer or 0
        elif (not request.form.get("shares").isdigit()):
            return apology("shares must be a positive inteegr", 400)

        # Ensure shares was a positive integer
        elif int(request.form.get("shares")) == 0:
            return apology("shares must be a positive inteegr", 400)

        # Ensure symbol was valid
        elif lookup(request.form.get("symbol")) is None:
            return apology("invalid symbol", 400)

        else:
            value = lookup(request.form.get("symbol"))
            unit_price = float(value["price"])
            shares = int(request.form.get("shares"))
            total_price = unit_price * shares

            # Query database for cash
            rows = db.execute("SELECT * FROM users WHERE id = ?", int(session["user_id"]))

            cash = rows[0]["cash"]

            # Query database for shares
            rows = db.execute("SELECT SUM(shares) AS total_count FROM transactions WHERE stock_symbol = ?", value["symbol"])
            total_count = int(rows[0]["total_count"])

            if total_count < shares:
                return apology("too many shares", 400)

            else:
                cash_left = cash + total_price

                # Get the current date and time
                current_datetime = datetime.now()

                # Set the shares as negative number for selling
                shares = - shares

                # INSERT the new transaction into transactions
                db.execute("INSERT INTO transactions VALUES (?)", (session["user_id"], "sell", value["symbol"], shares, unit_price, total_price, current_datetime.year, current_datetime.month, current_datetime.day, current_datetime.hour, current_datetime.minute, current_datetime.second))

                # UPDATE the cash value in users
                update_query = f"UPDATE users SET cash = '{cash_left}' WHERE id = {session['user_id']}"
                db.execute(update_query)

                # Redirect the user to the home page
                return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        # Query database for symbol which has shares greater than 0
        rows = db.execute("SELECT stock_symbol AS symbol, SUM(shares) AS total_shares FROM transactions WHERE id= ? GROUP BY symbol HAVING total_shares > 0", int(session["user_id"]))

        # Create an empty list
        my_list = []

        for i in range(len(rows)):
            my_list.append(rows[i]["symbol"])
        return render_template("sell.html", values=my_list)
