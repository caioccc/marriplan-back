from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from app.models import WeddingIdentity


WEDDING_IDENTITY_URL = '/api/wedding-identity/'


class WeddingIdentityApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass',
        )
        self.client.force_authenticate(user=self.user)

    def test_get_returns_404_when_identity_is_missing(self):
        response = self.client.get(WEDDING_IDENTITY_URL)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(WeddingIdentity.objects.count(), 0)

    def test_post_creates_wedding_identity(self):
        payload = {
            'selected_style': 'classico',
            'wedding_size': 'micro',
            'dress_code': 'social',
            'palette': [
                {'id': 1, 'hex': '#e3c1b5', 'name': 'Soft Rose Gold', 'isPrimary': True},
            ],
        }

        response = self.client.post(WEDDING_IDENTITY_URL, payload, format='json')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['selected_style'], 'classico')
        self.assertEqual(response.data['wedding_size'], 'micro')
        self.assertEqual(response.data['dress_code'], 'social')
        self.assertEqual(len(response.data['palette']), 1)
        self.assertEqual(WeddingIdentity.objects.count(), 1)
        self.assertEqual(WeddingIdentity.objects.get().wedding_profile.user, self.user)

    def test_patch_updates_wedding_identity_on_singleton_route(self):
        create_payload = {
            'selected_style': 'classico',
            'wedding_size': 'micro',
            'dress_code': 'social',
            'palette': [
                {'id': 1, 'hex': '#e3c1b5', 'name': 'Soft Rose Gold', 'isPrimary': True},
            ],
        }
        self.client.post(WEDDING_IDENTITY_URL, create_payload, format='json')

        patch_payload = {
            'selected_style': 'romantico',
            'wedding_size': 'medio',
            'palette': [
                {'id': 2, 'hex': '#4d602d', 'name': 'Verde Oliva', 'isPrimary': True},
            ],
        }

        response = self.client.patch(WEDDING_IDENTITY_URL, patch_payload, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['selected_style'], 'romantico')
        self.assertEqual(response.data['wedding_size'], 'medio')
        self.assertEqual(response.data['dress_code'], 'social')
        self.assertEqual(response.data['palette'][0]['hex'], '#4d602d')
