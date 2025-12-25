from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin
import cloudinary
app = Flask(__name__)
app.secret_key = "dfdsfi&^%&$&$"
app.config["SQLALCHEMY_DATABASE_URI"] ="mysql+pymysql://root:root@localhost/englishwebdb?charset=utf8mb4"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True
app.config["PAGE_SIZE"] =8
db = SQLAlchemy(app=app)
login = LoginManager(app)

cloudinary.config(cloud_name='dtmhmlbh1',
api_key ='912977876956358',
api_secret = 'LpYv5aoBpi22IPewHcHeqM0AE7A')