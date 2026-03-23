# app.py
from flask import Flask
from config import Config  # Importing the configuration class
from farmer import farmer_bp  # Importing the farmer routes from farmer.py
from common import home, register, login, profile, logout  # Importing other route functions
from common import datetimeformat  
from payment_gateway import payment_bp
from customer import customer_bp
# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)
# Register the Blueprint for related routes
app.register_blueprint(farmer_bp)
app.register_blueprint(customer_bp, url_prefix="/customer")
app.register_blueprint(payment_bp, url_prefix="/payment")
app.jinja_env.filters['datetimeformat'] = datetimeformat

# Define other routes using the imported functions
@app.route("/")
def home_route():
    return home()

@app.route("/register", methods=["GET", "POST"])
def register_route():
    return register()

@app.route("/login", methods=["GET", "POST"])
def login_route():
    return login()

@app.route("/profile", methods=["GET", "POST"])
def profile_route():
    return profile()

@app.route("/logout")
def logout_route():
    return logout()

if __name__ == "__main__":
    app.run(debug=True)
