from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from .models import Business, Service, Booking
import datetime

@login_required
def dashboard_view(request):
    if request.user.role != 'business':
        return redirect('website:discover')
    
    try:
        business = request.user.business
    except Business.DoesNotExist:
        return redirect('dashboard:onboarding')
    
    # Auto-fill missing payrolls for the current month
    from .models import Staff, StaffPayroll
    import datetime
    today = datetime.date.today()
    current_month = today.replace(day=1)
    
    active_staff = Staff.objects.filter(business=business, is_active=True)
    existing_payrolls = StaffPayroll.objects.filter(
        staff__in=active_staff, 
        month=current_month
    ).values_list('staff_id', flat=True)
    
    for staff in active_staff:
        if staff.id not in existing_payrolls:
            StaffPayroll.objects.create(
                staff=staff,
                month=current_month,
                base_amount=staff.base_salary,
                incentives=0,
                deductions=0,
                amount_paid=0
            )
            
    # Calculate pending payrolls for notifications
    pending_payrolls = StaffPayroll.objects.filter(
        staff__business=business, 
        status__in=['pending', 'partially_paid']
    )
    pending_payroll_count = pending_payrolls.count()
    pending_payroll_amount = sum(p.net_payable - p.amount_paid for p in pending_payrolls)
    
    services = business.services.all()
    context = {
        'business': business,
        'services': services,
        'pending_payroll_count': pending_payroll_count,
        'pending_payroll_amount': pending_payroll_amount,
    }
    return render(request, "dashboard/index.html", context)

@login_required
def business_onboarding(request):
    if request.user.role != 'business':
        return redirect('website:discover')
        
    if hasattr(request.user, 'business'):
        return redirect('dashboard:index')

    if request.method == 'POST':
        business_name = request.POST.get('business_name')
        category = request.POST.get('category')
        description = request.POST.get('description', '')
        phone = request.POST.get('phone', '')
        email = request.POST.get('email', '')
        address = request.POST.get('address', '')
        city = request.POST.get('city', '')

        Business.objects.create(
            owner=request.user,
            business_name=business_name,
            category=category,
            description=description,
            phone=phone,
            email=email,
            address=address,
            city=city
        )
        return redirect('dashboard:index')

    return render(request, 'dashboard/onboarding.html')

@login_required
def service_list(request):
    if request.user.role != 'business':
        return redirect('website:discover')
        
    try:
        business = request.user.business
    except Business.DoesNotExist:
        return redirect('dashboard:onboarding')

    services = business.services.all()
    return render(request, 'dashboard/services.html', {'business': business, 'services': services})

@login_required
def service_create(request):
    if request.user.role != 'business':
        return redirect('website:discover')
        
    try:
        business = request.user.business
    except Business.DoesNotExist:
        return redirect('dashboard:onboarding')

    if request.method == 'POST':
        service_name = request.POST.get('service_name', '').strip()
        description = request.POST.get('description', '').strip()
        duration = request.POST.get('duration')
        price = request.POST.get('price')

        if Service.objects.filter(business=business, service_name__iexact=service_name).exists():
            messages.error(request, f'This service "{service_name}" already exists. You can edit the existing service instead.')
        else:
            Service.objects.create(
                business=business,
                service_name=service_name,
                description=description,
                duration=duration,
                price=price
            )
            messages.success(request, 'Service added successfully!')
            return redirect('dashboard:services')

    from .utils.service_suggestions import get_service_suggestions
    suggestions = get_service_suggestions(business.category)
    
    # Existing service names (case insensitive) to hide/disable suggestions
    existing_service_names = set(business.services.values_list('service_name', flat=True))
    existing_lower = {name.lower() for name in existing_service_names}
    
    # Filter out suggestions that are already added
    available_suggestions = [s for s in suggestions if s['name'].lower() not in existing_lower]

    context = {
        'business': business,
        'suggestions': available_suggestions,
    }
    return render(request, 'dashboard/service_form.html', context)

@login_required
def service_delete(request, pk):
    if request.user.role != 'business':
        return redirect('website:discover')
        
    service = get_object_or_404(Service, pk=pk, business=request.user.business)
    service.delete()
    messages.success(request, 'Service deleted.')
    return redirect('dashboard:services')

def _get_business_or_redirect(request):
    if request.user.role != 'business':
        return None
    try:
        return request.user.business
    except Business.DoesNotExist:
        return None

@login_required
def calendar_view(request):
    business = _get_business_or_redirect(request)
    if not business: return redirect('dashboard:onboarding')
    
    import json
    bookings = business.bookings.all()
    events = []
    for booking in bookings:
        # Support both single-service and multi-service bookings
        if booking.service:
            service_label = booking.service.service_name
        elif booking.services.exists():
            service_label = ", ".join(s.service_name for s in booking.services.all())
        else:
            service_label = "Appointment"

        events.append({
            'title': f"{service_label} - {booking.customer.get_full_name() or booking.customer.username}",
            'start': f"{booking.date.isoformat()}T{booking.start_time.isoformat()}",
            'end': f"{booking.date.isoformat()}T{booking.end_time.isoformat()}",
            'url': f"/dashboard/bookings/{booking.id}/",
            'className': f"status-{booking.status}"
        })
        
    context = {
        'business': business,
        'events_json': json.dumps(events)
    }
    return render(request, 'dashboard/calendar.html', context)

@login_required
def bookings_view(request):
    business = _get_business_or_redirect(request)
    if not business: return redirect('dashboard:onboarding')
    
    bookings = business.bookings.all().order_by('-date', '-start_time')
    return render(request, 'dashboard/bookings.html', {'business': business, 'bookings': bookings})

@login_required
def update_booking_status(request, pk, status):
    business = _get_business_or_redirect(request)
    if not business: return redirect('dashboard:onboarding')
    
    from .models import Booking
    booking = get_object_or_404(Booking, pk=pk, business=business)
    
    if status in ['pending', 'confirmed', 'completed', 'cancelled']:
        booking.status = status
        booking.save()
        messages.success(request, f'Booking status updated to {status}.')
    
    return redirect('dashboard:bookings')

@login_required
def booking_manage_view(request, pk):
    business = _get_business_or_redirect(request)
    if not business: return redirect('dashboard:onboarding')
    
    from .models import Booking
    import datetime
    booking = get_object_or_404(Booking, pk=pk, business=business)
    
    if request.method == 'POST':
        date_str = request.POST.get('date')
        time_str = request.POST.get('time')
        status = request.POST.get('status')
        business_message = request.POST.get('business_message', '')
        
        try:
            booking_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
            start_time = datetime.datetime.strptime(time_str, '%H:%M').time()
            
            # Recalculate end time
            start_dt = datetime.datetime.combine(booking_date, start_time)
            end_dt = start_dt + datetime.timedelta(minutes=booking.service.duration)
            end_time = end_dt.time()
            
            # Check if timing or message changed to notify user
            timing_changed = (booking.date != booking_date or booking.start_time != start_time)
            message_changed = (booking.business_message != business_message and business_message.strip() != "")
            
            booking.date = booking_date
            booking.start_time = start_time
            booking.end_time = end_time
            booking.status = status
            booking.business_message = business_message
            booking.save()
            
            if timing_changed or message_changed:
                print("==========================================")
                print(f"NOTIFICATION TO {booking.customer.phone_number or booking.customer.email or booking.customer.username}:")
                if timing_changed:
                    print(f"- Your appointment was rescheduled to {booking_date} at {start_time}.")
                if message_changed:
                    print(f"- Message from {business.business_name}: {business_message}")
                print("==========================================")
            
            messages.success(request, 'Booking updated successfully.')
            return redirect('dashboard:bookings')
            
        except ValueError:
            messages.error(request, 'Invalid date or time format.')
            
    return render(request, 'dashboard/booking_manage.html', {'business': business, 'booking': booking})

@login_required
def customers_view(request):
    business = _get_business_or_redirect(request)
    if not business: return redirect('dashboard:onboarding')
    return render(request, 'dashboard/customers.html', {'business': business})

@login_required
def availability_view(request):
    business = _get_business_or_redirect(request)
    if not business: return redirect('dashboard:onboarding')
    
    from .models import BusinessTimeOff
    import datetime
    
    if request.method == 'POST':
        action = request.POST.get('action', 'update_hours')
        
        if action == 'update_hours':
            opening = request.POST.get('opening_time')
            closing = request.POST.get('closing_time')
            working_days = request.POST.get('working_days')
            
            if opening: business.opening_time = opening
            if closing: business.closing_time = closing
            if working_days and working_days.isdigit(): business.working_days = int(working_days)
            
            business.save()
            messages.success(request, 'Operating hours updated successfully.')
            
        elif action == 'add_off_day':
            start_date_str = request.POST.get('start_date')
            end_date_str = request.POST.get('end_date')
            reason = request.POST.get('reason', '')
            
            try:
                start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
                if end_date < start_date:
                    messages.error(request, 'End date cannot be before start date.')
                else:
                    BusinessTimeOff.objects.create(
                        business=business,
                        start_date=start_date,
                        end_date=end_date,
                        reason=reason
                    )
                    messages.success(request, 'Off day added successfully.')
            except ValueError:
                messages.error(request, 'Invalid date format.')
                
        elif action == 'delete_off_day':
            off_day_id = request.POST.get('off_day_id')
            try:
                off_day = BusinessTimeOff.objects.get(id=off_day_id, business=business)
                off_day.delete()
                messages.success(request, 'Off day removed.')
            except BusinessTimeOff.DoesNotExist:
                messages.error(request, 'Off day not found.')
                
        return redirect('dashboard:availability')
        
    time_offs = BusinessTimeOff.objects.filter(business=business).order_by('-start_date')
        
    return render(request, 'dashboard/availability.html', {'business': business, 'time_offs': time_offs})

@login_required
def analytics_view(request):
    business = _get_business_or_redirect(request)
    if not business: return redirect('dashboard:onboarding')
    return render(request, 'dashboard/analytics.html', {'business': business})

@login_required
def profile_view(request):
    business = _get_business_or_redirect(request)
    if not business: return redirect('dashboard:onboarding')
    
    if request.method == 'POST':
        business.business_name = request.POST.get('business_name', business.business_name).strip()
        business.category = request.POST.get('category', business.category).strip()
        business.description = request.POST.get('description', business.description).strip()
        business.phone = request.POST.get('phone', business.phone).strip()
        business.email = request.POST.get('email', business.email).strip()
        business.address = request.POST.get('address', business.address).strip()
        business.city = request.POST.get('city', business.city).strip()
        
        if 'profile_image' in request.FILES:
            business.profile_image = request.FILES['profile_image']
            
        business.save()

        # Handle multiple gallery images upload
        if 'gallery_images' in request.FILES:
            from .models import BusinessImage
            for img in request.FILES.getlist('gallery_images'):
                BusinessImage.objects.create(business=business, image=img)
                
        messages.success(request, 'Business profile updated successfully!')
        return redirect('dashboard:profile')
        
    return render(request, 'dashboard/profile.html', {'business': business})

@login_required
def gallery_image_delete(request, pk):
    if request.user.role != 'business':
        return redirect('website:discover')
        
    from .models import BusinessImage
    image = get_object_or_404(BusinessImage, pk=pk, business__owner=request.user)
    image.delete()
    messages.success(request, 'Image deleted successfully.')
    return redirect('dashboard:profile')

@login_required
def settings_view(request):
    business = _get_business_or_redirect(request)
    if not business: return redirect('dashboard:onboarding')
    return render(request, 'dashboard/settings.html', {'business': business})


@login_required
def staff_list_view(request):
    business = _get_business_or_redirect(request)
    if not business: return redirect('dashboard:onboarding')
    from .models import Staff
    staff_members = Staff.objects.filter(business=business)
    return render(request, 'dashboard/staff_list.html', {'business': business, 'staff_members': staff_members})

@login_required
def staff_add_view(request):
    business = _get_business_or_redirect(request)
    if not business: return redirect('dashboard:onboarding')
    from .models import Staff, Service
    
    services = Service.objects.filter(business=business)
    
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email', '')
        phone = request.POST.get('phone', '')
        job_title = request.POST.get('job_title', '')
        bio = request.POST.get('bio', '')
        base_salary = request.POST.get('base_salary', 0)
        salary_type = request.POST.get('salary_type', 'monthly')
        selected_services = request.POST.getlist('services')
        
        staff = Staff.objects.create(
            business=business,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            job_title=job_title,
            bio=bio,
            base_salary=base_salary if base_salary else 0,
            salary_type=salary_type,
            is_active=True
        )
        
        if 'profile_image' in request.FILES:
            staff.profile_image = request.FILES['profile_image']
            staff.save()
            
        if selected_services:
            staff.services.set(services.filter(id__in=selected_services))
            
        messages.success(request, f'Staff member {first_name} added successfully.')
        return redirect('dashboard:staff_list')
        
    return render(request, 'dashboard/staff_form.html', {'business': business, 'services': services, 'staff': None})

@login_required
def staff_edit_view(request, pk):
    business = _get_business_or_redirect(request)
    if not business: return redirect('dashboard:onboarding')
    from .models import Staff, Service
    
    staff = get_object_or_404(Staff, pk=pk, business=business)
    services = Service.objects.filter(business=business)
    
    if request.method == 'POST':
        staff.first_name = request.POST.get('first_name')
        staff.last_name = request.POST.get('last_name')
        staff.email = request.POST.get('email', '')
        staff.phone = request.POST.get('phone', '')
        staff.job_title = request.POST.get('job_title', '')
        staff.bio = request.POST.get('bio', '')
        staff.is_active = request.POST.get('is_active') == 'on'
        
        base_salary = request.POST.get('base_salary', 0)
        staff.base_salary = base_salary if base_salary else 0
        staff.salary_type = request.POST.get('salary_type', 'monthly')
        
        if 'profile_image' in request.FILES:
            staff.profile_image = request.FILES['profile_image']
            
        staff.save()
        
        selected_services = request.POST.getlist('services')
        staff.services.set(services.filter(id__in=selected_services))
            
        messages.success(request, f'Staff member {staff.first_name} updated successfully.')
        return redirect('dashboard:staff_detail', pk=staff.pk)
        
    return render(request, 'dashboard/staff_form.html', {'business': business, 'services': services, 'staff': staff})

@login_required
def staff_detail_view(request, pk):
    business = _get_business_or_redirect(request)
    if not business: return redirect('dashboard:onboarding')
    from .models import Staff, Booking
    import datetime
    
    staff = get_object_or_404(Staff, pk=pk, business=business)
    upcoming_bookings = staff.bookings.filter(date__gte=datetime.date.today()).exclude(status='cancelled').order_by('date', 'start_time')
    
    return render(request, 'dashboard/staff_detail.html', {
        'business': business, 
        'staff': staff,
        'upcoming_bookings': upcoming_bookings
    })

@login_required
def staff_schedule_view(request, pk):
    business = _get_business_or_redirect(request)
    if not business: return redirect('dashboard:onboarding')
    from .models import Staff, StaffAvailability
    import datetime
    
    staff = get_object_or_404(Staff, pk=pk, business=business)
    
    if request.method == 'POST':
        # Process the weekly schedule form
        for day_idx in range(7):
            is_working = request.POST.get(f'working_{day_idx}') == 'on'
            start_time_str = request.POST.get(f'start_{day_idx}')
            end_time_str = request.POST.get(f'end_{day_idx}')
            
            avail, created = StaffAvailability.objects.get_or_create(staff=staff, day_of_week=day_idx)
            avail.is_working = is_working
            
            if is_working and start_time_str and end_time_str:
                avail.start_time = datetime.datetime.strptime(start_time_str, '%H:%M').time()
                avail.end_time = datetime.datetime.strptime(end_time_str, '%H:%M').time()
            else:
                avail.start_time = None
                avail.end_time = None
                
            avail.save()
            
        messages.success(request, 'Schedule updated successfully.')
        return redirect('dashboard:staff_detail', pk=staff.pk)
        
    # Get existing schedule or create defaults
    days = [(0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'), (3, 'Thursday'), (4, 'Friday'), (5, 'Saturday'), (6, 'Sunday')]
    schedules = []
    
    for idx, name in days:
        avail, created = StaffAvailability.objects.get_or_create(staff=staff, day_of_week=idx)
        schedules.append({
            'day_idx': idx,
            'name': name,
            'avail': avail
        })
        
    return render(request, 'dashboard/staff_schedule.html', {'business': business, 'staff': staff, 'schedules': schedules})


@login_required
def staff_payroll_view(request, pk):
    business = _get_business_or_redirect(request)
    if not business: return redirect('dashboard:onboarding')
    from .models import Staff, StaffPayroll
    import datetime
    
    staff = get_object_or_404(Staff, pk=pk, business=business)
    payrolls = staff.payrolls.all().order_by('-month')
    
    # Calculate some stats
    total_paid = sum(p.amount_paid for p in payrolls)
    total_pending = sum(p.net_payable - p.amount_paid for p in payrolls if p.net_payable > p.amount_paid)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add_payroll':
            month_str = request.POST.get('month') # expected YYYY-MM
            try:
                # Add -01 to represent the first day of the month
                month_date = datetime.datetime.strptime(f"{month_str}-01", "%Y-%m-%d").date()
                base_amount = request.POST.get('base_amount', 0)
                incentives = request.POST.get('incentives', 0)
                deductions = request.POST.get('deductions', 0)
                notes = request.POST.get('notes', '')
                
                StaffPayroll.objects.create(
                    staff=staff,
                    month=month_date,
                    base_amount=base_amount or 0,
                    incentives=incentives or 0,
                    deductions=deductions or 0,
                    notes=notes
                )
                messages.success(request, 'Payroll record added successfully.')
            except ValueError:
                messages.error(request, 'Invalid month format.')
        elif action == 'update_payment':
            payroll_id = request.POST.get('payroll_id')
            amount = request.POST.get('amount_paid', 0)
            try:
                payroll = StaffPayroll.objects.get(id=payroll_id, staff=staff)
                payroll.amount_paid = amount or 0
                payroll.save() # This triggers the custom save() method that updates status
                messages.success(request, 'Payment amount updated.')
            except StaffPayroll.DoesNotExist:
                messages.error(request, 'Payroll record not found.')
                
        return redirect('dashboard:staff_payroll', pk=staff.pk)
        
    return render(request, 'dashboard/staff_payroll.html', {
        'business': business, 
        'staff': staff, 
        'payrolls': payrolls,
        'total_paid': total_paid,
        'total_pending': total_pending
    })

@login_required
def staff_leave_view(request, pk):
    business = _get_business_or_redirect(request)
    if not business: return redirect('dashboard:onboarding')
    from .models import Staff, StaffTimeOff
    import datetime
    
    staff = get_object_or_404(Staff, pk=pk, business=business)
    leaves = staff.time_off.all().order_by('-start_date')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add_leave':
            start_date_str = request.POST.get('start_date')
            end_date_str = request.POST.get('end_date')
            leave_type = request.POST.get('leave_type', 'unpaid')
            reason = request.POST.get('reason', '')
            status = request.POST.get('status', 'approved')
            notes = request.POST.get('notes', '')
            
            try:
                start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
                
                if end_date < start_date:
                    messages.error(request, 'End date cannot be before start date.')
                else:
                    StaffTimeOff.objects.create(
                        staff=staff,
                        start_date=start_date,
                        end_date=end_date,
                        leave_type=leave_type,
                        status=status,
                        reason=reason,
                        notes=notes
                    )
                    messages.success(request, 'Leave record added successfully.')
            except ValueError:
                messages.error(request, 'Invalid date format.')
                
        elif action == 'update_status':
            leave_id = request.POST.get('leave_id')
            new_status = request.POST.get('status')
            try:
                leave = StaffTimeOff.objects.get(id=leave_id, staff=staff)
                if new_status in ['approved', 'pending', 'rejected']:
                    leave.status = new_status
                    leave.save()
                    messages.success(request, 'Leave status updated.')
            except StaffTimeOff.DoesNotExist:
                messages.error(request, 'Leave record not found.')
                
        return redirect('dashboard:staff_leaves', pk=staff.pk)
        
    return render(request, 'dashboard/staff_leaves.html', {
        'business': business, 
        'staff': staff, 
        'leaves': leaves
    })

@login_required
def payroll_list_view(request):
    business = _get_business_or_redirect(request)
    if not business: return redirect('dashboard:onboarding')
    from .models import Staff, StaffPayroll
    import datetime
    
    # Default to current month
    month_str = request.GET.get('month', datetime.date.today().strftime('%Y-%m'))
    try:
        month_date = datetime.datetime.strptime(f"{month_str}-01", "%Y-%m-%d").date()
    except ValueError:
        month_date = datetime.date.today().replace(day=1)
        month_str = month_date.strftime('%Y-%m')
        
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'generate_all':
            # Generate payroll for all active staff who don't have one for this month
            staff_members = Staff.objects.filter(business=business, is_active=True)
            existing_payrolls = StaffPayroll.objects.filter(staff__in=staff_members, month=month_date).values_list('staff_id', flat=True)
            
            created_count = 0
            for staff in staff_members:
                if staff.id not in existing_payrolls:
                    StaffPayroll.objects.create(
                        staff=staff,
                        month=month_date,
                        base_amount=staff.base_salary,
                        incentives=0,
                        deductions=0,
                        amount_paid=0
                    )
                    created_count += 1
            messages.success(request, f'Generated {created_count} payroll records for {month_date.strftime("%B %Y")}.')
            
        elif action == 'mark_paid':
            payroll_id = request.POST.get('payroll_id')
            try:
                payroll = StaffPayroll.objects.get(id=payroll_id, staff__business=business)
                payroll.amount_paid = payroll.net_payable
                payroll.save()
                messages.success(request, f'Payroll for {payroll.staff.first_name} marked as fully paid.')
            except StaffPayroll.DoesNotExist:
                messages.error(request, 'Payroll record not found.')
                
        return redirect(f"{reverse('dashboard:payroll')}?month={month_str}")
        
    staff_members = Staff.objects.filter(business=business)
    payrolls = StaffPayroll.objects.filter(staff__business=business, month=month_date)
    
    payroll_dict = {p.staff_id: p for p in payrolls}
    
    staff_data = []
    for staff in staff_members:
        staff_data.append({
            'staff': staff,
            'payroll': payroll_dict.get(staff.id)
        })
        
    total_net = sum(p.net_payable for p in payrolls)
    total_paid = sum(p.amount_paid for p in payrolls)
    total_pending = sum(p.net_payable - p.amount_paid for p in payrolls if p.net_payable > p.amount_paid)
    
    return render(request, 'dashboard/payroll.html', {
        'business': business,
        'month_str': month_str,
        'month_date': month_date,
        'staff_data': staff_data,
        'total_net': total_net,
        'total_paid': total_paid,
        'total_pending': total_pending
    })
