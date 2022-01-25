from flask import Flask, render_template, request, flash, redirect, session, g, jsonify
from flask_debugtoolbar import DebugToolbarExtension
from forms import (
    LoginForm,
    UserAddForm,
    FridgeSearchForm,
    IngredientSearchForm,
    IngredientResultForm,
    UserEditForm,
)
from models import User, Ingredient, Fridge, Fridge_Ingredients, connect_db, db
from sqlalchemy.exc import IntegrityError
from fridge import check_for_fridge
from key import API_SECRET_KEY, APP_CONFIG_KEY
import requests
import os


CURR_USER_KEY = "curr_user"

app = Flask(__name__)

ENV = 'dev'

if ENV == 'dev':
    app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql:///cookwhat"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ECHO"] = True
    app.config["DEBUG_TB_INTERCEPT_REDIRECTS"] = False
    app.config["SECRET_KEY"] = APP_CONFIG_KEY
    toolbar = DebugToolbarExtension(app)
    API_KEY = API_SECRET_KEY
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = 'postgres://luavddnglgtpqk:9d32977cdfcb146d3ca4506e08260896d5effea72267c86203eedf5d74b27cba@ec2-184-73-243-101.compute-1.amazonaws.com:5432/d7ickq4oojjlgh'
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ECHO"] = False
    app.config["SECRET_KEY"] = os.environ.get('CONFIG_KEY')
    API_KEY = os.environ.get('API_KEY')

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


@app.route('/user/edit/<int:id>', methods=["GET", "POST"])
def edit_user_profile(id):
    """Handle edit user profile."""

    user = User.query.get_or_404(id)
    form = UserEditForm(obj=user)

    if form.validate_on_submit():
        if user.id == g.user.id:
            user.username = form.username.data
            user.email = form.email.data
            user.avatar_img = form.avatar_img.data
            user.password = user.password
            user.bio = form.bio.data

            db.session.commit()
            flash("User profile updated.", "info")
            return redirect('/')
        else:
            flash("Invalid credentials detected.", "danger")
            return redirect('/')
    else:
        return render_template("/users/edit.html", form=form)

######################################################################
# fridge routes


@app.route("/fridge/create", methods=["POST"])
def create_fridge():
    """Create fridge with g.user_id and add to database"""
    if g.user:
        fridge = Fridge(user_id=g.user.id)
        db.session.add(fridge)
        db.session.commit()
        flash(f"Fridge created!", "success")
        return redirect("/")
    else:
        flash("Please login first to create your fridge", "danger")
        return redirect("/login")


##################################################################################
# recipe routes

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


@app.route('/recipe/check-out/<int:rcp_id>', methods=["GET"])
def check_out_recipe(rcp_id):
    """
    Return JSON with recipe information from API.

    Render new template to present recipe information."""
    if g.user:
        rcp_info = lookup_recipe_info(rcp_id)
        rcp_inst_json = get_recipe_instructions(rcp_id)
        rcp_inst = [s['step'] for s in rcp_inst_json[0]['steps']]
        return render_template('/recipe/recipe.html', rcp_info=rcp_info, rcp_inst=rcp_inst)
    else:
        flash("Please login first to search for ingredients.", "danger")
        return redirect('/')


###############################################################################
# ingredient routes


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


#################################
# Non-view functions for ingredients

def gather_ingredients_query():
    """Gather all the ingredients in the current fridge.

    Generate a list of them and turn into string.

    Each ingredient must be seperated with a ','. """
    fridge = Fridge.query.filter(Fridge.user_id == g.user.id).one()
    ing_list = Fridge.get_ingredients_list(fridge.id)
    if len(ing_list) == 1:
        ing_q = ing_list[0].get('name', None)
    else:
        ing_names = [ing.get('name', None) for ing in ing_list]
        ing_q = ',+'.join(ing_names)
    return ing_q


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

####################################################################
# ingredient & recipe API calls


def request_recipes_search(query, number):
    """Return list of recipes based on query."""
    key = API_KEY
    url = f"{API_BASE_URL}/recipes/findByIngredients?ingredients={query}&number={number}&apiKey={key}"

    response = requests.get(url)
    rcps = response.json()
    return rcps


def lookup_recipe_info(id):
    """Return JSON of recipe info with given id"""
    key = API_KEY
    url = f"{API_BASE_URL}/recipes/{id}/information?includeNutrition=false&apiKey={key}"

    response = requests.get(url)
    rcp_inf = response.json()
    return rcp_inf


def get_recipe_instructions(id):
    """Return JSON of recipe instructions with given id"""
    key = API_KEY
    url = f"{API_BASE_URL}/recipes/{id}/analyzedInstructions?apiKey={key}"

    response = requests.get(url)
    rcp_inst = response.json()
    return rcp_inst


def request_ingredients(query, number):
    """Return list of ingredients based on query."""
    key = API_KEY
    url = f"{API_BASE_URL}/food/ingredients/search?query={query}&number={number}&apiKey={key}"

    response = requests.get(url)
    res = response.json()
    ings = [r for r in res["results"]]

    return ings


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
            return render_template("/fridge/user.html", fridge=fridge, ingredients=ingredients, srch_form=srch_form)
        else:
            return render_template("/fridge/user.html", fridge=None)
    else:
        flash("Welcome!", "success")
        return render_template("base-anon.html")
