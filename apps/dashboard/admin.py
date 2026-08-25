from django.contrib import admin
from .models import Business, Service

@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ('business_name', 'owner', 'category', 'city', 'is_active', 'created_at')
    search_fields = ('business_name', 'owner__username', 'category', 'city')
    list_filter = ('is_active', 'category')

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('service_name', 'business', 'price', 'duration', 'is_active')
    search_fields = ('service_name', 'business__business_name')
    list_filter = ('is_active',)

