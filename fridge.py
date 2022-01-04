# methods for the fridge

from models import User, Ingredient, Fridge, Fridge_Ingredients, connect_db, db


def check_for_fridge(user_id):
    """Check if user already has a fridge created. 

    - If they do, return an instance of the fridge

    - If they do not, return None
    """
    fridge = Fridge.query.filter_by(user_id=user_id).all()[0]
    return fridge
