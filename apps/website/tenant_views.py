import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from apps.dashboard.models import Service, Staff, Booking, BusinessTimeOff

def get_tenant(request):
    return getattr(request, 'tenant', None)

def tenant_home(request):
    tenant = get_tenant(request)
    if not tenant or not tenant.is_published:
        return render(request, 'tenant/unavailable.html', status=403)
        
    services = tenant.services.filter(is_active=True)[:4]
    staff = tenant.staff_members.filter(is_active=True)[:4]
    
    return render(request, 'tenant/home.html', {
        'tenant': tenant,
        'services': services,
        'staff': staff
    })

def tenant_services(request):
    tenant = get_tenant(request)
    if not tenant or not tenant.is_published:
        return render(request, 'tenant/unavailable.html', status=403)
        
    services = tenant.services.filter(is_active=True)
    return render(request, 'tenant/services.html', {'tenant': tenant, 'services': services})

def tenant_staff(request):
    tenant = get_tenant(request)
    if not tenant or not tenant.is_published:
        return render(request, 'tenant/unavailable.html', status=403)
        
    staff = tenant.staff_members.filter(is_active=True)
    return render(request, 'tenant/staff.html', {'tenant': tenant, 'staff': staff})

def tenant_book_service(request, service_id):
    tenant = get_tenant(request)
    if not tenant or not tenant.is_published:
        return render(request, 'tenant/unavailable.html', status=403)
        
    service = get_object_or_404(Service, id=service_id, business=tenant)
    staff_members = tenant.staff_members.filter(is_active=True, services=service)
    
    if request.method == 'POST':
        date_str = request.POST.get('booking_date')
        time_str = request.POST.get('booking_time')
        staff_id = request.POST.get('staff_id')
        
        # Collect customer details
        name = request.POST.get('customer_name')
        email = request.POST.get('customer_email')
        phone = request.POST.get('customer_phone')
        notes = request.POST.get('notes', '')
        
        try:
            booking_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
            booking_time = datetime.datetime.strptime(time_str, '%H:%M').time()
            end_time = (datetime.datetime.combine(datetime.date.today(), booking_time) + datetime.timedelta(minutes=service.duration)).time()
            
            selected_staff = None
            if staff_id:
                selected_staff = get_object_or_404(Staff, id=staff_id, business=tenant)
                
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            # Since tenant users might not be logged in, get or create a user by email
            customer, created = User.objects.get_or_create(
                username=phone,
                defaults={
                    'email': email,
                    'first_name': name,
                    'is_active': True
                }
            )
                
            status = 'confirmed' if tenant.auto_accept_bookings else 'pending'
            
            Booking.objects.create(
                business=tenant,
                service=service,
                staff=selected_staff,
                customer=customer,
                customer_phone=phone,
                date=booking_date,
                start_time=booking_time,
                end_time=end_time,
                notes=f"Phone: {phone}\nName: {name}\n\n{notes}",
                status=status
            )
            
            msg = "Your booking is confirmed!" if tenant.auto_accept_bookings else "Booking successfully requested! We will contact you soon."
            messages.success(request, msg)
            request.session['customer_phone'] = phone
            return redirect('tenant_my_bookings')
            
        except Exception as e:
            messages.error(request, 'An error occurred while booking.')
            
    return render(request, 'tenant/book.html', {
        'tenant': tenant,
        'service': service,
        'staff_members': staff_members
    })

def tenant_my_bookings(request):
    tenant = get_tenant(request)
    if not tenant or not tenant.is_published:
        return render(request, 'tenant/unavailable.html', status=403)
        
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'login':
            phone = request.POST.get('phone')
            if phone:
                request.session['customer_phone'] = phone
        elif action == 'logout':
            if 'customer_phone' in request.session:
                del request.session['customer_phone']
            return redirect('tenant_my_bookings')
            
    customer_phone = request.session.get('customer_phone')
    bookings = None
    if customer_phone:
        from apps.dashboard.models import Booking
        bookings = Booking.objects.filter(business=tenant, customer_phone=customer_phone).order_by('-date', '-start_time')
        
    return render(request, 'tenant/my_bookings.html', {
        'tenant': tenant, 
        'customer_phone': customer_phone, 
        'bookings': bookings
    })

def tenant_api_get_slots(request, service_id):
    tenant = get_tenant(request)
    if not tenant:
        return JsonResponse({'error': 'Not found'}, status=404)
        
    service = get_object_or_404(Service, id=service_id, business=tenant)
    date_str = request.GET.get('date')
    
    if not date_str:
        return JsonResponse({'error': 'Date is required'}, status=400)
        
    try:
        booking_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'error': 'Invalid date format'}, status=400)
        
    is_off_day = BusinessTimeOff.objects.filter(
        business=tenant,
        start_date__lte=booking_date,
        end_date__gte=booking_date
    ).exists()
    
    if is_off_day:
        return JsonResponse({'slots': []})
        
    # Same logic as before but adapted for tenant
    existing_bookings = Booking.objects.filter(business=tenant, date=booking_date).exclude(status='cancelled')
    
    staff_id = request.GET.get('staff_id')
    if staff_id:
        existing_bookings = existing_bookings.filter(staff_id=staff_id)
        
    opening_time = tenant.opening_time
    closing_time = tenant.closing_time
    service_duration = service.duration
    
    current_time = datetime.datetime.combine(booking_date, opening_time)
    closing_datetime = datetime.datetime.combine(booking_date, closing_time)
    
    available_slots = []
    
    while current_time + datetime.timedelta(minutes=service_duration) <= closing_datetime:
        slot_end = current_time + datetime.timedelta(minutes=service_duration)
        
        overlap = False
        for booking in existing_bookings:
            booking_start = datetime.datetime.combine(booking_date, booking.start_time)
            booking_end = datetime.datetime.combine(booking_date, booking.end_time)
            
            if current_time < booking_end and slot_end > booking_start:
                overlap = True
                break
                
        if not overlap:
            available_slots.append({
                'time': current_time.strftime('%H:%M'),
                'display': current_time.strftime('%I:%M %p')
            })
            
        current_time += datetime.timedelta(minutes=30)
        
    return JsonResponse({'slots': available_slots})

def tenant_api_get_multi_slots(request):
    tenant = get_tenant(request)
    if not tenant:
        return JsonResponse({'error': 'Not found'}, status=404)
        
    service_ids = request.GET.get('services', '')
    if not service_ids:
        return JsonResponse({'slots': []})
        
    try:
        service_id_list = [int(s) for s in service_ids.split(',')]
    except ValueError:
        return JsonResponse({'error': 'Invalid service IDs'}, status=400)
        
    services = Service.objects.filter(id__in=service_id_list, business=tenant)
    if not services.exists():
        return JsonResponse({'error': 'Services not found'}, status=404)
        
    total_duration = sum(s.duration for s in services)
    
    date_str = request.GET.get('date')
    if not date_str:
        return JsonResponse({'error': 'Date is required'}, status=400)
        
    try:
        booking_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'error': 'Invalid date format'}, status=400)
        
    is_off_day = BusinessTimeOff.objects.filter(
        business=tenant,
        start_date__lte=booking_date,
        end_date__gte=booking_date
    ).exists()
    
    if is_off_day:
        return JsonResponse({'slots': []})
        
    existing_bookings = Booking.objects.filter(business=tenant, date=booking_date).exclude(status='cancelled')
    
    staff_id = request.GET.get('staff_id')
    if staff_id:
        existing_bookings = existing_bookings.filter(staff_id=staff_id)
        
    opening_time = tenant.opening_time
    closing_time = tenant.closing_time
    
    current_time = datetime.datetime.combine(booking_date, opening_time)
    closing_datetime = datetime.datetime.combine(booking_date, closing_time)
    
    available_slots = []
    
    while current_time + datetime.timedelta(minutes=total_duration) <= closing_datetime:
        slot_end = current_time + datetime.timedelta(minutes=total_duration)
        
        overlap = False
        for booking in existing_bookings:
            booking_start = datetime.datetime.combine(booking_date, booking.start_time)
            booking_end = datetime.datetime.combine(booking_date, booking.end_time)
            
            if current_time < booking_end and slot_end > booking_start:
                overlap = True
                break
                
        if not overlap:
            available_slots.append({
                'time': current_time.strftime('%H:%M'),
                'display': current_time.strftime('%I:%M %p')
            })
            
        current_time += datetime.timedelta(minutes=30)
        
    return JsonResponse({'slots': available_slots})

def tenant_book_multi_service(request):
    tenant = get_tenant(request)
    if not tenant or not tenant.is_published:
        return render(request, 'tenant/unavailable.html', status=403)
        
    service_ids = request.GET.get('services', '')
    if not service_ids:
        return redirect('tenant_services')
        
    try:
        service_id_list = [int(s) for s in service_ids.split(',')]
    except ValueError:
        return redirect('tenant_services')
        
    services = Service.objects.filter(id__in=service_id_list, business=tenant)
    if not services.exists():
        return redirect('tenant_services')
        
    total_duration = sum(s.duration for s in services)
    total_price = sum(s.price for s in services)
    
    # Staff handling: for now, pick staff who can do the first service or just any staff 
    # Actually, let's just get all staff for simplicity if it's a multi-service.
    staff_members = tenant.staff_members.filter(is_active=True)
    
    if request.method == 'POST':
        date_str = request.POST.get('booking_date')
        time_str = request.POST.get('booking_time')
        staff_id = request.POST.get('staff_id')
        
        name = request.POST.get('customer_name')
        email = request.POST.get('customer_email')
        phone = request.POST.get('customer_phone')
        notes = request.POST.get('notes', '')
        
        try:
            booking_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
            booking_time = datetime.datetime.strptime(time_str, '%H:%M').time()
            end_time = (datetime.datetime.combine(datetime.date.today(), booking_time) + datetime.timedelta(minutes=total_duration)).time()
            
            selected_staff = None
            if staff_id:
                selected_staff = get_object_or_404(Staff, id=staff_id, business=tenant)
                
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            customer, created = User.objects.get_or_create(
                username=phone,
                defaults={
                    'email': email,
                    'first_name': name,
                    'is_active': True
                }
            )
                
            status = 'confirmed' if tenant.auto_accept_bookings else 'pending'
            
            booking = Booking.objects.create(
                business=tenant,
                staff=selected_staff,
                customer=customer,
                customer_phone=phone,
                date=booking_date,
                start_time=booking_time,
                end_time=end_time,
                notes=f"Phone: {phone}\nName: {name}\n\n{notes}",
                status=status
            )
            booking.services.set(services)
            
            msg = "Your booking is confirmed!" if tenant.auto_accept_bookings else "Booking successfully requested! We will contact you soon."
            messages.success(request, msg)
            request.session['customer_phone'] = phone
            return redirect('tenant_my_bookings')
            
        except Exception as e:
            messages.error(request, 'An error occurred while booking.')
            
    return render(request, 'tenant/book_multi.html', {
        'tenant': tenant,
        'services': services,
        'total_duration': total_duration,
        'total_price': total_price,
        'service_ids_str': service_ids,
        'staff_members': staff_members
    })

