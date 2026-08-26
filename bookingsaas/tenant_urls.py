from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from apps.website import tenant_views

urlpatterns = [
    path('', tenant_views.tenant_home, name='tenant_home'),
    path('services/', tenant_views.tenant_services, name='tenant_services'),
    path('staff/', tenant_views.tenant_staff, name='tenant_staff'),
    path('book/<int:service_id>/', tenant_views.tenant_book_service, name='tenant_book_service'),
    path('book/multi/', tenant_views.tenant_book_multi_service, name='tenant_book_multi_service'),
    path('my-bookings/', tenant_views.tenant_my_bookings, name='tenant_my_bookings'),
    path('api/slots/<int:service_id>/', tenant_views.tenant_api_get_slots, name='tenant_api_get_slots'),
    path('api/slots/multi/', tenant_views.tenant_api_get_multi_slots, name='tenant_api_get_multi_slots'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
