from flask import Flask
from pymongo import MongoClient
import os

def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.secret_key = os.environ.get("FLASK_SECRET", "super_secret_key")

    # MongoDB (optional) — if not needed you can remove these lines
    try:
        client = MongoClient(os.environ.get("MONGO_URI", "mongodb://localhost:27017/"))
        db = client["hydroponics_ai"]
        app.config["db"] = db
    except Exception:
        app.config["db"] = None

    # register blueprint
    from app.routes import main
    app.register_blueprint(main)

    return app
