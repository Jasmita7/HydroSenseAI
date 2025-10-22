from flask import Flask
from flask_pymongo import PyMongo
from flask_bcrypt import Bcrypt
import os

mongo = PyMongo()
bcrypt = Bcrypt()  # Correct

def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.secret_key = os.environ.get("FLASK_SECRET", "super_secret_key")
    app.config["MONGO_URI"] = os.environ.get("MONGO_URI", "mongodb://localhost:27017/hydroponics_ai")

    mongo.init_app(app)
    bcrypt.init_app(app)  # Correct

    from app.routes import main
    app.register_blueprint(main)

    return app
