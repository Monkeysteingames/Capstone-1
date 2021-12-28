from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy

bcrypt = Bcrypt()
db = SQLAlchemy()


class User(db.Model):
    """User in the system."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, nullable=False, unique=True)
    email = db.Column(db.String, nullable=False, unique=True)
    password = db.Column(db.String, nullable=False)
    fridge_id = db.Column(db.Integer, unique=True)


class Ingredient(db.Model):
    """Ingredients stored in user fridges"""

    __tablename__ = "ingredients"

    id = db.Column(db.Integer, primary_key=True)
    fridge_id = db.Column(db.Integer, db.ForeignKey(
        'users.fridge_id', ondelete='CASCADE'), nullable=False)

    ing_id = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String, nullable=False)
    food_group = db.Column(db.String, nullable=False)
    img = db.Column(db.String)

    user = db.relationship("User")


def connect_db(app):
    """Connect this database to our Flask app."""

    db.app = app
    db.init_app(app)
