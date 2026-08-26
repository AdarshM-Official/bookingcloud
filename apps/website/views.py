from django.shortcuts import render, redirect
from django.views.generic import TemplateView
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import get_user_model
from django.contrib import messages
import random

User = get_user_model()

class LandingPageView(TemplateView):
    template_name = "landing/index.html"

from django.views.generic import TemplateView
from apps.dashboard.models import Business
from django.db.models import Q

class DiscoveryView(TemplateView):
    template_name = "landing/discovery.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get query parameters
        query = self.request.GET.get('q', '').strip()
        category = self.request.GET.get('category', '').strip()
        sort = self.request.GET.get('sort', '').strip()
        
        # Start with all active businesses
        businesses = Business.objects.filter(is_active=True).prefetch_related('services')
        
        # Apply search filter
        if query:
            businesses = businesses.filter(
                Q(business_name__icontains=query) |
                Q(city__icontains=query) |
                Q(services__service_name__icontains=query)
            ).distinct()
            
        # Apply category filter
        if category:
            businesses = businesses.filter(category__icontains=category)
            
        # Apply sorting
        if sort == 'newest':
            businesses = businesses.order_by('-created_at')
        elif sort == 'name':
            businesses = businesses.order_by('business_name')
        # By default, maybe order randomly or by creation date
        else:
            businesses = businesses.order_by('-created_at')
            
        context['businesses'] = businesses
        context['current_query'] = query
        context['current_category'] = category
        context['current_sort'] = sort
        return context

def authentication_view(request):
    if request.user.is_authenticated:
        if getattr(request.user, 'role', '') == 'business':
            return redirect('dashboard:index')
        return redirect('website:discover')

    context = {}

    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'login':
            username = request.POST.get('username')
            password = request.POST.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                if user.role == 'business':
                    return redirect('dashboard:index')
                else:
                    return redirect('website:discover')
            else:
                messages.error(request, "Invalid username or password.")
                
        elif action == 'register':
            username = request.POST.get('username')
            email = request.POST.get('email')
            password = request.POST.get('password')
            confirm_password = request.POST.get('confirm_password')
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            role = request.POST.get('role')
            
            if password != confirm_password:
                messages.error(request, "Passwords do not match.")
            elif len(password) < 8:
                messages.error(request, "Password must be at least 8 characters long.")
            elif User.objects.filter(username=username).exists():
                messages.error(request, "Username already exists.")
            elif User.objects.filter(email=email).exists():
                messages.error(request, "Email already exists.")
            else:
                user = User.objects.create_user(
                    username=username, 
                    email=email, 
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    role=role
                )
                login(request, user)
                if role == 'business':
                    return redirect('dashboard:onboarding')
                else:
                    return redirect('website:discover')

        elif action == 'request_otp':
            phone_number = request.POST.get('phone_number')
            if not phone_number:
                messages.error(request, "Phone number is required.")
            else:
                otp = str(random.randint(100000, 999999))
                # SIMULATE SMS SENDING by printing to terminal
                print(f"==========================================")
                print(f"SMS TO {phone_number}: Your BookingSaaS OTP is {otp}")
                print(f"==========================================")
                
                request.session['auth_otp'] = otp
                request.session['auth_phone'] = phone_number
                
                context['show_otp_form'] = True
                context['phone_number'] = phone_number

        elif action == 'verify_otp':
            entered_otp = request.POST.get('otp')
            session_otp = request.session.get('auth_otp')
            phone_number = request.session.get('auth_phone')
            
            if entered_otp and session_otp and entered_otp == session_otp:
                # OTP is correct
                user = User.objects.filter(phone_number=phone_number).first()
                if not user:
                    # Register new user
                    username = f"user_{phone_number}"
                    user = User.objects.create_user(
                        username=username,
                        phone_number=phone_number,
                        role='customer'
                    )
                
                login(request, user)
                
                # Cleanup session
                del request.session['auth_otp']
                del request.session['auth_phone']
                
                if getattr(user, 'role', '') == 'business':
                    return redirect('dashboard:index')
                else:
                    return redirect('website:discover')
            else:
                messages.error(request, "Invalid or expired OTP.")
                context['show_otp_form'] = True
                context['phone_number'] = phone_number

    return render(request, "registration/authentication.html", context)

def logout_view(request):
    logout(request)
    return redirect('website:index')

from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from apps.dashboard.models import Service, Booking
import datetime

from django.http import JsonResponse

@login_required
def api_get_slots(request, service_id):
    service = get_object_or_404(Service, id=service_id)
    business = service.business
    date_str = request.GET.get('date')
    
    if not date_str:
        return JsonResponse({'error': 'Date is required'}, status=400)
        
    try:
        booking_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'error': 'Invalid date format'}, status=400)
        
    # Check if the business is on an off day
    from apps.dashboard.models import BusinessTimeOff
    is_off_day = BusinessTimeOff.objects.filter(
        business=business,
        start_date__lte=booking_date,
        end_date__gte=booking_date
    ).exists()
    
    if is_off_day:
        return JsonResponse({'slots': []})
        
    # Get all non-cancelled bookings for this business on this date
    existing_bookings = Booking.objects.filter(
        business=business, 
        date=booking_date
    ).exclude(status='cancelled')
    
    slots = []
    current_dt = datetime.datetime.combine(booking_date, business.opening_time)
    closing_dt = datetime.datetime.combine(booking_date, business.closing_time)
    
    # Generate slots based on service duration or 30 min increments (using service duration here)
    increment = datetime.timedelta(minutes=service.duration)
    
    while current_dt + increment <= closing_dt:
        slot_start = current_dt.time()
        slot_end = (current_dt + increment).time()
        
        # Check for overlap
        overlap = False
        for b in existing_bookings:
            if b.start_time < slot_end and b.end_time > slot_start:
                overlap = True
                break
                
        if not overlap:
            slots.append(slot_start.strftime('%H:%M'))
            
        current_dt += datetime.timedelta(minutes=15) # Generate slot options every 15 minutes
        
    return JsonResponse({'slots': slots})

@login_required
def book_service(request, service_id):
    service = get_object_or_404(Service, id=service_id)
    business = service.business
    staff_members = service.staff_members.filter(is_active=True)
    
    if request.method == 'POST':
        date_str = request.POST.get('date')
        time_str = request.POST.get('time')
        notes = request.POST.get('notes', '')
        staff_id = request.POST.get('staff_id')
        
        try:
            booking_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
            booking_time = datetime.datetime.strptime(time_str, '%H:%M').time()
            end_time = (datetime.datetime.combine(datetime.date.today(), booking_time) + datetime.timedelta(minutes=service.duration)).time()
            
            overlap_query = Booking.objects.filter(
                business=business,
                date=booking_date,
                status__in=['pending', 'confirmed']
            ).filter(
                Q(start_time__lt=end_time) & Q(end_time__gt=booking_time)
            )
            
            if staff_id:
                overlap_query = overlap_query.filter(staff_id=staff_id)
                
            if overlap_query.exists():
                # basic next slot generation
                suggested_time = (datetime.datetime.combine(datetime.date.today(), overlap_query.last().end_time)).time().strftime('%H:%M')
                messages.error(request, f'This time slot is already booked. Suggested next available slot: {suggested_time}')
                return render(request, 'landing/book_service.html', {'service': service, 'business': business, 'selected_date': date_str, 'suggested_time': suggested_time, 'staff_members': staff_members})
            
            staff_obj = None
            if staff_id:
                from apps.dashboard.models import Staff
                staff_obj = Staff.objects.filter(id=staff_id, business=business).first()
                
            Booking.objects.create(
                business=business,
                service=service,
                staff=staff_obj,
                customer=request.user,
                date=booking_date,
                start_time=booking_time,
                end_time=end_time,
                notes=notes
            )
            messages.success(request, f'Successfully booked {service.service_name} with {business.business_name}!')
            return redirect('website:my_bookings')
        except ValueError:
            messages.error(request, 'Invalid date or time format.')
            
    return render(request, 'landing/book_service.html', {'service': service, 'business': business, 'staff_members': staff_members})

def business_profile_view(request, business_id):
    business = get_object_or_404(Business, id=business_id, is_active=True)
    services = business.services.filter(is_active=True)
    return render(request, 'landing/business_profile.html', {'business': business, 'services': services})

@login_required
def customer_bookings_view(request):
    # Only customers should see their bookings page, if a business somehow hits this, redirect them.
    if getattr(request.user, 'role', '') == 'business':
        return redirect('dashboard:index')
        
    bookings = Booking.objects.filter(customer=request.user).order_by('-date', '-start_time')
    return render(request, 'landing/my_bookings.html', {'bookings': bookings})

@login_required
def reply_booking_view(request, booking_id):
    if request.method == 'POST':
        booking = get_object_or_404(Booking, id=booking_id, customer=request.user)
        reply = request.POST.get('reply', '').strip()
        if reply:
            booking.customer_reply = reply
            booking.save()
            messages.success(request, 'Reply sent to business.')
            
            # Simulate notification to business
            print("==========================================")
            print(f"NOTIFICATION TO BUSINESS {booking.business.business_name}:")
            print(f"- Reply from {booking.customer.first_name} {booking.customer.last_name}: {reply}")
            print("==========================================")
            
    return redirect('website:my_bookings')
