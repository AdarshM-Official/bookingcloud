from django.urls import path
from . import views

app_name = 'website'

urlpatterns = [
    path('', views.LandingPageView.as_view(), name='index'),
    path('auth/', views.authentication_view, name='auth'),
    path('logout/', views.logout_view, name='logout'),
    path('discover/', views.DiscoveryView.as_view(), name='discover'),
    path('business/<int:business_id>/', views.business_profile_view, name='business_profile'),
    path('book/<int:service_id>/', views.book_service, name='book_service'),
    path('api/slots/<int:service_id>/', views.api_get_slots, name='api_slots'),
    path('my-bookings/', views.customer_bookings_view, name='my_bookings'),
    path('my-bookings/<int:booking_id>/reply/', views.reply_booking_view, name='reply_booking'),
]
