"""
Views for resort APIs.
"""
from drf_spectacular.utils import (
    extend_schema_view,
    extend_schema,
    OpenApiParameter,
    OpenApiTypes,
)
from rest_framework import (
    viewsets,
    mixins,
    status, generics,
)
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser

from core.models import (
    Cottage,
    Amenities,
    Booking,
)
from resort import serializers


@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter(
                'amenities',
                OpenApiTypes.STR,
                description="Comma separated list of amenities IDs to filter",
            ),
            OpenApiParameter(
                'category',
                OpenApiTypes.STR,
                description='Category of the cottage (e.g. standard, luxury)',
            ),
        ]
    )
)
class CottageViewSet(viewsets.ModelViewSet):
    """Manage cottages in the database."""
    serializer_class = serializers.CottageSerializer
    queryset = Cottage.objects.all()
    authentication_classes = (TokenAuthentication,)
    permission_classes = (AllowAny,)

    def get_permissions(self):
        """Set permissions based on the action."""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [AllowAny]
        return [permission() for permission in permission_classes]

    def _params_to_ints(self, qs):
        """Convert a list of strings to integers."""
        return [int(str_id) for str_id in qs.split(',')]

    def get_queryset(self):
        """Filter queryset for user."""
        assigned_only = bool(
            int(self.request.query_params.get('assigned_only', 0))
        )
        queryset = self.queryset
        if assigned_only:
            queryset = queryset.filter(cottage__isnull=False)
        amenities = self.request.query_params.get('amenities')
        if amenities:
            amenity_ids = self._params_to_ints(amenities)
            queryset = queryset.filter(amenities__id__in=amenity_ids)

        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category__iexact=category)
        return queryset.order_by('-name').distinct()


class BaseCottageAttrViewSet(mixins.UpdateModelMixin,
                             mixins.DestroyModelMixin,
                             mixins.ListModelMixin,
                             viewsets.GenericViewSet):
    """Base viewset for cottage attributes."""
    authentication_classes = (TokenAuthentication,)
    permission_classes = (AllowAny,)

    def get_permissions(self):
        """Set permissions based on the action."""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [AllowAny]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        """Filter queryset for user."""
        assigned_only = bool(
            int(self.request.query_params.get('assigned_only', 0))
        )
        queryset = self.queryset
        if assigned_only:
            queryset = queryset.filter(cottage__isnull=False)
        return queryset.order_by('-name').distinct()


class AmenitiesViewSet(BaseCottageAttrViewSet,
                       mixins.CreateModelMixin):
    """Manage amenities in the database."""
    serializer_class = serializers.AmenitiesSerializer
    queryset = Amenities.objects.all()


class BookingViewSet(mixins.UpdateModelMixin,
                     mixins.DestroyModelMixin,
                     mixins.ListModelMixin,
                     viewsets.GenericViewSet,
                     mixins.CreateModelMixin):
    """Manage booking in the database."""
    authentication_classes = (TokenAuthentication,)
    serializer_class = serializers.BookingSerializer
    queryset = Booking.objects.all()

    def get_permissions(self):
        """Set permissions based on the action."""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [AllowAny]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        """Filter queryset for user."""
        assigned_only = bool(
            int(self.request.query_params.get('assigned_only', 0))
        )
        queryset = self.queryset
        if assigned_only:
            queryset = queryset.filter(cottage__isnull=False)
        return queryset.order_by('-check_in').distinct()


class CheckAvailabilityView(generics.GenericAPIView):
    serializer_class = serializers.AvailabilityCheckSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cottage_id = serializer.validated_data['cottage']
        check_in = serializer.validated_data['check_in']
        check_out = serializer.validated_data['check_out']

        cottage = Cottage.objects.get(id=cottage_id)

        overlapping_bookings = Booking.objects.filter(
            cottage=cottage,
            check_in__lt=check_out,
            check_out__gt=check_in
        )

        if overlapping_bookings.exists():
            return Response({
                'available': False,
                'message': 'The cottage is not available for the selected dates.'
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'available': True,
                'message': 'The cottage is available for the selected dates.'
            }, status=status.HTTP_200_OK)
