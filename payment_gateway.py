from flask import Blueprint, request, redirect, url_for, session, flash, render_template
import uuid
import logging
from datetime import datetime
import requests
from config import Config
from db import customers_collection, history_collection, records_collection

# Define Blueprint
payment_bp = Blueprint("payment", __name__)

# Determine Cashfree API URL
CASHFREE_BASE_URL = "https://sandbox.cashfree.com/pg/orders" if Config.CASHFREE_ENVIRONMENT == "sandbox" else "https://api.cashfree.com/pg/orders"

# Headers for Cashfree API
HEADERS = {
    "Content-Type": "application/json",
    "x-client-id": Config.CASHFREE_CLIENT_ID,
    "x-client-secret": Config.CASHFREE_CLIENT_SECRET,
    "x-api-version": "2023-08-01"
}

# Payment Gateway Page
@payment_bp.route("/gateway")
def gateway():
    if 'username' not in session:
        flash("Please log in to continue.", "error")
        return redirect(url_for("login_route"))

    customer = customers_collection.find_one({"username": session['username']})
    if not customer:
        flash("Customer not found.", "error")
        return redirect(url_for("customer.browse_vegetables"))

    # Fetch latest order cost
    latest_order = history_collection.find_one({"customer_id": customer["_id"]}, sort=[("order_time", -1)])
    total_amount = latest_order["cost"] if latest_order else 1.00  # Default to ₹1.00

    return render_template(
        "gateway.html",
        customer_name=customer.get("name", customer["username"]),
        customer_email=customer.get("email", ""),
        customer_phone=customer.get("phone", ""),
        address=customer.get("address", ""),
        city=customer.get("city", ""),
        state=customer.get("state", ""),
        pincode=customer.get("pincode", ""),
        total_amount=total_amount
    )

# Create Order Route
@payment_bp.route('/create-order', methods=['POST'])
def create_order():
    try:
        if 'username' not in session:
            flash("Please log in to continue.", "error")
            return redirect(url_for("login_route"))

        # Fetch customer details
        customer = customers_collection.find_one({"username": session['username']})
        if not customer:
            flash("Customer not found.", "error")
            return redirect(url_for("customer.browse_vegetables"))

        # Get details from form or use defaults
        customer_name = request.form.get('customer_name') or customer.get("name", customer["username"])
        customer_email = request.form.get('customer_email') or customer.get("email", "")
        customer_phone = request.form.get('customer_phone') or customer.get("phone", "")

        address = request.form.get('address', customer.get("address", "Default Address"))
        city = request.form.get('city', customer.get("city", "Default City"))
        state = request.form.get('state', customer.get("state", "Default State"))
        pincode = request.form.get('pincode', customer.get("pincode", "000000"))

        # Fetch latest order cost
        latest_order = history_collection.find_one({"customer_id": customer["_id"]}, sort=[("order_time", -1)])
        order_amount = latest_order.get("cost", 1.00) if latest_order else 1.00

        # Generate unique order ID
        order_id = str(uuid.uuid4())

        # Create order payload
        payload = {
            "order_id": order_id,
            "order_amount": order_amount,
            "order_currency": "INR",
            "customer_details": {
                "customer_id": str(customer["_id"]),
                "customer_name": customer_name,
                "customer_email": customer_email,
                "customer_phone": customer_phone
            },
            "order_meta": {
                "return_url": url_for("payment.payment_status", order_id=order_id, _external=True)
            }
        }

        # Send request to Cashfree API
        response = requests.post(CASHFREE_BASE_URL, json=payload, headers=HEADERS)

        if response.status_code == 200:
            data = response.json()
            payment_session_id = data.get("payment_session_id")

            # Store order in MongoDB
            records_collection.insert_one({
                "order_id": order_id,
                "customer_id": str(customer["_id"]),
                "customer_name": customer_name,
                "customer_email": customer_email,
                "customer_phone": customer_phone,
                "order_amount": order_amount,
                "payment_status": "PENDING",
                "address": address,
                "city": city,
                "state": state,
                "pincode": pincode,
                "created_at": datetime.utcnow()
            })

            if payment_session_id:
                return render_template("checkout.html", payment_session_id=payment_session_id, order_amount=order_amount)
            else:
                return "Failed to get payment session ID.", 400
        else:
            return f"Payment gateway error: {response.text}", 400

    except Exception as e:
        logging.error(f"Error in create_order: {e}")
        return f"Error: {str(e)}", 500

# Payment Status Route
@payment_bp.route('/payment-status')
def payment_status():
    order_id = request.args.get("order_id")
    if not order_id:
        flash("Order ID is missing.", "error")
        return redirect(url_for("browse_vegetables"))

    try:
        # Fetch order from MongoDB
        order = records_collection.find_one({"order_id": order_id})
        if not order:
            flash("Order not found.", "error")
            return redirect(url_for("browse_vegetables"))

        # Query Cashfree API for payment status
        response = requests.get(f"{CASHFREE_BASE_URL}/{order_id}", headers=HEADERS)

        if response.status_code == 200:
            data = response.json()
            order_status = data.get("order_status", "").upper()

            # Map Cashfree status to user-friendly messages
            status_map = {
                "PAID": "Success",
                "ACTIVE": "Pending Payment",
                "FAILED": "Payment Failed",
                "EXPIRED": "Payment Expired",
                "CANCELLED": "Payment Cancelled"
            }
            user_friendly_status = status_map.get(order_status, "Unknown Status")

            # Update payment status in DB
            records_collection.update_one({"order_id": order_id}, {"$set": {"payment_status": user_friendly_status}})

            # Fetch updated order details
            updated_order = records_collection.find_one({"order_id": order_id})

            return render_template("payment_status.html", order=updated_order)

        else:
            flash("Failed to fetch order status.", "error")
            return redirect(url_for("customer.browse_vegetables"))

    except Exception as e:
        logging.error(f"Error in payment_status: {e}")
        flash(f"Error checking payment status: {str(e)}", "error")
        return redirect(url_for("customer.browse_vegetables"))