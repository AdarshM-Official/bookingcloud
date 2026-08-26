from django.contrib import admin
from .models import Business, BusinessTimeOff, BusinessImage, Service, Booking, Staff, StaffAvailability, StaffBreak, StaffTimeOff, StaffPayroll

admin.site.register(Business)
admin.site.register(BusinessImage)
admin.site.register(Service)
admin.site.register(Booking)

@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'business', 'job_title', 'is_active', 'base_salary')
    search_fields = ('first_name', 'last_name', 'email', 'business__business_name')
    list_filter = ('is_active', 'business', 'salary_type')

@admin.register(StaffAvailability)
class StaffAvailabilityAdmin(admin.ModelAdmin):
    list_display = ('staff', 'day_of_week', 'start_time', 'end_time', 'is_working')
    list_filter = ('day_of_week', 'is_working', 'staff__business')

@admin.register(StaffBreak)
class StaffBreakAdmin(admin.ModelAdmin):
    list_display = ('staff', 'day_of_week', 'start_time', 'end_time')

@admin.register(StaffTimeOff)
class StaffTimeOffAdmin(admin.ModelAdmin):
    list_display = ('staff', 'start_date', 'end_date', 'leave_type', 'status')
    list_filter = ('leave_type', 'status')

@admin.register(StaffPayroll)
class StaffPayrollAdmin(admin.ModelAdmin):
    list_display = ('staff', 'month', 'net_payable', 'amount_paid', 'status')
    list_filter = ('status', 'month')
@admin.register(BusinessTimeOff)
class BusinessTimeOffAdmin(admin.ModelAdmin):
    list_display = ('business', 'start_date', 'end_date', 'reason')
