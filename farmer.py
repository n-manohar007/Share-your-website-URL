# farmer.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from bson import ObjectId
import os
from db import farmers_collection, vegetables_collection, history_collection  # Import collections from db.py
from config import Config
from common import datetimeformat  # Import the datetimeformat filter from common.py

# Create a Blueprint for the farmer routes
farmer_bp = Blueprint('farmer', __name__)

# Helper function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

# Farmer Dashboard Route
@farmer_bp.route("/farmer_dashboard/<username>", methods=["GET", "POST"])
def farmer_dashboard(username):
    farmer = farmers_collection.find_one({"username": username})
    vegetables = vegetables_collection.find({"farmer_username": username})

    if request.method == "POST":
        if "update_price" in request.form:
            vegetable_id = request.form["vegetable_id"]
            new_price = float(request.form["price"])

            # Update price in the database
            vegetables_collection.update_one(
                {"_id": ObjectId(vegetable_id)},
                {"$set": {"price": new_price}}
            )
        else:
            vegetable_name = request.form["vegetable_name"]
            price = float(request.form["price"])

            photo_filename = None
            if 'photo' in request.files:
                photo = request.files['photo']
                if photo and allowed_file(photo.filename):
                    photo_filename = secure_filename(photo.filename)
                    photo.save(os.path.join(Config.UPLOAD_FOLDER, photo_filename))

            # Add new vegetable to the database
            vegetables_collection.insert_one({
                "vegetable_name": vegetable_name,
                "price": price,
                "photo_filename": photo_filename,
                "farmer_username": username
            })

        return redirect(url_for("farmer.farmer_dashboard", username=username))

    return render_template("farmer_dashboard.html", farmer=farmer, vegetables=vegetables)

# Adjust Vegetable Price Route
@farmer_bp.route("/adjust_price/<username>/<vegetable_id>", methods=["GET", "POST"])
def adjust_price(username, vegetable_id):
    vegetable = vegetables_collection.find_one({"_id": ObjectId(vegetable_id)})

    if request.method == "POST":
        new_name = request.form["name"]
        new_price = float(request.form["price"])
        new_photo_filename = None

        if 'photo' in request.files:
            photo = request.files['photo']
            if photo and allowed_file(photo.filename):
                new_photo_filename = secure_filename(photo.filename)
                photo.save(os.path.join(Config.UPLOAD_FOLDER, new_photo_filename))

        # Update vegetable information
        update_data = {"$set": {"vegetable_name": new_name, "price": new_price}}
        if new_photo_filename:
            update_data["$set"]["photo_filename"] = new_photo_filename

        vegetables_collection.update_one({"_id": ObjectId(vegetable_id)}, update_data)
        return redirect(url_for("farmer.farmer_dashboard", username=username))

    return render_template("adjust_price.html", vegetable=vegetable)

# Remove Vegetable Route
@farmer_bp.route("/remove_vegetable/<username>/<vegetable_id>", methods=["POST"])
def remove_vegetable(username, vegetable_id):
    vegetable = vegetables_collection.find_one({"_id": ObjectId(vegetable_id)})

    if not vegetable:
        flash("Vegetable not found.", "error")
        return redirect(url_for("farmer.farmer_dashboard", username=username))

    if vegetable.get("farmer_username") != username:
        flash("You cannot delete this vegetable.", "error")
        return redirect(url_for("farmer.farmer_dashboard", username=username))

    # Remove vegetable from the database
    vegetables_collection.delete_one({"_id": ObjectId(vegetable_id)})

    if vegetable.get("photo_filename"):
        try:
            os.remove(os.path.join(Config.UPLOAD_FOLDER, vegetable["photo_filename"]))
        except Exception as e:
            flash(f"Error removing image file: {e}", "error")

    flash(f"'{vegetable['vegetable_name']}' removed successfully!", "success")
    return redirect(url_for("farmer.farmer_dashboard", username=username))


@farmer_bp.route('/update_status/<order_id>', methods=['POST'])
def update_status(order_id):
    new_status = request.form.get("status")

    if not new_status:
        flash("No status selected. Please try again.", "danger")
        return redirect(url_for('farmer.view_orders'))

    try:
        # Update the order status in the history collection
        result = history_collection.update_one(
            {"_id": ObjectId(order_id)},
            {"$set": {"status": new_status}}
        )

        if result.matched_count > 0:
            flash("Order status updated successfully!", "success")
        else:
            flash("Order not found. Update failed.", "danger")

    except Exception as e:
        flash(f"An error occurred: {str(e)}", "danger")

    return redirect(url_for('farmer.view_orders'))





# View Orders Route
@farmer_bp.route("/view_orders")
def view_orders():
    if 'username' not in session:
        flash("Please log in to view orders.", "error")
        return redirect(url_for("login_route"))  # Redirect to login if not logged in

    # Get the farmer's username from the session
    farmer_username = session['username']

    # Get all orders for the farmer, sorted by order_time (latest first)
    orders = list(history_collection.find({"farmer_username": farmer_username}).sort("order_time", -1))

    return render_template("view_orders.html", orders=orders, farmer_username=farmer_username)