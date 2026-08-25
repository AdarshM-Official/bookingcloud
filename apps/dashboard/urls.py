from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_view, name='index'),
    path('onboarding/', views.business_onboarding, name='onboarding'),
    path('calendar/', views.calendar_view, name='calendar'),
    path('bookings/', views.bookings_view, name='bookings'),
    path('bookings/<int:pk>/manage/', views.booking_manage_view, name='booking_manage'),
    path('bookings/<int:pk>/status/<str:status>/', views.update_booking_status, name='update_booking_status'),
    path('services/', views.service_list, name='services'),
    path('services/add/', views.service_create, name='service_add'),
    path('services/<int:pk>/delete/', views.service_delete, name='service_delete'),
    path('customers/', views.customers_view, name='customers'),
    path('availability/', views.availability_view, name='availability'),
    path('analytics/', views.analytics_view, name='analytics'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/gallery/<int:pk>/delete/', views.gallery_image_delete, name='gallery_image_delete'),
    path('settings/', views.settings_view, name='settings'),
]
