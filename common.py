# common.py
from flask import render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import re
from datetime import datetime
from db import farmers_collection, customers_collection  # Import collections from db.py

# Home Route
def home():
    return render_template("home.html")

# Registration Route
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        phone = request.form.get("phone")
        role = request.form.get("role")

        # Validate inputs
        if not username or not password or not phone or not role:
            flash("All fields are required!", "error")
            return redirect(url_for("home_route"))

        # Validate role
        if role not in ["farmer", "customer"]:
            flash("Invalid role selected!", "error")
            return redirect(url_for("home_route"))

        # Validate phone number (10-digit format)
        if not re.match(r"^\d{10}$", phone):
            flash("Phone number must be exactly 10 digits!", "error")
            return redirect(url_for("home_route"))

        # Hash password for security:
        hashed_password = generate_password_hash(password)

        # Determine the appropriate collection based on role
        collection = farmers_collection if role == "farmer" else customers_collection

        # Check if username or phone number already exists
        if collection.find_one({"$or": [{"username": username}, {"phone": phone}]}):
            flash("Username or phone number already exists!", "error")
            return redirect(url_for("home_route"))

        # Insert new user into the appropriate collection
        collection.insert_one({
            "username": username,
            "password": hashed_password,
            "phone": phone,
            "role": role
        })

        flash(f"{role.capitalize()} registered successfully!", "success")
        return redirect(url_for("login_route"))

    return redirect(url_for("home_route"))

# Login Route
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        role = request.form["role"]
        
        if not username or not password or not role:
            flash("All fields are required!", "error")
            return redirect(url_for("home_route"))

        collection = farmers_collection if role == "farmer" else customers_collection
        user = collection.find_one({"username": username})

        if user and check_password_hash(user["password"], password):
            session["username"] = username
            session["role"] = role
            
            if role == "farmer":
                return redirect(url_for("farmer.farmer_dashboard", username=username))
            else:
                return redirect(url_for("customer.browse_vegetables"))
        else:
            flash("Invalid credentials! Please check your username, password, or role.", "error")
            return redirect(url_for("home_route"))

    return redirect(url_for("home_route"))

# Profile Route
def profile():
    if 'username' not in session:
        flash("Please log in to view your profile.", "error")
        return redirect(url_for('login_route'))

    # Try to fetch the user from the farmers collection
    user = farmers_collection.find_one({"username": session['username']})

    # If not found in farmers, check the customers collection
    if not user:
        user = customers_collection.find_one({"username": session['username']})

    if not user:
        flash("User not found.", "error")
        return redirect(url_for('login_route'))

    # Handle username, password, and phone number updates
    if request.method == "POST":
        new_username = request.form.get("username")
        new_password = request.form.get("password")
        new_phone = request.form.get("phone")

        # Update the username if provided
        if new_username:
            collection = farmers_collection if user.get('role') == 'farmer' else customers_collection
            collection.update_one({"username": session['username']}, {"$set": {"username": new_username}})
            session['username'] = new_username  # Update session with the new username
            flash("Username updated successfully.", "success")

        # Update the password if provided
        if new_password:
            hashed_password = generate_password_hash(new_password)  # Hash the new password
            collection = farmers_collection if user.get('role') == 'farmer' else customers_collection
            collection.update_one({"username": session['username']}, {"$set": {"password": hashed_password}})
            flash("Password updated successfully.", "success")

        # Update the phone number if provided and valid
        if new_phone:
            if re.match(r"^\d{10}$", new_phone):  # Validate phone number format (10 digits)
                collection = farmers_collection if user.get('role') == 'farmer' else customers_collection
                collection.update_one({"username": session['username']}, {"$set": {"phone": new_phone}})
                flash("Phone number updated successfully.", "success")
            else:
                flash("Invalid phone number. Please enter a valid 10-digit number.", "error")

    # Re-fetch the user to reflect updated data in the profile
    user = farmers_collection.find_one({"username": session['username']}) or \
           customers_collection.find_one({"username": session['username']})

    return render_template("profile.html", user=user)


# Order time converter filter
def datetimeformat(value, format='%Y-%m-%d %H:%M:%S'):
    """Convert Unix timestamp to a human-readable format"""
    if isinstance(value, (int, float)):  # Check if it's a Unix timestamp
        return datetime.fromtimestamp(value).strftime(format)
    return value


# Logout Route
def logout():
    # Clear the user session
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login_route"))