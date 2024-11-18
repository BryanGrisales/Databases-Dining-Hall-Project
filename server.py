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
    query = request.args.get("query", "").lower()  # Get the search query
    search_type = request.args.get("search_type", "food").lower()  # Default to 'food'
    page = int(request.args.get("page", 1))  # Get the current page, default to 1
    per_page = 10  # Number of items per page

    with engine.connect() as conn:
        # Get dining hall information
        hall_query = "SELECT name, location FROM Dining_Hall WHERE hall_id = :hall_id"
        hall_result = conn.execute(text(hall_query), {"hall_id": hall_id}).fetchone()
        if not hall_result:
            return "Dining Hall not found", 404

        # Build the WHERE clause for filtering
        where_clause = "1=1"
        if search_type == "food":
            where_clause = "LOWER(f.name) LIKE :query"
        elif search_type == "category":
            where_clause = "LOWER(f.category) LIKE :query"

        # Query for foods with filtering and pagination
        food_query = f"""
        SELECT f.food_id, f.name, f.protein, f.carbs, f.fat, f.sugar, f.calories, 
               f.serving_size, f.category
        FROM Food f
        JOIN Food_DiningHall fd ON f.food_id = fd.food_id
        WHERE fd.hall_id = :hall_id AND {where_clause}
        LIMIT :limit OFFSET :offset
        """

        # Pagination parameters
        limit = per_page
        offset = (page - 1) * per_page
        foods = conn.execute(
            text(food_query),
            {"hall_id": hall_id, "query": f"%{query}%", "limit": limit, "offset": offset},
        ).fetchall()

        # Count total items for pagination
        count_query = f"""
        SELECT COUNT(f.food_id) AS total
        FROM Food f
        JOIN Food_DiningHall fd ON f.food_id = fd.food_id
        WHERE fd.hall_id = :hall_id AND {where_clause}
        """
        total_count = conn.execute(
            text(count_query), {"hall_id": hall_id, "query": f"%{query}%"}
        ).scalar()

    total_pages = (total_count + per_page - 1) // per_page  # Calculate total pages

    return render_template(
        "dining_hall_page.html",
        hall=hall_result,
        foods=foods,
        query=query,
        search_type=search_type,
        page=page,
        total_pages=total_pages,
        hall_id=hall_id,  # Pass hall_id explicitly
    )



@app.route("/all_foods")
def all_foods():
    query = request.args.get("query", "").lower()  # Get the search query
    search_type = request.args.get("search_type", "food").lower()  # Default to 'food'
    page = int(request.args.get("page", 1))  # Get the current page, default to 1
    per_page = 10  # Number of items per page

    with engine.connect() as conn:
        # Build the WHERE clause based on the search type
        where_clause = "1=1"  # Default: no filtering
        if search_type == "food":
            where_clause = "LOWER(f.name) LIKE :query"
        elif search_type == "category":
            where_clause = "LOWER(f.category) LIKE :query"
        elif search_type == "dining_hall":
            where_clause = "LOWER(dh.name) LIKE :query"

        # Query for foods with filtering and pagination
        food_query = f"""
        SELECT f.food_id, f.name, f.protein, f.carbs, f.fat, f.sugar, f.calories, 
               f.serving_size, f.category, 
               STRING_AGG(dh.name, ', ') AS dining_halls
        FROM Food f
        LEFT JOIN Food_DiningHall fd ON f.food_id = fd.food_id
        LEFT JOIN Dining_Hall dh ON fd.hall_id = dh.hall_id
        WHERE {where_clause}
        GROUP BY f.food_id
        LIMIT :limit OFFSET :offset
        """

        # Pagination parameters
        limit = per_page
        offset = (page - 1) * per_page
        foods = conn.execute(
            text(food_query),
            {"query": f"%{query}%", "limit": limit, "offset": offset},
        ).fetchall()

        # Count total items for pagination
        count_query = f"""
        SELECT COUNT(DISTINCT f.food_id) AS total
        FROM Food f
        LEFT JOIN Food_DiningHall fd ON f.food_id = fd.food_id
        LEFT JOIN Dining_Hall dh ON fd.hall_id = dh.hall_id
        WHERE {where_clause}
        """
        total_count = conn.execute(
            text(count_query), {"query": f"%{query}%"}
        ).scalar()

    total_pages = (total_count + per_page - 1) // per_page  # Calculate total pages

    return render_template(
        "all_foods.html",
        foods=foods,
        query=query,
        search_type=search_type,
        page=page,
        total_pages=total_pages,
    )





@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        role = request.form.get("role", "Visitor")

        if password != confirm_password:
            flash("Passwords do not match. Please try again.", "danger")
            return render_template("register.html") 

        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

        with engine.connect() as conn:
            try:
                conn.execute(
                    text("INSERT INTO Users (email, password, role) VALUES (:email, :password, :role)"),
                    {"email": email, "password": hashed_password, "role": role}
                )
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

            flash("Login successful!", "success")
            if user["role"] == "Admin":
                return redirect(url_for("admin_dashboard"))
            else:
                return redirect(url_for("user_dashboard"))
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
    user_id = session["user_id"]

    with engine.connect() as conn:
        # Fetch the admin's information
        user_query = "SELECT user_id, email, role FROM Users WHERE user_id = :user_id"
        user = conn.execute(text(user_query), {"user_id": user_id}).fetchone()

        # Fetch all records created by the admin
        records_query = """
        SELECT r.content, r.time, f.name AS food_name 
        FROM Record r
        JOIN Food f ON r.food_id = f.food_id
        WHERE r.user_id = :user_id
        ORDER BY r.time DESC
        """
        records = conn.execute(text(records_query), {"user_id": user_id}).fetchall()

    return render_template("admin_dashboard.html", user=user, records=records)



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

    # Check if the request is a POST (attempt to add a new record)
    if request.method == "POST":
        # Ensure the user is logged in
        if "user_id" not in session:
            flash("Please log in to create a record.", "warning")
            return redirect(url_for("login"))

        # Get the form data for creating a new record
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

def user_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session or session.get("role") != "Visitor":
            flash("Access denied: Admin users cannot access the user dashboard", "danger")
            return redirect(url_for("admin_dashboard"))
        return f(*args, **kwargs)
    return decorated_function

@app.route("/user_dashboard")
@user_only
def user_dashboard():
    user_id = session["user_id"]
    with engine.connect() as conn:
        # Fetch user information
        user_query = "SELECT user_id, email, role FROM Users WHERE user_id = :user_id"
        user = conn.execute(text(user_query), {"user_id": user_id}).fetchone()

        # Fetch records created by the user
        records_query = """
        SELECT r.content, r.time, f.name AS food_name 
        FROM Record r
        JOIN Food f ON r.food_id = f.food_id
        WHERE r.user_id = :user_id
        ORDER BY r.time DESC
        """
        records = conn.execute(text(records_query), {"user_id": user_id}).fetchall()

    return render_template("user_dashboard.html", user=user, records=records)


@app.route("/my_requests")
def my_requests():
    # Ensure the user is logged in
    if "user_id" not in session:
        flash("Please log in to view your requests.", "warning")
        return redirect(url_for("login"))

    user_id = session["user_id"]

    with engine.connect() as conn:
        # Query to fetch user requests
        requests_query = """
        SELECT request_id, request_food_item, description, request_status, request_date
        FROM Request
        WHERE user_id = :user_id
        ORDER BY request_date DESC
        """
        user_requests = conn.execute(text(requests_query), {"user_id": user_id}).fetchall()

    return render_template("my_requests.html", requests=user_requests)



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
