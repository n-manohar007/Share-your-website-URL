import certifi
from pymongo import MongoClient
from config import Config

ca = certifi.where()

client = MongoClient(Config.MONGO_URI, tlsCAFile=ca)

db = client.farm_fresh

# ✅ All collections (FINAL VERSION)
farmers_collection = db.farmers
customers_collection = db.customers
vegetables_collection = db.vegetables
history_collection = db.history
records_collection = db.records   # 🔥 ADD THIS LINE
users_collection = db.users
carts_collection = db.carts