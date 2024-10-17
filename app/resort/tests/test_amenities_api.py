"""
Tests for the Amenities API.
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Amenities, Cottage
from resort.serializers import AmenitiesSerializer

AMENITIES_URL = reverse('resort:amenities-list')


def detail_url(amenities_id):
    """Create and return an amenities detail URL."""
    return reverse('resort:amenities-detail', args=[amenities_id])


def create_user(email='user@example.com', password='testpass123'):
    """Create and return a user."""
    return get_user_model().objects.create_user(
        email=email,
        password=password
    )


def create_admin(email='admin@example.com', password='testpass123', is_staff=True):
    """Create and return a user."""
    return get_user_model().objects.create_user(
        email=email,
        password=password,
        is_staff=is_staff
    )


class PublicAmenitiesApiTest(TestCase):
    """Test unauthenticated API requests."""

    def setUp(self):
        self.client = APIClient()

    def test_auth_not_required(self):
        """Test that auth is not required for retrieving amenities."""
        res = self.client.get(AMENITIES_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)


class AdminAmenitiesApiTest(TestCase):
    """Test admin API requests."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_admin()
        self.client.force_authenticate(self.user)

    def test_update_amenity(self):
        """Test updating an amenity for admin."""
        amenity = Amenities.objects.create(user=self.user, name='Good Dinner')

        payload = {'name': 'Pool'}
        url = detail_url(amenity.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        amenity.refresh_from_db()
        self.assertEqual(amenity.name, payload['name'])

    def test_delete_amenity(self):
        """Test deleting an amenity for admin."""
        amenity = Amenities.objects.create(user=self.user, name='Big Bed')

        url = detail_url(amenity.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        amenities = Amenities.objects.filter(user=self.user)
        self.assertFalse(amenities.exists())


class PrivateAmenitiesApiTest(TestCase):
    """Test authenticated API requests."""

    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrieve_amenities(self):
        """Test retrieving a list of amenities."""
        Amenities.objects.create(user=self.user, name='Wi-Fi')
        Amenities.objects.create(user=self.user, name='Sea')

        res = self.client.get(AMENITIES_URL)

        amenities = Amenities.objects.all().order_by('-name')
        serializer = AmenitiesSerializer(amenities, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_amenities_not_limited_to_user(self):
        """Test list of amenities is not limited for authenticated user."""
        user2 = create_user(email='user2@example.com')
        Amenities.objects.create(user=user2, name='Clear')
        amenity = Amenities.objects.create(user=self.user, name='Comfortable')

        res = self.client.get(AMENITIES_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)
        self.assertEqual(res.data[0]['name'], amenity.name)
        self.assertEqual(res.data[0]['id'], amenity.id)

    def test_filter_amenities_assigned_to_cottages(self):
        """Test listing amenities by those assigned to cottages."""
        amenity1 = Amenities.objects.create(user=self.user, name='Big')
        amenity2 = Amenities.objects.create(user=self.user, name='Pretty')
        cottage1 = Cottage.objects.create(
            name='Big House',
            base_capacity=5,
            price_per_night=Decimal('5.50'),
            user=self.user
        )
        cottage1.amenities.add(amenity1)

        res = self.client.get(AMENITIES_URL, {'assigned_only': 1})

        s1 = AmenitiesSerializer(amenity1)
        s2 = AmenitiesSerializer(amenity2)

        self.assertIn(s1.data, res.data)
        self.assertNotIn(s2.data, res.data)

    def test_filtered_amenities_unique(self):
        """Test filtered amenities return a unique list."""
        amenity = Amenities.objects.create(user=self.user, name='Big Beds')
        Amenities.objects.create(user=self.user, name='Wi-Fi')
        cottage1 = Cottage.objects.create(
            name='Big House',
            base_capacity=5,
            price_per_night=Decimal('5.50'),
            user=self.user
        )
        cottage2 = Cottage.objects.create(
            name='Nice House',
            base_capacity=3,
            price_per_night=Decimal('50.50'),
            user=self.user
        )
        cottage1.amenities.add(amenity)
        cottage2.amenities.add(amenity)

        res = self.client.get(AMENITIES_URL, {'assigned_only': 1})

        self.assertEqual(len(res.data), 1)
