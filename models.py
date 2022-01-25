# models for User, Fridge, Ingredients and method for db connection

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
    avatar_img = db.Column(
        db.String, default="https://st2.depositphotos.com/1341440/7182/v/600/depositphotos_71824861-stock-illustration-chef-hat-vector-black-silhouette.jpg")
    bio = db.Column(db.String)

    def __repr__(self):
        return f"<User #{self.id}, {self.username}, {self.email}>"

    @classmethod
    def signup(cls, username, email, password, avatar_img, bio):
        """Sign up user.

        Hashes password and adds user to system.
        """

        hashed_pwd = bcrypt.generate_password_hash(password).decode("UTF-8")

        user = User(
            username=username,
            email=email,
            password=hashed_pwd,
            avatar_img=avatar_img,
            bio=bio,
        )

        db.session.add(user)
        return user

    @classmethod
    def authenticate(cls, username, password):
        """Find user with provide 'username' & 'password'.

        If user and pass match, returns that user object.

        If can't find matching user or if password is wrong, returns False.
        """

        user = cls.query.filter_by(username=username).first()

        if user:
            is_auth = bcrypt.check_password_hash(user.password, password)
            if is_auth:
                return user

        return False


class Ingredient(db.Model):
    """Ingredients stored in user fridges"""

    __tablename__ = "ingredients"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)

    def __repr__(self):
        return f"<Ingredient ID#{self.ing_id}, {self.name}>"


class Fridge(db.Model):
    """Relationship table between our user and fridges."""

    __tablename__ = "user_fridges"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    ingredients = db.relationship("Fridge_Ingredients")

    def __repr__(self):
        return f"<Fridge #{self.id}, User #{self.user_id}>"

    @classmethod
    def get_ingredients_list(cls, id):
        """Get list of ingredients associated with fridge of given id"""
        fridge = Fridge.query.get_or_404(id)
        fridge_ingredients = [i.__dict__ for i in fridge.ingredients]
        return fridge_ingredients


class Fridge_Ingredients(db.Model):
    """Relationship table between our fridge and ingredients. Our fridge!"""

    __tablename__ = "fridge_ingredients"

    id = db.Column(db.Integer, primary_key=True)
    fridge_id = db.Column(
        db.Integer, db.ForeignKey("user_fridges.id", ondelete="CASCADE"), nullable=False
    )
    ing_id = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String)

    def __repr__(self):
        return f"<Ingredient #{self.ing_id}, stored in Fridge #{self.fridge_id}>"


def connect_db(app):
    """Connect this database to our Flask app."""

    db.app = app
    db.init_app(app)
