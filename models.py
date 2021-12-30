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
    avatar_img = db.Column(db.String)
    bio = db.Column(db.String)

    def __repr__(self):
        return f"<User #{self.id}, {self.username}, {self.email}>"

    @classmethod
    def signup(cls, username, email, password, avatar_img, bio):
        """Sign up user.

        Hashes password and adds user to system.
        """

        hashed_pwd = bcrypt.generate_password_hash(password).decode('UTF-8')

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
    ing_id = db.Column(db.Integer, nullable=False)
    food_group = db.Column(db.String)
    img = db.Column(db.String)


class Fridge(db.Model):
    """Relationship table between our user and ingredients. Our fridge!"""

    __tablename__ = "fridges"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(
        'users.id', ondelete='CASCADE'), nullable=False)
    ing_id = db.Column(db.Integer, db.ForeignKey(
        'ingredients.id', ondelete='CASCADE'), nullable=False)


def connect_db(app):
    """Connect this database to our Flask app."""

    db.app = app
    db.init_app(app)
