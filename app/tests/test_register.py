from django.test import TestCase
from rest_framework.test import APIClient

REGISTER_URL = '/api/auth/register/'


class AuthRegisterApiTests(TestCase):
    """Test the authentication register module API"""

    def setUp(self):
        self.client = APIClient()

    def test_register_valid_user_success(self):
        """Test creating user with valid payload is successful"""
        payload = {
            'username': 'testuser',
            'password': 'testpass',
            'email': 'caio@gmail.com'
        }
        res = self.client.post(REGISTER_URL, payload)

        self.assertEqual(res.status_code, 201)
        self.assertIn('token', res.data)
        self.assertIn('user', res.data)

    def test_register_user_exists(self):
        """Test creating a user that already exists fails"""
        payload = {
            'username': 'testuser',
            'password': 'testpass',
            'email': 'caio@gmail.com'
        }
        self.client.post(REGISTER_URL, payload)

        res = self.client.post(REGISTER_URL, payload)

        self.assertEqual(res.status_code, 400)
        self.assertIn('username', res.data)

    def test_register_user_invalid(self):
        """Test creating user with invalid payload fails"""
        payload = {
            'username': '',
            'password': '',
            'email': ''
        }
        res = self.client.post(REGISTER_URL, payload)

        self.assertEqual(res.status_code, 400)

    def test_register_user_invalid_email(self):
        """Test creating user with invalid email fails"""
        payload = {
            'username': 'testuser',
            'password': 'testpass',
            'email': 'caio'
        }
        res = self.client.post(REGISTER_URL, payload)

        self.assertEqual(res.status_code, 400)

    def test_register_user_invalid_password(self):
        """Test creating user with invalid password fails"""
        payload = {
            'username': 'testuser',
            'password': '',
            'email': 'caio@gmail.com'
        }
        res = self.client.post(REGISTER_URL, payload)

        self.assertEqual(res.status_code, 400)
