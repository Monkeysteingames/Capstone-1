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


@app.route("/fridge/<int:fridge_id>/search", methods=["GET", "POST"])
def search_recipes(fridge_id):
    """Send request to API to search for recipes based on given ingredients"""

    fridge = Fridge.query.get_or_404(fridge_id)
    form = FridgeSearchForm()

    # API can only support 1-100 results per query, create constraint for total results list
    choice_range = list(range(1, 101))
    form.quantity.choices = list(zip(choice_range, choice_range))

    if g.user:
        # TODO: edit this to get the ingredients from our fridge
        # we'll need to create a string from the list that fits the API's format for the end point
        if form.validate_on_submit():
            ingredients = form.ingredient.data
            rcps = request_recipes_fridge(ingredients)
            return render_template(
                "/fridge/recipe-search.html", form=form, fridge=fridge
            )
    else:
        flash("Please login first to create your fridge", "danger")
        return redirect("/login")

    return render_template("/fridge/recipe-search.html", form=form, fridge=fridge)


@app.route("/fridge/<int:fridge_id>/ingredient/search", methods=["GET", "POST"])
def search_ingredients(fridge_id):
    """Send request to API to search for ingredients based on given query"""

    fridge = Fridge.query.get_or_404(fridge_id)
    srch_form = IngredientSearchForm()
    # API can only support 1-100 results per query, create constraint for total results list
    choice_range = list(range(1, 101))
    srch_form.quantity.choices = list(zip(choice_range, choice_range))

    if g.user:
        if srch_form.validate_on_submit():
            # get query from form validation and call API request to get ingredients
            q = srch_form.query.data
            ings = request_ingredients(q)

            # split results from API call in list of tuples and add that list to session
            ing_choices = [(r["id"], r["name"]) for r in ings]
            session["ing_list"] = ing_choices

            # add ing_list to our choices for the result form and render the template
            res_form = IngredientResultForm()
            res_form.result.choices = ing_choices

            return render_template(
                "home.html",
                srch_form=srch_form,
                fridge=fridge,
                ings=ings,
                res_form=res_form,
            )
    else:
        flash("Please login first to create your fridge.", "danger")
        return redirect("/login")

    return render_template(
        "home.html", srch_form=srch_form, fridge=fridge
    )


@app.route("/ingredient/search/<query>&<int:number>", methods=["GET"])
def search_for_ingredients(query, number):
    """Handle ingredient search"""
    if g.user:
        ings = request_ingredients(query, number)
        session['ings'] = ings
        return jsonify(ings)
    else:
        return jsonify('Must be logged in to search ingredients.')


@app.route("/fridge/ingredient/add", methods=["POST"])
def add_ingredient_to_fridge():
    """Handle add ingredient to fridge"""
    if g.user:
        # get existing fridge for curr_user
        fridge = Fridge.query.filter(Fridge.user_id == g.user.id).one()
        fridge_ing = Fridge_Ingredients(
            fridge_id=fridge.id, ing_id=request.json['ing_id'], name=request.json['ing_name'])
        db.session.add(fridge_ing)
        db.session.commit()
        session["ings"] = []
        flash(f"{request.json['ing_name']} added to your fridge.", "success")
        return redirect("/")
    else:
        flash("Please login first to edit your fridge", "danger")
        return redirect("/login")


@app.route("/fridge/<int:fridge_id>/add", methods=["GET", "POST"])
def add_to_fridge(fridge_id):
    """Handle adding ingredient to fridge with id of fridge_id"""
    res_form = IngredientResultForm()
    fridge = Fridge.query.get_or_404(fridge_id)
    # grab our ing list from session
    ing_choices = session.get("ing_list", "not found")
    # having an issue with pre-validation due to using radiofield for the ingredient results.
    # we need to generate the same ing choices for the form to validate. So we pull it from our session.
    res_form.result.choices = ing_choices

    if g.user:
        if res_form.validate_on_submit():
            ing_name = get_ingredient_name(res_form.result.data)
            ing_id = res_form.result.data

            fridge_ing = Fridge_Ingredients(
                fridge_id=fridge_id, ing_id=ing_id, name=ing_name
            )
            db.session.add(fridge_ing)
            db.session.commit()
            session["ing_list"] = []
            flash(f"{ing_name} added to your fridge.", "success")
            return redirect("/")
    else:
        flash("Please login first to edit your fridge", "danger")
        return redirect("/login")

    return redirect(f"/fridge/{fridge_id}/ingredient/search")


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
# ingredient & recipe search methods - API calls


def request_recipes_fridge(ingredients):
    """Return list of recipes based on query."""
    key = API_SECRET_KEY
    url = f"{API_BASE_URL}/recipes/findByIngredients?ingredients={ingredients}&apiKey={key}"

    response = requests.get(url)
    res = response.json()
    rcps = [r for r in res["results"]]

    return rcps


def request_recipes_search(query, number):
    """Return list of recipes based on query."""
    key = API_SECRET_KEY
    url = f"{API_BASE_URL}/recipes/complexSearch?query={query}&apiKey={key}"

    response = requests.get(url)
    res = response.json()
    rcps = [r for r in res["results"]]

    return rcps


def request_ingredients(query, number):
    """Return list of ingredients based on query."""
    key = API_SECRET_KEY
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
            return render_template("home.html", fridge=fridge, ingredients=ingredients, srch_form=srch_form)
        else:
            return render_template("home.html", fridge=None)
    else:
        flash("Welcome!", "success")
        return render_template("home-anon.html")
