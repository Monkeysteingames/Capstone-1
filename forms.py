# forms for Adding user, Logging In, Creating/Editing Fridge

from flask_wtf import FlaskForm
from models import Ingredient
from wtforms import (
    StringField,
    PasswordField,
    TextAreaField,
    IntegerField,
    SelectField,
    RadioField,
)
from wtforms.validators import DataRequired, Email, Length, Optional


class UserAddForm(FlaskForm):
    """Form for adding users."""

    username = StringField("Username", validators=[DataRequired()])
    email = StringField("E-mail", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[Length(min=6)])
    avatar_img = StringField("(Optional) Image URL")
    bio = StringField("(Optional) Bio for user")


class UserEditForm(FlaskForm):

    username = StringField("Username", validators=[DataRequired()])
    email = StringField("E-mail", validators=[DataRequired(), Email()])
    avatar_img = StringField("(Optional) Image URL")
    bio = StringField("(Optional) Bio for user")


class LoginForm(FlaskForm):
    """Login form."""

    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[Length(min=6)])


class FridgeForm(FlaskForm):
    """Form for adding ingredients to users fridge."""

    ingredient = SelectField("Ingredient", coerce=int)
    quantity = IntegerField("Quantity", default=1, validators=[DataRequired()])


class FridgeSearchForm(FlaskForm):
    """Form for searching for recipes."""

    ingredient = TextAreaField("Ingredient")
    quantity = SelectField("Amount of Recipes", coerce=int, default=10)


class IngredientSearchForm(FlaskForm):
    """Form for searching for ingredients."""

    query = TextAreaField("Query")
    quantity = SelectField("Amount of Recipes", coerce=int, default=10)


class IngredientResultForm(FlaskForm):
    """Form for displaying ingredient results."""

    result = RadioField("Ingredient Results", coerce=int)
