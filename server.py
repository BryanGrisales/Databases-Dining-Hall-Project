import os
import uuid
from sqlalchemy import create_engine, text
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_bcrypt import Bcrypt
from flask_session import Session
from functools import wraps


tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)
bcrypt = Bcrypt(app)
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_PERMANENT"] = False
app.secret_key = "your_secret_key"  # -- Might add later
Session(app)

DB_USER = "sa4469"
DB_PASSWORD = "shunsuke"
DB_SERVER = "w4111.cisxo09blonu.us-east-1.rds.amazonaws.com"
DATABASEURI = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_SERVER}/w4111"

engine = create_engine(DATABASEURI)

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


@app.route("/")
def front_page():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT hall_id, name, location FROM Dining_Hall"))
        dining_halls = [{"id": row[0], "name": row[1], "location": row[2]} for row in result]
    return render_template("front_page.html", dining_halls=dining_halls)


@app.route("/dining_hall/<int:hall_id>")
def dining_hall_page(hall_id):
    query = request.args.get("query", "").lower()  
    search_type = request.args.get("search_type", "food").lower()  
    page = int(request.args.get("page", 1))  
    per_page = 10  

    with engine.connect() as conn:
        # Get dining hall information
        hall_query = "SELECT name, location FROM Dining_Hall WHERE hall_id = :hall_id"
        hall_result = conn.execute(text(hall_query), {"hall_id": hall_id}).fetchone()
        if not hall_result:
            return "Dining Hall not found", 404

        # Validate search_type
        valid_search_types = {"food": "f.name", "category": "f.category"}
        if search_type not in valid_search_types:
            search_type = "food"  # Default to food name

        # Use separate queries for each type to prevent column injection
        if search_type == "food":
            food_query = """
            SELECT f.food_id, f.name, f.protein, f.carbs, f.fat, f.sugar, f.calories, 
                f.serving_size, f.category
            FROM Food f
            JOIN Food_DiningHall fd ON f.food_id = fd.food_id
            WHERE fd.hall_id = :hall_id AND LOWER(f.name) LIKE :query
            LIMIT :limit OFFSET :offset
            """
            count_query = """
            SELECT COUNT(f.food_id) AS total
            FROM Food f
            JOIN Food_DiningHall fd ON f.food_id = fd.food_id
            WHERE fd.hall_id = :hall_id AND LOWER(f.name) LIKE :query
            """
        elif search_type == "category":
            food_query = """
            SELECT f.food_id, f.name, f.protein, f.carbs, f.fat, f.sugar, f.calories, 
                f.serving_size, f.category
            FROM Food f
            JOIN Food_DiningHall fd ON f.food_id = fd.food_id
            WHERE fd.hall_id = :hall_id AND LOWER(f.category) LIKE :query
            LIMIT :limit OFFSET :offset
            """
            count_query = """
            SELECT COUNT(f.food_id) AS total
            FROM Food f
            JOIN Food_DiningHall fd ON f.food_id = fd.food_id
            WHERE fd.hall_id = :hall_id AND LOWER(f.category) LIKE :query
            """

        # Fetch foods
        foods = conn.execute(
            text(food_query),
            {"hall_id": hall_id, "query": f"%{query}%", "limit": per_page, "offset": (page - 1) * per_page},
        ).fetchall()

        # Fetch total count for pagination
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
    query = request.args.get("query", "").lower()  
    search_type = request.args.get("search_type", "food").lower()  
    page = int(request.args.get("page", 1))  
    per_page = 10  

    with engine.connect() as conn:
        # Validate the search type to avoid SQL injection
        valid_search_types = {"food": "f.name", "category": "f.category", "dining_hall": "dh.name"}
        column = valid_search_types.get(search_type, "f.name") 

        # Query for foods with filtering and pagination
        food_query = f"""
        SELECT f.food_id, f.name, f.protein, f.carbs, f.fat, f.sugar, f.calories, 
               f.serving_size, f.category, 
               STRING_AGG(DISTINCT dh.name, ', ') AS dining_halls
        FROM Food f
        LEFT JOIN Food_DiningHall fd ON f.food_id = fd.food_id
        LEFT JOIN Dining_Hall dh ON fd.hall_id = dh.hall_id
        WHERE LOWER({column}) LIKE :query
        GROUP BY f.food_id
        LIMIT :limit OFFSET :offset
        """
        foods = conn.execute(
            text(food_query),
            {"query": f"%{query}%", "limit": per_page, "offset": (page - 1) * per_page},
        ).fetchall()

        # Count total items for pagination
        count_query = f"""
        SELECT COUNT(DISTINCT f.food_id) AS total
        FROM Food f
        LEFT JOIN Food_DiningHall fd ON f.food_id = fd.food_id
        LEFT JOIN Dining_Hall dh ON fd.hall_id = dh.hall_id
        WHERE LOWER({column}) LIKE :query
        """
        total_count = conn.execute(
            text(count_query), {"query": f"%{query}%"}
        ).scalar()

    total_pages = (total_count + per_page - 1) // per_page

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

        try:
            with engine.begin() as conn:
                user_id = conn.execute(
                    text("SELECT COALESCE(MAX(user_id), 0) + 1 FROM Users")
                ).scalar()
                conn.execute(
                    text("""
                        INSERT INTO Users (user_id, email, password, role) 
                        VALUES (:user_id, :email, :password, :role)
                    """),
                    {"user_id": user_id, "email": email, "password": password, "role": role}
                )

                session["user_id"] = user_id
                session["user_email"] = email
                session["role"] = role

                flash("Registration successful! You are now logged in.", "success")
                return redirect(url_for("front_page"))
        except Exception as e:
            print(f"INSERT FAILED: {e}")
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

        if user and user["password"] == password: 
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

@app.route("/admin_dashboard")
@role_required("Admin")
def admin_dashboard():
    with engine.connect() as conn:
        user_id = session.get("user_id")
        if not user_id:
            flash("Session expired. Please log in again.", "danger")
            return redirect(url_for("login"))

        user_query = "SELECT user_id, email, role FROM Users WHERE user_id = :user_id"
        admin_user = conn.execute(text(user_query), {"user_id": user_id}).fetchone()
        if not admin_user:
            flash("Admin user not found. Please log in again.", "danger")
            return redirect(url_for("login"))

        page = int(request.args.get("page", 1))
        per_page = 5  
        offset = (page - 1) * per_page

        users_query = """
        SELECT user_id, email, role 
        FROM Users 
        WHERE user_id != :admin_id
        ORDER BY role, email
        LIMIT :limit OFFSET :offset
        """
        users = conn.execute(
            text(users_query),
            {"admin_id": user_id, "limit": per_page, "offset": offset},
        ).fetchall()

        total_count_query = """
        SELECT COUNT(*) 
        FROM Users 
        WHERE user_id != :admin_id
        """
        total_count = conn.execute(
            text(total_count_query), {"admin_id": user_id}
        ).scalar()

        total_pages = (total_count + per_page - 1) // per_page

        records_query = """
        SELECT r.record_id, r.content, r.time, f.name AS food_name 
        FROM Record r
        JOIN Food f ON r.food_id = f.food_id
        WHERE r.user_id = :admin_id
        ORDER BY r.time DESC
        """
        records = conn.execute(
            text(records_query), {"admin_id": user_id}
        ).fetchall()

    return render_template(
        "admin_dashboard.html",
        admin=admin_user,
        users=users,
        page=page,
        total_pages=total_pages,
        records=records,  
    )


@app.route("/update_role/<int:user_id>/<new_role>", methods=["POST"])
@role_required("Admin")
def update_role(user_id, new_role):
    if new_role not in ["Admin", "Visitor"]:
        flash("Invalid role specified.", "danger")
        return redirect(url_for("admin_dashboard"))

    try:
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE Users SET role = :new_role WHERE user_id = :user_id"),
                {"new_role": new_role, "user_id": user_id}
            )
        flash(f"User role updated to {new_role} successfully!", "success")
    except Exception as e:
        print(f"UPDATE ROLE FAILED: {e}")
        flash("Failed to update user role. Please try again.", "danger")

    return redirect(url_for("admin_dashboard"))




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

        if not request_food_item:
            flash("Food item name cannot be empty.", "danger")
            return redirect(url_for("request_food"))

        try:
            with engine.begin() as conn:
                result = conn.execute(
                    text("""
                        INSERT INTO Request (user_id, request_food_item, description, request_status, request_date)
                        VALUES (:user_id, :request_food_item, :description, 'pending', CURRENT_DATE)
                    """),
                    {"user_id": user_id, "request_food_item": request_food_item, "description": description}
                )
                print(f"INSERT SUCCESSFUL: {result.rowcount} row(s) affected")
            flash("Food request submitted successfully!", "success")
        except Exception as e:
            print(f"INSERT FAILED: {e}")
            flash("Failed to submit the food request. Please try again.", "danger")
            return redirect(url_for("request_food"))

        return redirect(url_for("front_page"))

    return render_template("request_food.html")


@app.route("/records/<int:food_id>", methods=["GET", "POST"])
def view_records(food_id):
    if request.method == "POST":
        if "user_id" not in session:
            flash("Please log in to create a record.", "warning")
            return redirect(url_for("login"))

        content = request.form.get("content")
        user_id = session["user_id"]

        print(f"User ID: {user_id}, Food ID: {food_id}, Content: {content}")

        if not content:
            flash("Content cannot be empty.", "danger")
            return redirect(url_for("view_records", food_id=food_id))

        try:
            with engine.begin() as conn:
                result = conn.execute(
                    text("""
                    INSERT INTO record (food_id, user_id, content, time)
                    VALUES (:food_id, :user_id, :content, CURRENT_TIMESTAMP)
                    """),
                    {"food_id": food_id, "user_id": user_id, "content": content}
                )
                print(f"INSERT SUCCESSFUL: {result.rowcount} row(s) affected")
            flash("Your record has been added successfully!", "success")
        except Exception as e:
            print(f"INSERT FAILED: {e}")
            flash("Failed to add the record. Please try again.", "danger")

        return redirect(url_for("view_records", food_id=food_id))

    with engine.connect() as conn:
        food_query = """
        SELECT name, calories, protein, carbs, fat, sugar, serving_size
        FROM food
        WHERE food_id = :food_id
        """
        food = conn.execute(text(food_query), {"food_id": food_id}).mappings().fetchone()

        if not food:
            flash("Food item not found.", "danger")
            return redirect(url_for("front_page"))

        records_query = """
        SELECT r.content, r.time, u.email
        FROM record r
        JOIN users u ON r.user_id = u.user_id
        WHERE r.food_id = :food_id
        ORDER BY r.time DESC
        """
        records = conn.execute(text(records_query), {"food_id": food_id}).fetchall()

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
    try:
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE Request SET request_status = :status WHERE request_id = :request_id"),
                {"status": status, "request_id": request_id}
            )
        flash(f"Request {status.capitalize()} successfully.", "success")
    except Exception as e:
        print(f"UPDATE FAILED: {e}")
        flash("Failed to update the request. Please try again.", "danger")

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
        user_query = "SELECT user_id, email, role FROM Users WHERE user_id = :user_id"
        user = conn.execute(text(user_query), {"user_id": user_id}).fetchone()

        records_query = """
        SELECT r.record_id, r.content, r.time, f.name AS food_name 
        FROM Record r
        JOIN Food f ON r.food_id = f.food_id
        WHERE r.user_id = :user_id
        ORDER BY r.time DESC
        """
        records = conn.execute(text(records_query), {"user_id": user_id}).fetchall()

    return render_template("user_dashboard.html", user=user, records=records)


@app.route("/my_requests")
def my_requests():
    if "user_id" not in session:
        flash("Please log in to view your requests.", "warning")
        return redirect(url_for("login"))

    user_id = session["user_id"]

    with engine.connect() as conn:
        requests_query = """
        SELECT request_id, request_food_item, description, request_status, request_date
        FROM Request
        WHERE user_id = :user_id
        ORDER BY request_date DESC
        """
        user_requests = conn.execute(text(requests_query), {"user_id": user_id}).fetchall()

    return render_template("my_requests.html", requests=user_requests)

@app.route("/add_food/<int:request_id>", methods=["GET", "POST"])
@role_required("Admin")
def add_food(request_id):
    with engine.connect() as conn:
        request_details = conn.execute(
            text("""
                SELECT request_food_item, description, user_id
                FROM Request
                WHERE request_id = :request_id AND request_status = 'pending'
            """),
            {"request_id": request_id}
        ).mappings().fetchone()

        if not request_details:
            flash("Request not found or already processed.", "danger")
            return redirect(url_for("admin_requests"))

        dining_halls = conn.execute(
            text("SELECT hall_id, name FROM Dining_Hall")
        ).fetchall()

        if request.method == "POST":
            # Collect form data
            name = request.form.get("name")
            calories = request.form.get("calories", 0)
            protein = request.form.get("protein", 0)
            carbs = request.form.get("carbs", 0)
            fat = request.form.get("fat", 0)
            sugar = request.form.get("sugar", 0)
            serving_size = request.form.get("serving_size", "N/A")
            category = request.form.get("category", "Other")
            selected_halls = request.form.getlist("dining_halls") 

            # Validate required fields
            if not name or not calories or not selected_halls:
                flash("Please fill out all required fields and select at least one dining hall.", "danger")
                return render_template("add_food.html", request_details=request_details, dining_halls=dining_halls)

            try:
                with engine.begin() as conn:
                    food_id = conn.execute(
                        text("SELECT COALESCE(MAX(food_id), 0) + 1 FROM Food")
                    ).scalar()

                    conn.execute(
                        text("""
                            INSERT INTO Food (food_id, name, calories, protein, carbs, fat, sugar, serving_size, category)
                            VALUES (:food_id, :name, :calories, :protein, :carbs, :fat, :sugar, :serving_size, :category)
                        """),
                        {
                            "food_id": food_id,
                            "name": name,
                            "calories": calories,
                            "protein": protein,
                            "carbs": carbs,
                            "fat": fat,
                            "sugar": sugar,
                            "serving_size": serving_size,
                            "category": category,
                        }
                    )

                    for hall_id in selected_halls:
                        conn.execute(
                            text("""
                                INSERT INTO Food_DiningHall (food_id, hall_id)
                                VALUES (:food_id, :hall_id)
                            """),
                            {"food_id": food_id, "hall_id": int(hall_id)}
                        )

                    # Update the request status to 'approved'
                    conn.execute(
                        text("""
                            UPDATE Request
                            SET request_status = 'approved'
                            WHERE request_id = :request_id
                        """),
                        {"request_id": request_id}
                    )

                    flash("Food item and associated dining halls added successfully!", "success")
                    return redirect(url_for("admin_requests"))

            except Exception as e:
                print(f"INSERT FAILED: {e}")
                flash("Failed to add the food item. Please try again.", "danger")

    return render_template("add_food.html", request_details=request_details, dining_halls=dining_halls)

@app.route("/delete_record/<int:record_id>", methods=["POST"])
def delete_record(record_id):
    if "user_id" not in session:
        flash("Please log in to delete a record.", "danger")
        return redirect(url_for("login"))
    
    user_id = session["user_id"]
    try:
        with engine.begin() as conn:
            record = conn.execute(
                text("SELECT * FROM Record WHERE record_id = :record_id AND user_id = :user_id"),
                {"record_id": record_id, "user_id": user_id}
            ).fetchone()

            if not record:
                flash("You do not have permission to delete this record.", "danger")
                return redirect(url_for("user_dashboard") if session["role"] == "Visitor" else url_for("admin_dashboard"))

            # Delete the record
            conn.execute(
                text("DELETE FROM Record WHERE record_id = :record_id"),
                {"record_id": record_id}
            )
            flash("Record deleted successfully.", "success")
    except Exception as e:
        print(f"DELETE RECORD FAILED: {e}")
        flash("Failed to delete the record. Please try again.", "danger")
    
    return redirect(url_for("user_dashboard") if session["role"] == "Visitor" else url_for("admin_dashboard"))




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
