# import unittest
# from flask import Flask
# from app import create_app, db

# class ViewTestCase(unittest.TestCase):
#     def setUp(self):
#         self.app = create_app()
#         self.app.config['TESTING'] = True
#         self.app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing
#         self.client = self.app.test_client()
#         self.app_context = self.app.app_context()
#         self.app_context.push()

#     def tearDown(self):
#         self.app_context.pop()

#     def test_user_profile_page(self):
#         # Attempt to log in
#         login_response = self.client.post('/login', data={
#             'email': 'user@example.com',
#             'password': 'correcthorsebatterystaple'
#         }, follow_redirects=True)
        
#         # Check if login was successful
#         self.assertEqual(login_response.status_code, 200, "Login failed, check setup or login handling")

#         # Now, access the profile page
#         profile_response = self.client.get('/profile', follow_redirects=True)
#         self.assertEqual(profile_response.status_code, 200, "Failed to access profile page")
#         self.assertIn('Your Profile', profile_response.data.decode('utf-8'), "Profile page content not as expected")
