#!/usr/bin/env python3

import os
from sqlalchemy import create_engine, text
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_bcrypt import Bcrypt
from flask_session import Session
from functools import wraps

# Set up Flask and database connection
tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)
bcrypt = Bcrypt(app)
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_PERMANENT"] = False
app.secret_key = "your_secret_key"  # Use a secure key in production
Session(app)

DB_USER = "sa4469"
DB_PASSWORD = "shunsuke"
DB_SERVER = "w4111.cisxo09blonu.us-east-1.rds.amazonaws.com"
DATABASEURI = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_SERVER}/w4111"

engine = create_engine(DATABASEURI)

# --- Define helper functions and decorators ---

# Role-based access control decorator
def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "user_id" not in session or session.get("role") != role:
                flash("Access denied: Insufficient permissions", "danger")
                return redirect(url_for("front_page"))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# --- Define routes ---

# Route for front dining hall page
@app.route("/")
def front_page():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT hall_id, name, location FROM Dining_Hall"))
        dining_halls = [{"id": row[0], "name": row[1], "location": row[2]} for row in result]
    return render_template("front_page.html", dining_halls=dining_halls)


@app.route("/dining_hall/<int:hall_id>")
def dining_hall_page(hall_id):
    with engine.connect() as conn:
        # Get dining hall information
        hall_query = "SELECT name, location FROM Dining_Hall WHERE hall_id = :hall_id"
        hall_result = conn.execute(text(hall_query), {"hall_id": hall_id}).fetchone()
        if not hall_result:
            return "Dining Hall not found", 404

        # Get foods for this dining hall
        food_query = """
        SELECT f.name, f.protein, f.carbs, f.fat, f.sugar, f.calories, f.serving_size, f.category
        FROM Food f
        JOIN Food_DiningHall fd ON f.food_id = fd.food_id
        WHERE fd.hall_id = :hall_id
        """
        food_result = conn.execute(text(food_query), {"hall_id": hall_id})
        foods = [{
            "name": row[0], "protein": row[1], "carbs": row[2], "fat": row[3],
            "sugar": row[4], "calories": row[5], "serving_size": row[6], "category": row[7]
        } for row in food_result]
    
    return render_template("dining_hall_page.html", hall=hall_result, foods=foods)


@app.route("/all_foods")
def all_foods():
    with engine.connect() as conn:
        food_query = """
        SELECT f.food_id, f.name, f.protein, f.carbs, f.fat, f.sugar, f.calories, 
               f.serving_size, f.category, 
               STRING_AGG(dh.name, ', ') AS dining_halls
        FROM Food f
        LEFT JOIN Food_DiningHall fd ON f.food_id = fd.food_id
        LEFT JOIN Dining_Hall dh ON fd.hall_id = dh.hall_id
        GROUP BY f.food_id
        """
        food_result = conn.execute(text(food_query))
        
        foods = [{
            "food_id": row[0], "name": row[1], "protein": row[2], "carbs": row[3], 
            "fat": row[4], "sugar": row[5], "calories": row[6], "serving_size": row[7], 
            "category": row[8], "dining_halls": row[9]
        } for row in food_result]
    
    return render_template("all_foods.html", foods=foods)



@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        role = request.form.get("role", "Visitor")

        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

        with engine.connect() as conn:
            try:
                conn.execute(text("INSERT INTO Users (email, password, role) VALUES (:email, :password, :role)"),
                             {"email": email, "password": hashed_password, "role": role})
                flash("Registration successful!", "success")
                return redirect(url_for("login"))
            except Exception as e:
                flash("Registration failed. Please try again.", "danger")
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        with engine.connect() as conn:
            user = conn.execute(
                text("SELECT user_id, email, password, role FROM Users WHERE email = :email"),
                {"email": email}
            ).mappings().fetchone()

        if user and user["password"] == password:  # Access password by key
            session["user_id"] = user["user_id"]
            session["user_email"] = user["email"]
            session["role"] = user["role"]
            session["user_name"] = "Admin Name"  # Placeholder name for now

            flash("Login successful!", "success")
            if user["role"] == "Admin":
                return redirect(url_for("admin_dashboard"))
            else:
                return redirect(url_for("front_page"))
        else:
            flash("Invalid email or password", "danger")
    return render_template("login.html")



@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out", "info")
    return redirect(url_for("front_page"))

# Admin-only dashboard
@app.route("/admin_dashboard")
@role_required("Admin")
def admin_dashboard():
    return render_template("admin_dashboard.html")


# Custom error page for Access Denied (Optional)
@app.errorhandler(403)
def access_denied(error):
    return render_template("403.html"), 403

@app.route("/request_food", methods=["GET", "POST"])
def request_food():
    if "user_id" not in session:
        flash("Please log in to make a food request.", "warning")
        return redirect(url_for("login"))

    if request.method == "POST":
        request_food_item = request.form.get("request_food_item")
        description = request.form.get("description")
        user_id = session["user_id"]

        with engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO Request (user_id, request_food_item, description, request_status, request_date)
                    VALUES (:user_id, :request_food_item, :description, 'pending', CURRENT_DATE)
                """),
                {"user_id": user_id, "request_food_item": request_food_item, "description": description}
            )

        flash("Food request submitted successfully!", "success")
        return redirect(url_for("front_page"))

    return render_template("request_food.html")

@app.route("/records/<int:food_id>", methods=["GET", "POST"])
def view_records(food_id):
    if "user_id" not in session:
        flash("Please log in to view or create records.", "warning")
        return redirect(url_for("login"))

    with engine.connect() as conn:
        # Fetch food details
        food_query = "SELECT name, calories FROM Food WHERE food_id = :food_id"
        food = conn.execute(text(food_query), {"food_id": food_id}).fetchone()

        # Fetch existing records for this food item
        records_query = """
        SELECT r.content, r.time, u.email 
        FROM Record r
        JOIN Users u ON r.user_id = u.user_id
        WHERE r.food_id = :food_id
        ORDER BY r.time DESC
        """
        records = conn.execute(text(records_query), {"food_id": food_id}).fetchall()

    if request.method == "POST":
        # Ensure the user is logged in
        if "user_id" not in session:
            flash("Please log in to create a record.", "warning")
            return redirect(url_for("login"))

        # Get the form data
        content = request.form.get("content")
        user_id = session["user_id"]

        # Insert the new record into the database
        with engine.connect() as conn:
            conn.execute(
                text("INSERT INTO Record (food_id, user_id, content, time) VALUES (:food_id, :user_id, :content, CURRENT_TIMESTAMP)"),
                {"food_id": food_id, "user_id": user_id, "content": content}
            )
        flash("Your record has been added successfully!", "success")
        return redirect(url_for("view_records", food_id=food_id))

    return render_template("records.html", food=food, records=records)


@app.route("/admin_requests")
@role_required("Admin")
def admin_requests():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM Request WHERE request_status = 'pending'"))
        requests = [{"request_id": row[0], "user_id": row[1], "food_item": row[2], "description": row[3]} for row in result]
    return render_template("admin_requests.html", requests=requests)

# --- Add this route to handle request updates (e.g., approving or rejecting requests) ---
@app.route("/update_request/<int:request_id>/<status>")
@role_required("Admin")
def update_request(request_id, status):
    with engine.connect() as conn:
        # Update the request status in the database
        conn.execute(
            text("UPDATE Request SET request_status = :status WHERE request_id = :request_id"),
            {"status": status, "request_id": request_id}
        )
    flash(f"Request {status.capitalize()} successfully.", "success")
    return redirect(url_for("admin_requests"))




if __name__ == "__main__":
    import click

    @click.command()
    @click.option('--debug', is_flag=True)
    @click.option('--threaded', is_flag=True)
    @click.argument('HOST', default='0.0.0.0')
    @click.argument('PORT', default=8111, type=int)
    def run(debug, threaded, host, port):
        app.run(host=host, port=port, debug=debug, threaded=threaded)

    run()
