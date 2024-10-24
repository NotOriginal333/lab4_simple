"""
Views for resort APIs.
"""
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

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
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser

from core.models import (
    Cottage,
    Amenities,
    Booking,
)
from resort import serializers
from rest_framework.views import APIView


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
    """View for checking availability of cottage in dates chosen by user."""
    serializer_class = serializers.CheckAvailabilitySerializer

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


class CottageAvailabilityView(generics.GenericAPIView):
    """View for getting the cottage available dates to years end."""
    serializer_class = serializers.CottageAvailabilitySerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cottage_id = serializer.validated_data['cottage']

        try:
            cottage = Cottage.objects.get(id=cottage_id)
        except Cottage.DoesNotExist:
            return Response({
                'message': 'Cottage not found.'
            }, status=status.HTTP_404_NOT_FOUND)

        bookings = Booking.objects.filter(cottage=cottage).order_by('check_in')

        available_dates = []

        current_date = timezone.now().date()
        end_of_year = current_date.replace(month=12, day=31)

        last_end_date = current_date

        for booking in bookings:
            if last_end_date < booking.check_in:
                available_dates.append({
                    'from': last_end_date,
                    'to': booking.check_in
                })

            last_end_date = max(last_end_date, booking.check_out)

        if last_end_date <= end_of_year:
            available_dates.append({
                'from': last_end_date,
                'to': end_of_year
            })

        return Response({
            'available_dates': available_dates
        }, status=status.HTTP_200_OK)


class FinancialReportView(APIView):
    """View to calculate and return total income and expenses for cottages."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.is_authenticated:
            raise PermissionDenied('Authentication required to view financial summary.')

        total_income = Booking.objects.filter(cottage__user=request.user).aggregate(total=Sum('price'))[
                           'total'] or Decimal('0')

        total_expenses = Cottage.objects.filter(user=request.user).aggregate(total=Sum('expenses'))['total'] or Decimal(
            '0')

        net_profit = total_income - total_expenses

        return Response({
            'total_income': total_income,
            'total_expenses': total_expenses,
            'net_profit': net_profit
        })
