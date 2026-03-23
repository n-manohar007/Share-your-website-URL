from flask import Blueprint, request, render_template, redirect, url_for, session, flash
from bson.objectid import ObjectId
from datetime import datetime
from config import *
from db import  *
#from payment_gateway import payment_bp

# Create a Blueprint for customer routes
customer_bp = Blueprint("customer", __name__)

# ---------------------- BROWSE VEGETABLES ----------------------
@customer_bp.route("/browse_vegetables", methods=["GET", "POST"])
def browse_vegetables():
    if 'username' not in session:
        flash("Please log in to continue.", "error")
        return redirect(url_for("login_route"))

    customer = customers_collection.find_one({"username": session['username']})
    if not customer:
        flash("Customer not found.", "error")
        return redirect(url_for("login_route"))

    vegetables = list(vegetables_collection.find())

    if request.method == "POST":
        vegetable_id = request.form["vegetable_id"]
        action = request.form["action"]
        quantity = int(request.form.get("quantity", 1))

        vegetable = vegetables_collection.find_one({"_id": ObjectId(vegetable_id)})
        if not vegetable:
            flash("Vegetable not found!", "error")
            return redirect(url_for("customer.browse_vegetables"))

        vegetable_name = vegetable["vegetable_name"]
        vegetable_price = vegetable["price"]
        vegetable_photo = vegetable.get("photo_filename", None)
        farmer_username = vegetable.get("farmer_username", "Unknown")

        if action == "add_to_cart":
            cart = carts_collection.find_one({"customer_id": customer["_id"]})

            if not cart:
                carts_collection.insert_one({
                    "customer_id": customer["_id"],
                    "customer_name": customer["username"],
                    "vegetables": [{
                        "vegetable_id": vegetable_id,
                        "vegetable_name": vegetable_name,
                        "price": vegetable_price,
                        "photo_filename": vegetable_photo,
                        "farmer_username": farmer_username,
                        "quantity": quantity
                    }]
                })
            else:
                carts_collection.update_one(
                    {"customer_id": customer["_id"]},
                    {"$addToSet": {"vegetables": {
                        "vegetable_id": vegetable_id,
                        "vegetable_name": vegetable_name,
                        "price": vegetable_price,
                        "photo_filename": vegetable_photo,
                        "farmer_username": farmer_username,
                        "quantity": quantity
                    }}}
                )

            flash(f"'{vegetable_name}' added to your cart!", "success")
            return redirect(url_for("customer.browse_vegetables"))

        elif action == "order":
            farmer = farmers_collection.find_one({"username": farmer_username})
            farmer_phone = farmer.get("phone", "N/A")

            history_collection.insert_one({
                "customer_id": customer["_id"],
                "customer_name": customer["username"],
                "customer_phone": customer.get("phone", "N/A"),
                "farmer_phone": farmer_phone,
                "vegetable_id": vegetable_id,
                "vegetable_name": vegetable_name,
                "cost": vegetable_price * quantity,
                "photo_filename": vegetable_photo,
                "farmer_username": farmer_username,
                "status": "Ordered",
                "quantity": quantity,
                "order_time": datetime.now().timestamp()
            })

            flash(f"Order for {quantity} {vegetable_name}(s) placed successfully!", "success")
            return redirect(url_for("payment.gateway"))

    return render_template("browse_vegetables.html", vegetables=vegetables, customer=customer)

# ---------------------- VIEW ORDER HISTORY ----------------------
@customer_bp.route("/order_history")
def order_history():
    if 'username' not in session:
        flash("Please log in to view your order history.", "error")
        return redirect(url_for("login_route"))

    customer = customers_collection.find_one({"username": session['username']})
    if not customer:
        flash("Customer not found.", "error")
        return redirect(url_for("login_route"))

    orders = list(history_collection.find({"customer_id": customer["_id"]}).sort("order_time", -1))
    return render_template("order_history.html", orders=orders, customer=customer)

# ---------------------- VIEW CART ----------------------
@customer_bp.route("/view_cart", methods=["GET", "POST"])
def view_cart():
    if 'username' not in session:
        flash("Please log in to continue.", "error")
        return redirect(url_for("login_route"))

    customer = customers_collection.find_one({"username": session['username']})
    if not customer:
        flash("Customer not found.", "error")
        return redirect(url_for("login_route_route"))

    cart = carts_collection.find_one({"customer_id": customer["_id"]}) or {"vegetables": []}
    total_price = sum(item["price"] * item["quantity"] for item in cart["vegetables"]) if cart["vegetables"] else 0

    if request.method == "POST":
        action = request.form.get("action")
        vegetable_id = request.form.get("vegetable_id")

        if action == "update_quantity":
            new_quantity = int(request.form.get("new_quantity", 1))
            carts_collection.update_one(
                {"customer_id": customer["_id"], "vegetables.vegetable_id": vegetable_id},
                {"$set": {"vegetables.$.quantity": new_quantity}}
            )
            flash("Cart updated successfully!", "success")
        elif action == "remove_from_cart":
            carts_collection.update_one(
                {"customer_id": customer["_id"]},
                {"$pull": {"vegetables": {"vegetable_id": vegetable_id}}}
            )
            flash("Item removed from cart.", "success")
        elif action == "checkout":
            return redirect(url_for("customer.checkout"))

        return redirect(url_for("customer.view_cart"))

    return render_template("view_cart.html", cart=cart, total_price=total_price, customer=customer)

# ---------------------- CHECKOUT ----------------------
@customer_bp.route("/checkout", methods=["POST"])
def checkout():
    if 'username' not in session:
        flash("Please log in to proceed with checkout.", "error")
        return redirect(url_for("login_route"))

    customer = customers_collection.find_one({"username": session['username']})
    if not customer:
        flash("Customer not found.", "error")
        return redirect(url_for("login_route"))

    cart = carts_collection.find_one({"customer_id": customer["_id"]}) or {"vegetables": []}
    if not cart["vegetables"]:
        flash("Your cart is empty.", "error")
        return redirect(url_for("customer.view_cart"))

    total_cost = sum(item["price"] * item["quantity"] for item in cart["vegetables"])
    vegetables_list = []
    farmer_usernames = set()

    for item in cart["vegetables"]:
        vegetables_list.append({
            "vegetable_id": item["vegetable_id"],
            "vegetable_name": item["vegetable_name"],
            "quantity": item["quantity"],
            "price": item["price"],
            "total_price": item["price"] * item["quantity"],
            "farmer_username": item["farmer_username"],
            "photo_filename": item.get("photo_filename", ""),
        })
        farmer_usernames.add(item["farmer_username"])

    farmers = farmers_collection.find({"username": {"$in": list(farmer_usernames)}})
    farmer_phone_map = {farmer["username"]: farmer.get("phone", "N/A") for farmer in farmers}

    history_collection.insert_one({
        "customer_id": customer["_id"],
        "customer_name": customer["username"],
        "customer_phone": customer.get("phone", "N/A"),
        "farmer_phones": farmer_phone_map,
        "order_items": vegetables_list,
        "cost": total_cost,
        "status": "Ordered",
        "order_time": datetime.now().timestamp()
    })

    carts_collection.delete_one({"customer_id": customer["_id"]})

    flash("Checkout successful! Your order has been placed.", "success")
    return redirect(url_for("payment.gateway"))


@customer_bp.route("/clear_selected_orders", methods=["POST"])
def clear_selected_orders():
    if 'username' not in session:
        flash("Please log in first.", "error")
        return redirect(url_for("login_route"))

    selected_order_ids = request.form.getlist("order_ids")  # Get list of selected order IDs

    if selected_order_ids:
        history_collection.delete_many({"_id": {"$in": [ObjectId(oid) for oid in selected_order_ids]}})
        flash("Selected orders have been deleted.", "success")
    else:
        flash("No orders selected.", "warning")

    return redirect(url_for("customer.order_history"))

@customer_bp.route("/clear_all_orders", methods=["POST"])
def clear_all_orders():
    if 'username' not in session:
        flash("Please log in first.", "error")
        return redirect(url_for("login_route"))

    customer = customers_collection.find_one({"username": session['username']})
    if customer:
        history_collection.delete_many({"customer_id": customer["_id"]})
        flash("All order history has been cleared.", "success")
    
    return redirect(url_for("customer.order_history"))

