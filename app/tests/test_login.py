from django.test import TestCase
from rest_framework.test import APIClient

REGISTER_URL = '/api/auth/register/'
LOGIN_URL = '/api/auth/login/'


class AuthLoginApiTests(TestCase):
    """Test the authentication login module API"""

    def setUp(self):
        self.client = APIClient()

    def register_user(self):
        payload = {
            'username': 'testuser',
            'password': 'testpass',
            'email': 'caio@gmail.com'
        }
        res = self.client.post(REGISTER_URL, payload)
        token = res.data['token']
        return token

    def test_login_user(self):
        """Test login a user"""
        self.register_user()
        payload = {
            'username': 'testuser',
            'password': 'testpass'
        }
        res = self.client.post(LOGIN_URL, payload)

        self.assertEqual(res.status_code, 200)
        self.assertIn('token', res.data)
        self.assertIn('user', res.data)

    def test_login_user_invalid(self):
        payload = {
            'username': '',
            'password': ''
        }
        res = self.client.post(LOGIN_URL, payload)

        self.assertEqual(res.status_code, 400)
        self.assertIn('username', res.data)

    def test_login_user_invalid_password(self):
        payload = {
            'username': 'testuser',
            'password': ''
        }
        res = self.client.post(LOGIN_URL, payload)

        self.assertEqual(res.status_code, 400)
