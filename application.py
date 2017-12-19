## Litterbug
## Application to track plastic bag usage

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from passlib.apps import custom_app_context as pwd_context
from tempfile import gettempdir
from passlib.apps import custom_app_context as pwd_context
from collections import OrderedDict

from helpers import *
from categories import categories as dictionary

import sys
import uuid
import math

# Define Global Variables
avg_bag_weight = 35.7


points_per_bag = 10
# Defined for the Rewards Program

# configure application
app = Flask(__name__)

# ensure responses aren't cached
if app.config["DEBUG"]:
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response

# custom filter
app.jinja_env.filters["usd"] = usd

# configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = gettempdir()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# configure CS50 Library to use SQLite database
db = SQL("sqlite:///litterbug.db")

@app.route("/")
@login_required
def index():
    """Render homepage for application."""
    
    # retrieve user's point balance
    rows = db.execute("SELECT username, points, total_saved, total_used FROM users WHERE id = :id", id= session["user_id"] )
    
    # validate user in database
    if not rows:
        return render_template("apology.html", message = "Missing user")
    
    # extract data points from user's record
    username = rows[0]["username"]
    points = rows[0]["points"]
    total_saved = rows[0]["total_saved"]
    total_used = rows[0]["total_used"]
    
    # retrieve user's current rewards level
    reward = db.execute("SELECT level_name, reward_id, rewards_txt, reward FROM rewards WHERE :points between min_points and max_points", points = points)
    level = reward[0]["level_name"]
    reward_text = reward[0]["rewards_txt"]
    current_reward_id = reward[0]["reward_id"]
    reward = reward[0]["reward"]
    
    # retrieve user's next possible rewards level
    next_reward = db.execute("SELECT level_name, min_points FROM rewards WHERE reward_id = :reward_id +1", reward_id = current_reward_id)
    next_reward_points = next_reward[0]["min_points"]
    next_reward_level = next_reward[0]["level_name"]
    point_difference = next_reward_points - points
    
    # retrieve random advise for plastic bag savings
    advise_text = db.execute("SELECT advise FROM advise ORDER BY RANDOM() LIMIT 1;")
    advise = advise_text[0]["advise"]
    
    return render_template("index.html", username = username, points = points, total_saved = total_saved, total_used = total_used, level = level, point_difference = point_difference, next_reward_level = next_reward_level, reward_text = reward_text,  reward = reward, advise = advise )

@app.route("/grocery_cart_new", methods=["GET", "POST"])
@login_required
def grocery_cart_new():
    """ Generate Initial Grocery Cart ID"""
    
    if request.method == "GET":
        
        # commit new cart to database 
        id = db.execute("INSERT INTO grocery_cart (user_id) VALUES (:user_id)", user_id= session["user_id"])
        
        # generate cart_id
        session["cart_id"] = id 
        
        return redirect(url_for("grocery_cart"))


@app.route("/grocery_cart", methods=["GET", "POST"])
@login_required
def grocery_cart():
    """ Add Items to Grocery Cart ID"""
    
    if request.method == "GET":
        
        # import and order alphabetically items from dictionary
        cat = OrderedDict(sorted(dictionary.items(), key=lambda t: t[0]))
        
        # sustain card_id
        cart_id = session["cart_id"]
        
        # calculate distinct items in cart
        items = db.execute("SELECT COUNT(DISTINCT id) AS count FROM grocery_list_detail WHERE cart_id = :cart_id", cart_id = cart_id)
        num_items = items[0]["count"]
        
        return render_template("grocery_cart.html", cat=cat , num_items = num_items)
        
@app.route("/grocery_entry", methods=["GET", "POST"])
@login_required
def grocery_entry():
    """ Retrieve and Log Grocery Item"""
    
    if request.method == "POST":
        
        # validate form for completeness
        if not request.form.get("item"):
            return render_template("apology.html", message = "Please enter a specific item.")
        elif not request.form.get("qty"):
            return render_template("apology.html", message = "Please enter a quantity")
        elif not request.form.get("item") and not request.form.get("qty"):
            return render_template("apology.html", message = "Please enter an item and quantity.")
         
            
        # retrieve item classification details
        classification = request.form.get("classification")
        sub_group = request.form.get("sub_group")

        # look up item weight
        weight_lookup = db.execute("SELECT weight FROM food_inventory WHERE classification = classification and sub_group = sub_group")
        weight = int(weight_lookup[0]["weight"])
        
        # validate data type of quantity
        try:
            qty = int(request.form.get("qty"))
        except:
            return render_template("apology.html", message = "Please enter the quantity as an integer. Ex) 3 ")
        
        if qty <= 0:
            return render_template("apology.html", message = "Please enter a valid quantity as an integer greater than 0.")
        
        # commit item to data base
        db.execute("INSERT INTO grocery_list_detail (user_id, classification, sub_group, item, weight, qty, total_weight, cart_id) VALUES (:user_id, :classification, :sub_group, :item, :weight, :qty, :total_weight, :cart_id)", user_id= session["user_id"] , classification = classification, sub_group = sub_group, item = request.form.get("item"), weight = weight, qty = qty, total_weight = weight * qty, cart_id = session["cart_id"])
        
        # update grocery cart
        db.execute("UPDATE 'grocery_cart' SET total_items = total_items + 1, total_qty = total_qty + :qty, total_weight = total_weight + :weight WHERE cart_id = :cart_id", cart_id = session["cart_id"], qty = qty, weight = weight)
        
        # confirm success
        flash("Entry successful!")
        return redirect(url_for("grocery_cart"))
        
    # GET
    else:
        
        # retrieve classification of grocery item
        classification = request.args.get("classification")
        if not classification:
            return render_template("apology.html", message = "Missing Classification") 
        
        # retrieve sub_group of grocery item
        sub_group = request.args.get("sub_group")
        if not sub_group:
            return render_template("apology.html", message ="Missing Group")
        
        return render_template("grocery_entry.html", classification = classification, sub_group = sub_group)
        
@app.route("/bag_inquiry", methods = ["GET","POST"])
@login_required
def bag_inquiry():
    """Inquire if user bag status"""
    
    if request.method == "GET":
        return render_template("bag_inquiry.html")
    elif request.method == "POST":
        
        # retrieve user bag status
        bag_status = request.form.get("bag_status")
        
        # retrieve cart metrics
        cart = db.execute("SELECT * from grocery_cart WHERE cart_id = :cart_id", cart_id = session["cart_id"])
        
        # extract data points for cart
        total_items = cart[0]["total_items"]
        total_qty = cart[0]["total_qty"]
        total_weight = cart[0]["total_weight"]
        bags = cart[0]["total_bags"]
        total_bags = math.ceil((total_weight/avg_bag_weight))
        
        # initialize bag variables
        total_bags_saved = 0
        total_bags_used = 0
        
        # calculate total bags based on user's bag status
        if bag_status == "Yes":
            total_bags_saved = total_bags
            
            # calculate total points
            total_points = total_bags * points_per_bag
            
            # retrieve fact with positive sentiment
            fact = db.execute("SELECT fact FROM facts WHERE sentiment = 'positive' ORDER BY RANDOM() LIMIT 1;")
            fact_text = "Thanks for helping save the enviornment"
            
        elif bag_status == "No":
            total_bags_used = total_bags
            
            # calculate total points
            total_points = -(total_bags * points_per_bag)
            
            # retrieve fact with negative sentiment
            fact = db.execute("SELECT fact FROM facts WHERE sentiment = 'negative' ORDER BY RANDOM() LIMIT 1;")
            fact_text = "Did you know:"
         
        # extract from row of data    
        fact = fact[0]["fact"]
        
        
        # update cart record
        db.execute("UPDATE 'grocery_cart' SET total_bags = :total_bags, total_qty = :total_qty, total_points = :total_points WHERE cart_id = :cart_id", cart_id = session["cart_id"], total_qty = total_qty, total_bags = total_bags, total_points = total_points)
        
        # update user record
        db.execute("UPDATE 'users' SET points = points + :total_points, total_saved = total_saved + :total_bags_saved, total_used = total_used + :total_bags_used WHERE id = :user_id", user_id = session["user_id"], total_points = total_points, total_bags_saved = total_bags_saved, total_bags_used = total_bags_used)
        
        return render_template("grocery_cart_total.html", total_items = total_items, total_qty = total_qty, total_weight = total_weight, total_bags_saved = total_bags_saved, total_bags_used = total_bags_used, total_points = total_points, fact = fact, fact_text = fact_text)
 

@app.route("/cart_history", methods = ["GET", "POST"])
@login_required
def cart_history():
    """Show history of grocery carts."""
    
    if request.method == "GET":
        
        # retrieve transaction data
        cart_transactions = db.execute("SELECT cart_id, CASE WHEN total_points < 0 THEN 'USED' ELSE 'SAVED' END AS bag_status, total_items, total_qty, total_weight, total_bags, total_points, strftime('%m-%d-%Y', purchased) AS purchase_date FROM grocery_cart WHERE user_id = :id ORDER BY purchased ASC", id= session["user_id"])
        
        # calculate transaction totals
        totals = db.execute("SELECT COUNT(DISTINCT cart_id) as total_carts, SUM(total_items) as total_items, SUM(total_qty) as total_qty, SUM(total_weight) as total_weight, SUM(total_bags) as total_bags, sum(total_points) as total_points FROM grocery_cart WHERE user_id = :id", id= session["user_id"])
        
        return render_template("cart_history.html", cart_transactions = cart_transactions, totals = totals)
    
    elif request.method == "POST":
        
        # retrieve cart_id
        cart_id = request.form.get("cart_id")
        
        # retrieve items in cart
        items = db.execute("SELECT * from grocery_list_detail WHERE cart_id = :cart_id", cart_id = cart_id)
        
        return render_template("single_cart.html", items = items)
        
@app.route("/rewards_structure")
@login_required
def rewards_structure():
    """Display Rewards Structure."""
  
    # retrieve all reward information
    rewards = db.execute("SELECT min_points, level_name, (CASE WHEN reward IS NULL THEN '' ELSE reward END)  AS reward FROM rewards ORDER BY id")

    return render_template("rewards_structure.html", rewards = rewards)
     
@app.route("/single_cart", methods = ["GET"])
@login_required
def single_cart():
    """Show history of single grocery cart."""
    
    if request.method == "GET":
        
        # retrieve cart_id
        cart_id = request.args.get("cart_id")
        
        # retrieve items associated to cart_id
        items = db.execute("SELECT * FROM grocery_list_detail WHERE cart_id = :cart_id", cart_id = cart_id)
        
        # retrieve distinct purchase date
        date = db.execute("SELECT DISTINCT strftime('%m-%d-%Y', purchased) as purchase_date FROM grocery_list_detail WHERE cart_id = :cart_id", cart_id = cart_id)
        purchase_date = date[0]["purchase_date"]

        return render_template("single_cart.html", items = items, purchase_date = purchase_date)

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in."""

    # clear any user_id
    session.clear()

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("username"):
            return render_template("apology.html", message = "Must provide a username")

        # ensure password was submitted
        elif not request.form.get("password"):
            return render_template("apology.html", message = "Must provide a password")

        # query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))

        # ensure username exists and password is correct
        if len(rows) != 1 or not pwd_context.verify(request.form.get("password"), rows[0]["hash"]):
            return render_template("apology.html", message = "Invalid username and/or password")

        # remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # redirect user to home page
        return redirect(url_for("index"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out."""

    # forget any user_id
    session.clear()

    # redirect user to login form
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user."""

    if request.method == "POST":
        
        # validate form submission
        if not request.form.get("username"):
            return render_template("apology.html", message = "Please enter a username.")
        elif not request.form.get("password"):
            return render_template("apology.html", message = "Please enter a password.")
        elif request.form.get("password") != request.form.get("password_authenticate"):
            return render_template("apology.html", message = "Password authentication failed. Passwords don't match.")            
            
        # encrypt password
        hash = pwd_context.encrypt(request.form.get("password"))
        
        # add user to the database
        id = db.execute("INSERT INTO users (username, hash) VALUES(:username, :hash)", username=request.form.get("username"), hash = hash)
        if not id:
            return render_template("apology.html", message = "Username already taken. Please try a different username.")
            
        # log in user
        session["user_id"] = id
        
        # alert the user of successful registration
        flash("Registration complete")
        return redirect(url_for("index"))
    
    else:
        return render_template("register.html")
