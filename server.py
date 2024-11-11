#!/usr/bin/env python3

import os
from sqlalchemy import create_engine, text
from flask import Flask, render_template, request, redirect, url_for

# Set up Flask and database connection
tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)

DB_USER = "sa4469"
DB_PASSWORD = "shunsuke"
DB_SERVER = "w4111.cisxo09blonu.us-east-1.rds.amazonaws.com"
DATABASEURI = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_SERVER}/w4111"

engine = create_engine(DATABASEURI)

# --- Define routes here ---

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
        SELECT name, protein, carbs, fat, sugar, calories, serving_size, category 
        FROM Food
        """
        food_result = conn.execute(text(food_query))
        
        foods = [{
            "name": row[0], "protein": row[1], "carbs": row[2], "fat": row[3], 
            "sugar": row[4], "calories": row[5], "serving_size": row[6], "category": row[7]
        } for row in food_result]
    
    return render_template("all_foods.html", foods=foods)



# --- End of routes ---

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
