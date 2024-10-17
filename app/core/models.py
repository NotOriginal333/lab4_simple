from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin
)
from django.conf import settings
from rest_framework.exceptions import ValidationError


class UserManager(BaseUserManager):
    """Manager for users."""

    def create_user(self, email, password=None, **extra_fields):
        """Create, save and return a new user."""
        if not email:
            raise ValueError('Users must have an email address')
        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, email, password):
        """Create and return a new superuser."""
        user = self.create_user(email, password)
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)

        return user


class User(AbstractBaseUser, PermissionsMixin):
    """User in the system."""
    email = models.EmailField(max_length=255, unique=True)
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'email'


class Amenities(models.Model):
    """Amenities for cottages and hotel."""
    name = models.CharField(max_length=100)
    additional_capacity = models.IntegerField(default=0)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    def __str__(self):
        return f"{self.name} (+{self.additional_capacity})"


class Cottage(models.Model):
    """Cottage object."""
    CATEGORY_CHOICES = [
        ('standard', 'Standard'),
        ('luxury', 'Luxury'),
    ]
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=255, choices=CATEGORY_CHOICES, default='standard')
    base_capacity = models.IntegerField()
    amenities = models.ManyToManyField(Amenities)
    price_per_night = models.DecimalField(max_digits=10, decimal_places=2)
    total_capacity = models.IntegerField(editable=False, default=0)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    def calculate_total_capacity(self):
        """Calculate the total capacity of the cottage including amenities."""
        additional_capacity = sum(amenity.additional_capacity for amenity in self.amenities.all())
        self.total_capacity = self.base_capacity + additional_capacity

    def __str__(self):
        return f'{self.name}, {self.category}, max. guests - {self.total_capacity}, price - {self.price_per_night}'


class Booking(models.Model):
    """Booking model for managing cottage reservations."""
    cottage = models.ForeignKey(Cottage, on_delete=models.CASCADE)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    check_in = models.DateField()
    check_out = models.DateField()
    customer_name = models.CharField(max_length=255)
    customer_email = models.EmailField()
    is_confirmed = models.BooleanField(default=False)

    def clean(self):
        overlapping_bookings = Booking.objects.filter(
            cottage=self.cottage,
            check_in__lt=self.check_out,
            check_out__gt=self.check_in,
        ).exclude(id=self.id)

        if overlapping_bookings.exists():
            raise ValidationError('This cottage is already booked for the selected dates.')

        customer_bookings = Booking.objects.filter(
            customer_email=self.customer_email,
            check_in__lt=self.check_out,
            check_out__gt=self.check_in
        ).exclude(id=self.id)

        if customer_bookings.exists():
            raise ValidationError('This customer already has a booking in another cottage for the selected dates.')

        if self.check_in >= self.check_out:
            raise ValidationError('Check-out date must be later than check-in date.')

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Booking for {self.customer_name} in {self.cottage.name}'
