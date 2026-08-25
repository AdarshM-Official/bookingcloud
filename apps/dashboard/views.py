from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Business, Service
from django.contrib import messages

@login_required
def dashboard_view(request):
    if request.user.role != 'business':
        return redirect('website:discover')
    
    try:
        business = request.user.business
    except Business.DoesNotExist:
        return redirect('dashboard:onboarding')
    
    services = business.services.all()
    context = {
        'business': business,
        'services': services,
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
        events.append({
            'title': f"{booking.service.service_name} - {booking.customer.get_full_name() or booking.customer.username}",
            'start': f"{booking.date.isoformat()}T{booking.start_time.isoformat()}",
            'end': f"{booking.date.isoformat()}T{booking.end_time.isoformat()}",
            'url': f"/dashboard/bookings/{booking.id}/", # Assuming you might add this later
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
    return render(request, 'dashboard/availability.html', {'business': business})

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
        
        # Working Hours
        opening = request.POST.get('opening_time')
        closing = request.POST.get('closing_time')
        working_days = request.POST.get('working_days')
        
        if opening: business.opening_time = opening
        if closing: business.closing_time = closing
        if working_days and working_days.isdigit(): business.working_days = int(working_days)
        
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

