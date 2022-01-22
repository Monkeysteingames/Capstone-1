from app import app, CURR_USER_KEY
import os
from unittest import TestCase

from models import db, connect_db, User, Ingredient, Fridge, Fridge_Ingredients

os.environ['DATABASE_URL'] = "postgresql:///cookwhat-test"

db.create_all()

app.config['WTF_CSRF_ENABLED'] = False
app.config['TESTING'] = True
app.config['DEBUG_TB_HOSTS'] = ['dont-show-debug-toolbar']


class UserViewTestCase(TestCase):
    """Test views for users."""

    def setUp(self):
        """Create test client, add sample data."""

        User.query.delete()

        self.client = app.test_client()

        self.testuser = User.signup(
            username='test_user',
            email='test_user@test.com',
            password='test_pwd',
            avatar_img='default_img',
            bio='test bio',
        )

        db.session.add(self.testuser)
        db.session.commit()

    def test_user_login(self):
        """
        Can we log the user in?
        """
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

        resp = c.post(
            "/login", data={"username": "test_user", "password": "test_pwd"}, follow_redirects=True)
        html = resp.get_data(as_text=True)

        self.assertEqual(resp.status_code, 200)
        self.assertIn('test_user', html)
        self.assertIn('test bio', html)

    def test_user_logout(self):
        """
        Does it properly log out the user?
        """
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

        c.post(
            "/login", data={"username": "test_user", "password": "test_pwd"}, follow_redirects=True)
        resp = c.get('/logout', follow_redirects=True)
        html = resp.get_data(as_text=True)

        self.assertEqual(resp.status_code, 200)
        self.assertIn("You&#39;ve been logged out.", html)

    def test_user_homepage(self):
        """
        When you’re logged in, does it redirect you to the home page?
        Does it show your avatar portion?
        """

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

        resp = c.get("/")
        html = resp.get_data(as_text=True)

        self.assertEqual(resp.status_code, 200)
        self.assertIn('test_user', html)
        self.assertIn('test bio', html)

    def test_user_edit(self):
        """
        Does user profile updated correctly?
        Does it prevent another user from updating a different user?
        """

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

        c.post(
            "/login", data={"username": "test_user", "password": "test_pwd"}, follow_redirects=True)
        resp = c.post(f"/user/edit/{self.testuser.id}", data={"username": "test_user_edited", "email": "test_user@test.com",
                                                              "avatar_img": "default_img", "bio": "test bio edited"}, follow_redirects=True)
        html = resp.get_data(as_text=True)

        self.assertEqual(resp.status_code, 200)
        self.assertIn('test_user_edited', html)
        self.assertIn('test bio edited', html)


class FridgeViewTestCase(TestCase):
    """Test views for fridge."""

    def setUp(self):
        """Create test client, add sample data."""

        User.query.delete()
        Fridge.query.delete()

        self.client = app.test_client()

        self.testuser = User.signup(
            username='test_user',
            email='test_user@test.com',
            password='test_pwd',
            avatar_img='default_img',
            bio='test bio',
        )

        db.session.add(self.testuser)
        db.session.commit()

    def test_create_fridge(self):
        """Does it create fridge and add to database?"""

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

        resp = c.post("/fridge/create", follow_redirects=True)
        html = resp.get_data(as_text=True)

        self.assertEqual(resp.status_code, 200)
        self.assertIn("Fridge created!", html)
        self.assertIsInstance(Fridge.query.filter_by(
            user_id=self.testuser.id).one(), Fridge)
