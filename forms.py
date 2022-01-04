# forms for Adding user, Logging In, Creating/Editing Fridge

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, IntegerField
from wtforms.validators import DataRequired, Email, Length


class UserAddForm(FlaskForm):
    """Form for adding users."""

    username = StringField('Username', validators=[DataRequired()])
    email = StringField('E-mail', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[Length(min=6)])
    avatar_img = StringField('(Optional) Image URL')
    bio = StringField('(Optional) Bio for user')


class LoginForm(FlaskForm):
    """Login form."""

    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[Length(min=6)])


class FridgeForm(FlaskForm):
    """Form for adding ingredients to users fridge."""

    ingredient = StringField('Ingredient', validators=[DataRequired()])
    quantity = IntegerField('Quantity', default=1, validators=[DataRequired()])
