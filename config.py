
class Config:
    SECRET_KEY = "your_secret_key_here"

    MONGO_URI = (
        "mongodb+srv://manoharnellikondi1_db_user:KRXLVEctmS9bk0y3"
        "@cluster0.2mza3bb.mongodb.net/farm_fresh"
        "?retryWrites=true&w=majority&appName=Cluster0"
    )

    DEBUG = True

    # ✅ Cashfree Config
    CASHFREE_CLIENT_ID = "test"
    CASHFREE_CLIENT_SECRET = "test"
    CASHFREE_ENVIRONMENT ="test"
    UPLOAD_FOLDER = "static/uploads"
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}




