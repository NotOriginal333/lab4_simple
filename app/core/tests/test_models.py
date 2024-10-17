"""
Tests for models.
"""
from datetime import timedelta
from decimal import Decimal

from unittest.mock import patch

from django.test import TestCase
from django.contrib.auth import get_user_model

from core import models
from django.utils import timezone


def create_user(email='user@example.com', password='testpass123'):
    """Create and return a new user."""
    return get_user_model().objects.create_user(email, password)


class ModelTests(TestCase):
    """Test models."""

    def test_create_user_with_email_successful(self):
        """Test creating a user with an email is successful."""
        email = 'test@example.com'
        password = 'testpass123'
        user = get_user_model().objects.create_user(
            email=email,
            password=password
        )

        self.assertEqual(user.email, email)
        self.assertTrue(user.check_password(password))

    def test_new_user_email_normalized(self):
        """Test the email for a new user is normalized."""
        sample_emails = [
            ['test1@EXAMPLE.com', 'test1@example.com'],
            ['Test2@Example.com', 'Test2@example.com'],
            ['TEST3@EXAMPLE.COM', 'TEST3@example.com'],
            ['test4@example.COM', 'test4@example.com'],
        ]

        for email, expected in sample_emails:
            user = get_user_model().objects.create_user(email, 'samle123')
            self.assertEqual(user.email, expected)

    def test_new_user_without_email_raises_error(self):
        """Test that creating user with no email raises a ValueError."""
        with self.assertRaises(ValueError):
            get_user_model().objects.create_user('', 'test123')

    def test_create_superuser(self):
        """Test creating a superuser."""

        user = get_user_model().objects.create_superuser(
            'test@examle.com',
            'test123',
        )

        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)

    def test_create_cottage(self):
        """Test creating a cottage is successful."""
        user = create_user()
        cottage = models.Cottage.objects.create(
            name='Sample cottage name',
            base_capacity=5,
            price_per_night=Decimal('500.50'),
            user=user
        )

        self.assertEqual('Sample cottage name', cottage.name)
        self.assertEqual(5, cottage.base_capacity)
        self.assertEqual(Decimal(500.50), cottage.price_per_night)

    def test_create_amenity(self):
        """Test creating an amenity is successful."""
        user = create_user()
        amenity = models.Amenities.objects.create(
            name='Sample amenity name',
            additional_capacity=5,
            user=user
        )

        self.assertEqual('Sample amenity name', amenity.name)
        self.assertEqual(5, amenity.additional_capacity)

    def test_create_booking(self):
        """Test creating a booking is successful."""
        user = create_user()
        cottage = models.Cottage.objects.create(
            name='Sample cottage name',
            base_capacity=5,
            price_per_night=Decimal('500.50'),
            user=user
        )
        check_in = timezone.now().date() + timedelta(days=1)
        check_out = check_in + timedelta(days=2)
        booking = models.Booking.objects.create(
            cottage=cottage,
            check_in=check_in,
            check_out=check_out,
            customer_name="username",
            customer_email="example@example.com",
            user=user
        )

        self.assertEqual(booking.check_in, check_in)
        self.assertEqual(booking.check_out, check_out)
        self.assertEqual(booking.customer_name, "username")
        self.assertEqual(booking.cottage, cottage)
