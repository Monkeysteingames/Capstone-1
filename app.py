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
app.config["DEBUG_TB_INTERCEPT_REDIRECTS"] = True
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
        fridge = Fridge.query.filter(Fridge.user_id == g.user.id).one()
        q = Fridge_Ingredients.query
        fridge_ing = q.filter(
            Fridge_Ingredients.id == id, Fridge_Ingredients.fridge_id == fridge.id
        )
        db.session.delete(fridge_ing)
        db.session.commit()
        return jsonify(message="deleted")
    else:
        flash("Please login first to create your fridge", "danger")
        return redirect("/login")


@app.route("/fridge/<int:fridge_id>/search", methods=["GET", "POST"])
def search_recipes(fridge_id):
    """Send request to API to search for recipes based on given ingredients"""

    fridge = Fridge.query.get_or_404(fridge_id)
    form = FridgeSearchForm()

    # API can only support 1-100 results per query, create constraint for total results list
    choice_range = list(range(1, 101))
    form.quantity.choices = list(zip(choice_range, choice_range))

    if g.user:
        if form.validate_on_submit():
            ingredients = form.ingredient.data
            rcps = request_recipes(ingredients)
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
                "/fridge/ingredient-search.html",
                srch_form=srch_form,
                fridge=fridge,
                ings=ings,
                res_form=res_form,
            )
    else:
        flash("Please login first to create your fridge", "danger")
        return redirect("/login")

    return render_template(
        "/fridge/ingredient-search.html", srch_form=srch_form, fridge=fridge
    )


@app.route("/fridge/<int:fridge_id>/add", methods=["POST"])
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
            flash(
                f"form validated and returning to ingredient search for fridge #{fridge_id}"
            )
            return redirect(f"/fridge/{fridge_id}/ingredient/search")
    else:
        flash("Please login first to edit your fridge", "danger")
        return redirect("/login")
    flash("No form validated.", "danger")
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


def request_recipes(ingredients):
    """Return list of ingredients based on query."""
    key = API_SECRET_KEY
    url = f"{API_BASE_URL}/recipes/findByIngredients?ingredients={ingredients}&apiKey={key}"

    response = requests.get(url)
    res = response.json()
    rcps = [r for r in res["results"]]

    return rcps


def request_ingredients(query):
    """Return list of ingredients based on query."""
    key = API_SECRET_KEY
    url = f"{API_BASE_URL}/food/ingredients/search?query={query}&apiKey={key}"

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
            return render_template("home.html", fridge=fridge, ingredients=ingredients)
        else:
            return render_template("home.html", fridge=None)
    else:
        flash("Welcome!", "success")
        return render_template("home-anon.html")
