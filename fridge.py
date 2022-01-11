# methods for the fridge
from models import Fridge


def check_for_fridge(user_id):
    """Check if user already has a fridge created.

    - If they do, return an instance of the fridge

    - If they do not, return None
    """
    try:
        fridge = Fridge.query.filter_by(user_id=user_id).one()
        return fridge
    except:
        return None
