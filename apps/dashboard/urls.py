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
    path('staff/', views.staff_list_view, name='staff_list'),
    path('staff/add/', views.staff_add_view, name='staff_add'),
    path('staff/<int:pk>/', views.staff_detail_view, name='staff_detail'),
    path('staff/<int:pk>/edit/', views.staff_edit_view, name='staff_edit'),
    path('staff/<int:pk>/schedule/', views.staff_schedule_view, name='staff_schedule'),
    path('staff/<int:pk>/payroll/', views.staff_payroll_view, name='staff_payroll'),
    path('staff/<int:pk>/leaves/', views.staff_leave_view, name='staff_leaves'),
    path('payroll/', views.payroll_list_view, name='payroll'),
    path('availability/', views.availability_view, name='availability'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/gallery/<int:pk>/delete/', views.gallery_image_delete, name='gallery_image_delete'),
    path('settings/', views.settings_view, name='settings'),
    path('support/', views.support_view, name='support'),
]

