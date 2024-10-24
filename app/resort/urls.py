"""
URL mapping for the resort app.
"""
from django.urls import (
    path,
    include
)
from rest_framework.routers import DefaultRouter

from resort import views

router = DefaultRouter()
router.register('cottages', views.CottageViewSet)
router.register('amenities', views.AmenitiesViewSet)
router.register('booking', views.BookingViewSet)

app_name = 'resort'

urlpatterns = [
    path('', include(router.urls)),
    path('check-availability/', views.CheckAvailabilityView.as_view(), name='check-availability'),
    path('cottage-availability/', views.CottageAvailabilityView.as_view(), name='cottage-availability'),
    path('financial-report/', views.FinancialReportView.as_view(), name='financial-report'),
]
