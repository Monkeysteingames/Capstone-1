from flask import Flask, render_template, request, flash, redirect, session, g, jsonify
from flask_debugtoolbar import DebugToolbarExtension
from forms import (
    LoginForm,
    UserAddForm,
    FridgeSearchForm,
    IngredientSearchForm,
    IngredientResultForm,
)
from models import User, Ingredient, Fridge, Fridge_Ingredients, connect_db, db
from key import API_SECRET_KEY, APP_CONFIG_KEY
from sqlalchemy.exc import IntegrityError
from fridge import check_for_fridge
import requests


CURR_USER_KEY = "curr_user"

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql:///cookwhat"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = True
app.config["DEBUG_TB_INTERCEPT_REDIRECTS"] = False
app.config["SECRET_KEY"] = APP_CONFIG_KEY
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


@app.route("/signup", methods=["GET", "POST"])
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
                bio=form.bio.data,
            )
            db.session.commit()

        except IntegrityError:
            flash("Username already taken", "danger")
            return render_template("/users/signup.html", form=form)

        do_login(user)

        return redirect("/")

    else:
        return render_template("/users/signup.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Handle user login."""

    form = LoginForm()

    if form.validate_on_submit():
        user = User.authenticate(form.username.data, form.password.data)

        if user:
            do_login(user)
            flash(f"Hey {user.username}, welcome back!", "success")
            return redirect("/")

        else:
            flash("Invalid credentials", "danger")

    return render_template("/users/login.html", form=form)


@app.route("/logout")
def logout():
    """Handle user logout."""

    do_logout()

    flash("You've been logged out.", "info")

    return redirect("/")


# TODO: add route to update user profile


######################################################################
# fridge routes


@app.route("/fridge/create", methods=["POST"])
def create_fridge():
    """Create fridge with g.user_id and add to database"""
    if g.user:
        fridge = Fridge(user_id=g.user.id)
        db.session.add(fridge)
        db.session.commit()
        flash(f"Fridge created for user #{g.user.id}", "success")
        return redirect("/")
    else:
        flash("Please login first to create your fridge", "danger")
        return redirect("/login")


@app.route("/fridge/ingredient/remove/<int:id>", methods=["DELETE"])
def remove_from_fridge(id):
    """Handle remove ingredient from fridge."""
    if g.user:
        # get existing fridge_ing for curr_user and id for ing to delete
        fridge = Fridge.query.filter(Fridge.user_id == g.user.id).one()
        fridge_ing = Fridge_Ingredients.query.filter(
            Fridge_Ingredients.id == id, Fridge_Ingredients.fridge_id == fridge.id
        ).one()
        # remove from database
        db.session.delete(fridge_ing)
        db.session.commit()
        return jsonify(f"ingredient {id} removed from fridge {fridge.id}")
    else:
        flash("Please login first to create your fridge", "danger")
        return jsonify("Must be logged in to remove this ingredient.")


@app.route('/recipe/search', methods=["GET"])
def search_for_recipes():
    """Take query and number from JS send request for recipes. 

    Return with JSON of recipes retrieved from API."""
    # Implement
    if g.user:
        query = gather_ingredients_query()
        # We'll implement quantity selection for num of results on deployment
        rcps = request_recipes_search(query=query, number=10)
        return jsonify(rcps)
    else:
        return jsonify("Must be logged in to search for recipes.")


@app.route("/ingredient/search/<query>&<int:number>", methods=["GET"])
def search_for_ingredients(query, number):
    """Handle ingredient search"""
    if g.user:
        ings = request_ingredients(query, number)
        session['add_ings'] = ings
        return jsonify(ings)
    else:
        return jsonify('Must be logged in to search ingredients.')


@app.route("/fridge/ingredient/add", methods=["POST"])
def add_ingredient_to_fridge():
    """Handle add ingredient to fridge"""
    if g.user:
        try:
            # see if the fridge we're referencing is our curr_user's
            fridge = Fridge.query.filter(Fridge.user_id == g.user.id).one()
            fridge_ing = Fridge_Ingredients(
                fridge_id=fridge.id, ing_id=request.json['ing_id'], name=request.json['ing_name'])
            db.session.add(fridge_ing)
            db.session.commit()
            session["add_ings"] = []
            return jsonify(f"{request.json['ing_name']} added to fridge {fridge.id}")
        except:
            return jsonify('No matching fridge detected for curr_user')
    else:
        return jsonify("User not logged in. Cannot add item to fridge.")


@app.route('/fridge/ingredient/search/<int:ing_id>', methods=["GET"])
def get_fridge_ing_id(ing_id):
    """Search db for matching ing_id and fridge_id.

    Return json data of the id within in fridge."""
    if g.user:
        try:
            fridge = Fridge.query.filter(Fridge.user_id == g.user.id).one()
            frg_ing = Fridge_Ingredients.query.filter(
                Fridge_Ingredients.ing_id == ing_id, Fridge_Ingredients.fridge_id == fridge.id
            ).one()
            ing_f_id = frg_ing.id
            return jsonify(ing_f_id)
        except:
            return jsonify('No matching ingredient located in curr_users fridge.')
    else:
        return jsonify('No user logged in.')


def gather_ingredients_query():
    """Gather all the ingredients in the current fridge.

    Generate a list of them and turn into string.

    Each ingredient must be seperated with a ','. """
    fridge = Fridge.query.filter(Fridge.user_id == g.user.id).one()
    ing_list = Fridge.get_ingredients_list(fridge.id)
    ing_names = [ing.get('name', None) for ing in ing_list]
    ing_q = ',+'.join(ing_names)
    return ing_q

####################################################################
# ingredient & recipe search methods & API calls


def request_recipes_search(query, number):
    """Return list of recipes based on query."""
    key = API_SECRET_KEY
    url = f"{API_BASE_URL}/recipes/findByIngredients?ingredients={query}&number={number}&apiKey={key}"

    response = requests.get(url)
    rcps = response.json()
    return rcps


def request_ingredients(query, number):
    """Return list of ingredients based on query."""
    key = API_SECRET_KEY
    url = f"{API_BASE_URL}/food/ingredients/search?query={query}&number={number}&apiKey={key}"

    response = requests.get(url)
    res = response.json()
    ings = [r for r in res["results"]]

    return ings


def get_ingredient_name(selection):
    """Take the id of the ing we selected from the ing_res form.

    Turn the list of tuples into a dict.

    Get value of index with id == selection
    """
    ing_choices = session.get("ing_list", "not found")
    # change to dict to search through more efficiently
    d_ing_choices = dict(ing_choices)
    name = d_ing_choices[selection]
    return name

#####################################################################
# homepage routes


@app.route("/")
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
            srch_form = IngredientSearchForm()
            choice_range = list(range(1, 101))
            srch_form.quantity.choices = list(zip(choice_range, choice_range))
            return render_template("home.html", fridge=fridge, ingredients=ingredients, srch_form=srch_form)
        else:
            return render_template("home.html", fridge=None)
    else:
        flash("Welcome!", "success")
        return render_template("home-anon.html")
