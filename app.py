from flask import Flask, render_template, request, flash, redirect, session, g
from flask_debugtoolbar import DebugToolbarExtension
from forms import LoginForm, UserAddForm, FridgeForm, FridgeSearchForm
from models import User, Ingredient, Fridge, Fridge_Ingredients, connect_db, db
from key import API_SECRET_KEY, APP_CONFIG_KEY
from sqlalchemy.exc import IntegrityError
from fridge import check_for_fridge
import requests


CURR_USER_KEY = "curr_user"

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql:///cookwhat'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = True
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
app.config['SECRET_KEY'] = APP_CONFIG_KEY
toolbar = DebugToolbarExtension(app)

API_KEY = API_SECRET_KEY
API_BASE_URL = "https://api.spoonacular.com/"

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
            return render_template('/users/signup.html', form=form)

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
    ingredients = [(i.id, i.name) for i in Ingredient.query.all()]
    form.ingredient.choices = ingredients
    import pdb
    pdb.set_trace()

    if g.user:
        if form.validate_on_submit():
            #############
            # TODO: when we obtain ingredients, we'll need to also get the food
            # group and image so we can display them correctly in the Fridge
            # We'll need to implement our first API call here
            #############
            fridge_ing = Fridge_Ingredients(
                fridge_id=fridge_id, ing_id=form.ingredient.data)
            db.session.add(fridge_ing)
            db.session.commit()
            return redirect(f"/fridge/{fridge_id}/add")
    else:
        flash("Please login first to create your fridge", "danger")
        return redirect("/login")

    return render_template('/fridge/fridge.html', form=form, fridge=fridge)


@app.route('/fridge/<int:fridge_id>/remove', methods=["GET", "POST"])
def remove_from_fridge(fridge_id):
    """Handle remove ingredient from fridge with id of fridge_id."""


@app.route('/fridge/<int:fridge_id>/search', methods=["GET", "POST"])
def search_recipes(fridge_id):
    """Send request to API to search for recipes based on given ingredients"""
    # TODO: implement fully

    fridge = Fridge.query.get_or_404(fridge_id)
    form = FridgeSearchForm()
    choice_range = list(range(1, 100))
    form.quantity.choices = list(zip(choice_range, choice_range))

    if g.user:
        if form.validate_on_submit():
            ingredient = form.ingredient.data
            r = request_ingredients(ingredient)
            import pdb
            pdb.set_trace()

            return render_template('/fridge/recipe-search.html', form=form, fridge=fridge)
    else:
        flash("Please login first to create your fridge", "danger")
        return redirect("/login")

    flash("No form validated", "info")
    return render_template('/fridge/recipe-search.html', form=form, fridge=fridge)

####################################################################
# ingredient search methods


def request_ingredients(ingredients):
    """Return list of ingredients based on query."""
    key = API_SECRET_KEY
    url = f"{API_BASE_URL}/recipes/findByIngredients?ingredients={ingredients}&apiKey={key}"

    response = requests.get(url)
    r = response.json()
    print(r)
    return r


#####################################################################
# homepage routes


@app.route('/')
def homepage():
    """Show homepage

    - anon users: show landing page
    - logged in:
        check if fridge exists:
            - if it does: show user fridge features
            - if it does not: show button to create fridge
    """
    if g.user:
        fridge = check_for_fridge(g.user.id)
        if fridge:
            ingredients = Fridge.get_ingredients_list(fridge.id)
            return render_template('home.html', fridge=fridge, ingredients=ingredients)
        else:
            return render_template('home.html', fridge=None)
    else:
        flash("Welcome!", "success")
        return render_template('home-anon.html')
