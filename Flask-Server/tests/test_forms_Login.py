import unittest
from flask import Flask
from app import create_app, db
from app.forms import LoginForm

class TestLoginForm(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_login_form_validation(self):
        form_data = {'email': 'user@example.com', 'password': 'correcthorsebatterystaple'}
        form = LoginForm(data=form_data)
        self.assertTrue(form.validate(), "Form should be valid")

    def test_login_form_validation_failure(self):
        form_data = {'email': 'notanemail', 'password': 'short'}
        form = LoginForm(data=form_data)
        self.assertFalse(form.validate(), "Form should not validate with invalid data")
        if not form.validate():
            print("Form errors:", form.errors)
