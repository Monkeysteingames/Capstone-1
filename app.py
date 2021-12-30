from flask import Flask, render_template, request, flash, redirect, session, g
from flask_debugtoolbar import DebugToolbarExtension
from forms import LoginForm, UserAddForm
from models import User, Ingredient, connect_db, db
from key import API_SECRET_KEY, APP_CONFIG_KEY
from sqlalchemy.exc import IntegrityError

CURR_USER_KEY = "curr_user"

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql:///cookwhat'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = True
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
app.config['SECRET_KEY'] = APP_CONFIG_KEY
toolbar = DebugToolbarExtension(app)

API_KEY = API_SECRET_KEY

connect_db(app)

################################
# user signup/login/logout


@app.before_request
def add_user_to_g():
    """If we're logged in, add curr user to Flask global."""

    if CURR_USER_KEY in session:
        g.user = User.query.get(session[CURR_USER_KEY])

    else:
        g.user = None


def do_login(user):
    """Log in user."""

    session[CURR_USER_KEY] = user.id


def do_logout():
    """Logout user."""

    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]


@app.route('/signup', methods=["GET", "POST"])
def signup():
    """Handle user signup.

    Create a new user and add them to the DB. Then redirect to homepage.

    If form is not valid, present form.

    If username is taken, flash error message and show form again.
    """

    form = UserAddForm()

    if form.validate_on_submit():
        try:
            user = User.signup(
                username=form.username.data,
                password=form.password.data,
                email=form.email.data,
                avatar_img=form.avatar_img.data,
                bio=form.bio.data
            )
            db.session.commit()

        except IntegrityError:
            flash("Username already taken", "danger")
            return render_template('/users/signup.html')

        do_login(user)

        return redirect('/')

    else:
        return render_template('/users/signup.html', form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    """Handle user login."""

    form = LoginForm()

    if form.validate_on_submit():
        user = User.authenticate(form.username.data, form.password.data)

        if user:
            do_login(user)
            flash(f"Hey {user.username}, welcome back!", "success")
            return redirect('/')

        else:
            flash("Invalid credentials", "danger")

    return render_template('/users/login.html', form=form)


@app.route('/logout')
def logout():
    """Handle user logout."""

    do_logout()

    flash("You've been logged out.", "info")

    return redirect('/')

#################################
# homepage routes


@app.route('/')
def homepage():
    """Show homepage

    - anon users: show landing page
    - logged in: show user fridge
    """
    if g.user:
        return render_template('home.html')
    else:
        flash("Welcome!", "Success")
        return render_template('home-anon.html')
