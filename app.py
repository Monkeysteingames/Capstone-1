from flask import Flask, render_template, request, flash, redirect, session, g
from flask_debugtoolbar import DebugToolbarExtension
from forms import LoginForm, UserAddForm, FridgeForm
from models import User, Ingredient, Fridge, Fridge_Ingredients, connect_db, db
from key import API_SECRET_KEY, APP_CONFIG_KEY
from sqlalchemy.exc import IntegrityError
from fridge import check_for_fridge

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

######################################################################
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

######################################################################
# fridge routes


@app.route('/fridge/create', methods=["POST"])
def create_fridge():
    """Create fridge with g.user_id and add to database"""
    if g.user:
        fridge = Fridge(user_id=g.user.id)
        db.session.add(fridge)
        db.session.commit()
        flash(f"Fridge created for user #{g.user.id}", "success")
        return redirect('/')
    else:
        flash("Please login first to create your fridge", "danger")
        return redirect("/login")


@app.route('/fridge/<int:fridge_id>/add', methods=["GET", "POST"])
def add_to_fridge(fridge_id):
    """Handle adding ingredient to fridge with id of fridge_id"""
    form = FridgeForm()
    fridge = Fridge.query.get_or_404(fridge_id)

    if g.user:
        if form.validate_on_submit():
            fridge_ing = Fridge_Ingredients(
                fridge_id=fridge_id, ing_id=form.ing_id.data, food_group=form.food_group.data, img=form.img.data)
            db.session.add(fridge_ing)
            db.session.commit()
            return redirect(f"/fridge/{fridge_id}/add", form=form)
    else:
        flash("Please login first to create your fridge", "danger")
        return redirect("/login")

    return render_template('/fridge/fridge.html', form=form, fridge=fridge)


@app.route('/fridge/<int:fridge_id>/remove', methods=["GET", "POST"])
def remove_from_fridge(fridge_id):
    """Handle remove ingredient from fridge with id of fridge_id."""

#####################################################################
# homepage routes


@app.route('/')
def homepage():
    """Show homepage

    - anon users: show landing page
    - logged in:
        check if fridge exists:
            - if it does: show user fridge
            - if it does not: show button to create fridge
    """
    if g.user:
        fridge = check_for_fridge(g.user.id)
        return render_template('home.html', fridge=fridge)
    else:
        flash("Welcome!", "Success")
        return render_template('home-anon.html')
