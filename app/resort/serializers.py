"""
Serializers for resort APIs.
"""
from rest_framework import serializers

from core.models import Cottage, Amenities, Booking


class AmenitiesSerializer(serializers.ModelSerializer):
    """Serializer for Amenities."""

    class Meta:
        model = Amenities
        fields = '__all__'
        read_only_fields = ['id']

    def validate(self, data):
        """Validate amenities data."""
        if 'name' not in data or not data['name']:
            raise serializers.ValidationError('The name of the amenity is required.')
        return data


class BookingSerializer(serializers.ModelSerializer):
    """Serializer for Booking."""

    class Meta:
        model = Booking
        fields = '__all__'
        read_only_fields = ['id']

    def validate(self, data):
        """Validate booking data."""
        check_in = data.get('check_in')
        check_out = data.get('check_out')

        if check_in and check_out and check_in >= check_out:
            raise serializers.ValidationError('Check-out date must be after check-in date.')

        return data


class CottageSerializer(serializers.ModelSerializer):
    """Serializer for cottages."""
    amenities = AmenitiesSerializer(many=True, required=False)

    class Meta:
        model = Cottage
        fields = '__all__'
        read_only_fields = ['id']

    def _get_or_create_amenities(self, amenities, cottage):
        """Handle getting or creating amenities as needed."""
        auth_user = self.context['request'].user
        for amenity in amenities:
            name = amenity.get('name')
            additional_capacity = amenity.get('additional_capacity', 0)
            amenity_obj, created = Amenities.objects.get_or_create(
                user=auth_user,
                name=name,
                defaults={'additional_capacity': additional_capacity}
            )
            cottage.amenities.add(amenity_obj)

    def create(self, validated_data):
        """Create a cottage."""
        amenities = validated_data.pop('amenities', [])
        cottage = Cottage.objects.create(**validated_data)
        self._get_or_create_amenities(amenities, cottage)
        cottage.total_capacity = cottage.calculate_total_capacity()
        cottage.save()

        return cottage


class AvailabilityCheckSerializer(serializers.Serializer):
    cottage = serializers.IntegerField()
    check_in = serializers.DateField()
    check_out = serializers.DateField()

    def validate(self, data):
        check_in = data.get('check_in')
        check_out = data.get('check_out')

        if check_in >= check_out:
            raise serializers.ValidationError({
                'check_out': 'Check-out date must be later than check-in date.'
            })

        return data
