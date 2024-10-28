"""
Tests for the Cottage API.
"""
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from core.models import Cottage, Amenities
from resort.serializers import CottageSerializer

COTTAGE_URL = reverse('resort:cottage-list')
REPORT_URL = reverse('resort:financial-report')
BOOKING_URL = reverse('resort:booking-list')


def detail_url(cottage_id):
    """Create and return a cottage detail URL."""
    return reverse('resort:cottage-detail', args=[cottage_id])


def create_user(email='user@example.com', password='testpass123'):
    """Create and return a user."""
    return get_user_model().objects.create_user(
        email=email,
        password=password
    )


def create_admin(email='admin@example.com', password='testpass123', is_staff=True):
    """Create and return an admin."""
    return get_user_model().objects.create_user(
        email=email,
        password=password,
        is_staff=is_staff
    )


def create_cottage(user, **params):
    """Create and return a cottage."""
    defaults = {
        'name': 'Test Cottage',
        'category': 'standard',
        'base_capacity': 5,
        'price_per_night': Decimal('100')
    }
    defaults.update(params)

    cottage = Cottage.objects.create(user=user, **defaults)
    return cottage


class PublicCottageAPITests(TestCase):
    """Test unauthenticated API requests."""

    def setUp(self):
        self.client = APIClient()

    def test_auth_not_required(self):
        """Test that auth is not required for retrieving cottages."""
        res = self.client.get(COTTAGE_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)


class AdminCottageApiTest(TestCase):
    """Test admin API requests."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_admin()
        self.client.force_authenticate(self.user)

    def test_update_cottage(self):
        """Test updating a cottage for admin."""
        cottage = create_cottage(user=self.user, name='House')

        payload = {'name': 'Cabin'}
        url = detail_url(cottage.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        cottage.refresh_from_db()
        self.assertEqual(cottage.name, payload['name'])

    def test_delete_cottage(self):
        """Test deleting a cottage for admin."""
        cottage = create_cottage(user=self.user)

        url = detail_url(cottage.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        cottages = Cottage.objects.filter(user=self.user)
        self.assertFalse(cottages.exists())

    def test_create_cottage_with_new_amenities(self):
        """Test creating a cottage with new amenities."""
        payload = {
            'name': 'Test Cottage',
            'base_capacity': 5,
            'category': 'standard',
            'user': self.user.id,
            'price_per_night': Decimal('100.0'),
            'amenities': [
                {
                    'name': "Wi-Fi",
                    'additional_capacity': 0
                },
                {
                    'name': "Sofa",
                    'additional_capacity': 0
                }
            ],
        }
        res = self.client.post(COTTAGE_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        cottages = Cottage.objects.filter(user=self.user)
        self.assertEqual(cottages.count(), 1)
        cottage = cottages[0]
        self.assertEqual(cottage.amenities.count(), 2)
        for amenity in payload['amenities']:
            exists = cottage.amenities.filter(
                name=amenity['name'],
                user=self.user
            ).exists()
            self.assertTrue(exists)

    def test_create_cottage_with_existing_amenities(self):
        """Test creating a cottage with existing amenities."""
        amenity_sofa = Amenities.objects.create(user=self.user, name='Sofa')
        self.assertEqual("Sofa", amenity_sofa.name)
        payload = {
            'name': 'Test Cottage',
            'base_capacity': 5,
            'user': self.user.id,
            'price_per_night': Decimal('100'),
            'amenities': [{'name': 'Wi-Fi', },
                          {'name': 'Sofa'}],
        }

        res = self.client.post(COTTAGE_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        cottages = Cottage.objects.filter(user=self.user)
        self.assertEqual(cottages.count(), 1)
        cottage = cottages[0]
        self.assertEqual(cottage.amenities.count(), 2)
        self.assertIn(amenity_sofa, cottage.amenities.all())
        for amenity in payload['amenities']:
            exists = cottage.amenities.filter(
                name=amenity['name'],
                user=self.user
            )
            self.assertTrue(exists)

    def test_create_amenity_on_update(self):
        """Test updating an amenity on updating a cottage."""
        cottage = create_cottage(user=self.user)
        payload = {'amenities': [{'name': 'Sofa', 'additional_capacity': 0}]}
        url = detail_url(cottage.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_amenity = Amenities.objects.get(user=self.user, name='Sofa')
        self.assertIn(new_amenity, cottage.amenities.all())

    def test_update_cottage_assign_amenity(self):
        """Test assigning an existing amenity when updating a cottage."""
        amenity_wifi = Amenities.objects.create(user=self.user, name='Wi-Fi', additional_capacity=0)
        cottage = create_cottage(user=self.user)
        cottage.amenities.add(amenity_wifi)

        amenity_sofa = Amenities.objects.create(user=self.user, name='Sofa', additional_capacity=0)
        payload = {'amenities': [{'name': 'Sofa'}]}
        url = detail_url(cottage.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(amenity_sofa, cottage.amenities.all())
        self.assertNotIn(amenity_wifi, cottage.amenities.all())

    def test_clear_cottage_amenities(self):
        """Test clearing a cottage amenities."""
        amenity = Amenities.objects.create(user=self.user, name='Kitchen', additional_capacity=0)
        cottage = create_cottage(user=self.user)
        cottage.amenities.add(amenity)
        payload = {'amenities': []}
        url = detail_url(cottage.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(cottage.amenities.count(), 0)

    def test_filter_by_amenities(self):
        """Test filtering cottages by amenities."""
        c1 = create_cottage(user=self.user, name='Big House')
        c2 = create_cottage(user=self.user, name='Family House')
        amenity1 = Amenities.objects.create(user=self.user, name='Sauna')
        amenity2 = Amenities.objects.create(user=self.user, name='Wi-Fi')

        c1.amenities.add(amenity1)
        c2.amenities.add(amenity2)
        c3 = create_cottage(user=self.user, name='Nice House')

        params = {'amenities': f'{amenity1.id}, {amenity2.id}'}
        res = self.client.get(COTTAGE_URL, params)

        s1 = CottageSerializer(c1)
        s2 = CottageSerializer(c2)
        s3 = CottageSerializer(c3)

        self.assertIn(s1.data, res.data)
        self.assertIn(s2.data, res.data)
        self.assertNotIn(s3.data, res.data)

    def test_filter_by_category(self):
        """Test filtering cottages by category."""
        c1 = create_cottage(user=self.user, name='Big House', category="luxury")
        c2 = create_cottage(user=self.user, name='Family House', category="luxury")
        c3 = create_cottage(user=self.user, name='Nice House', category="standard")

        params = {'category': "luxury"}
        res = self.client.get(COTTAGE_URL, params)

        s1 = CottageSerializer(c1)
        s2 = CottageSerializer(c2)
        s3 = CottageSerializer(c3)

        self.assertIn(s1.data, res.data)
        self.assertIn(s2.data, res.data)
        self.assertNotIn(s3.data, res.data)


class PrivateCottageApiTest(TestCase):
    """Test authenticated API requests."""

    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrieve_cottages(self):
        """Test retrieving a list of cottages."""
        create_cottage(user=self.user)
        create_cottage(user=self.user)

        res = self.client.get(COTTAGE_URL)

        cottages = Cottage.objects.all()
        serializer = CottageSerializer(cottages, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_cottages_not_limited_to_user(self):
        """Test list of cottages is not limited for authenticated user."""
        other_user = create_user(email='user2@example.com')
        create_cottage(user=other_user, name="Cabin")
        cottage = create_cottage(user=self.user, name='House')

        res = self.client.get(COTTAGE_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)
        self.assertEqual(res.data[0]['name'], cottage.name)
        self.assertEqual(res.data[0]['id'], cottage.id)


class AdditionalFunctionalityTests(TestCase):
    """Tests for additional functions."""

    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrieve_financial_report(self):
        """Test retrieving a financial report."""
        cottage1 = create_cottage(user=self.user)
        cottage2 = create_cottage(user=self.user)

        payload = {
            'cottage': cottage1.id,
            'check_in': '2024-10-01',
            'check_out': '2024-10-05',
            'customer_name': 'John Doe',
            'customer_email': 'john.doe@example.com',
            'user': self.user.id
        }
        self.client.post(BOOKING_URL, payload, format='json')

        amenity1 = Amenities.objects.create(user=self.user, name='Sauna', expenses=Decimal('50'))
        amenity2 = Amenities.objects.create(user=self.user, name='Wi-Fi', expenses=Decimal('10'))

        cottage1.base_expenses = Decimal('100')
        cottage2.base_expenses = Decimal('100')
        cottage1.save()
        cottage2.save()
        cottage1.amenities.add(amenity1)
        cottage1.amenities.add(amenity2)
        cottage2.amenities.add(amenity2)

        res = self.client.get(REPORT_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['total_expenses'], Decimal('270'))
        self.assertEqual(res.data['total_income'], Decimal('400'))
        self.assertEqual(res.data['net_profit'], Decimal('130'))
