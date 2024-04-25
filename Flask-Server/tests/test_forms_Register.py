import unittest
from flask import Flask
from app import create_app, db
from app.forms import RegistrationForm

class TestRegistrationForm(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF tokens for testing
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_valid_registration_form(self):
        # Using the test client to create a request context
        with self.app.test_client() as client:
            # Prepare form data
            form_data = {
                'email': 'user@example.com',
                'first_name': 'John',
                'last_name': 'Doe',
                'password': 'securepassword123',
                'confirm_password': 'securepassword123'
            }
            # Directly use the data to populate the form
            form = RegistrationForm(data=form_data)
            # Validate the form
            is_valid = form.validate()
            # Check if the form is not valid and print errors
            if not is_valid:
                print("Form errors:", form.errors)
            self.assertTrue(is_valid)



# Run the tests
if __name__ == '__main__':
    unittest.main()
