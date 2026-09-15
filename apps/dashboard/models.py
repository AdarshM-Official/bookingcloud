from django.db import models
from django.conf import settings
import datetime

class Business(models.Model):
    owner = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='business')
    business_name = models.CharField(max_length=255)
    category = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    profile_image = models.ImageField(upload_to='business_profiles/', blank=True, null=True)
    opening_time = models.TimeField(default=datetime.time(9, 0))
    closing_time = models.TimeField(default=datetime.time(17, 0))
    working_days = models.IntegerField(default=5, help_text="Number of working days in a week")
    is_active = models.BooleanField(default=True)
    
    # Tenant & Branding Fields
    slug = models.SlugField(unique=True, null=True, blank=True)
    is_published = models.BooleanField(default=True)
    primary_color = models.CharField(max_length=20, default='#4F46E5')
    secondary_color = models.CharField(max_length=20, default='#F1F5F9')
    facebook_url = models.URLField(blank=True, null=True)
    instagram_url = models.URLField(blank=True, null=True)
    website_url = models.URLField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        from django.utils.text import slugify
        if not self.slug and self.business_name:
            base_slug = slugify(self.business_name)
            new_slug = base_slug
            counter = 1
            while Business.objects.filter(slug=new_slug).exclude(pk=self.pk).exists() or new_slug in ['www', 'admin', 'api', 'app', 'auth', 'login', 'register', 'dashboard', 'static', 'media', 'support', 'help', 'mail', 'smtp', 'blog', 'discover', 'bookingcloud']:
                new_slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = new_slug
        super().save(*args, **kwargs)

    def get_tenant_url(self):
        protocol = getattr(settings, 'TENANT_PROTOCOL', 'http')
        base_domain = getattr(settings, 'BASE_DOMAIN', 'localhost:8000')
        return f"{protocol}://{self.slug}.{base_domain}"

    def __str__(self):
        return self.business_name

class BusinessTimeOff(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='time_off')
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.business.business_name} - Off: {self.start_date} to {self.end_date}"

class Service(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='services')
    service_name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    duration = models.IntegerField(help_text="Duration in minutes")
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.service_name} ({self.business.business_name})"

class Staff(models.Model):
    SALARY_TYPES = (
        ('monthly', 'Monthly Fixed'),
        ('hourly', 'Hourly Rate'),
        ('commission', 'Commission Only'),
    )
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='staff_members')
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    display_name = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    profile_image = models.ImageField(upload_to='staff_profiles/', blank=True, null=True)
    job_title = models.CharField(max_length=100, blank=True)
    bio = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    accepts_bookings = models.BooleanField(default=True)
    services = models.ManyToManyField(Service, related_name='staff_members', blank=True)
    base_salary = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    salary_type = models.CharField(max_length=20, choices=SALARY_TYPES, default='monthly')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"

class StaffAvailability(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='availabilities')
    day_of_week = models.IntegerField(choices=[(0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'), (3, 'Thursday'), (4, 'Friday'), (5, 'Saturday'), (6, 'Sunday')])
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    is_working = models.BooleanField(default=True)

class StaffBreak(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='breaks')
    day_of_week = models.IntegerField(choices=[(0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'), (3, 'Thursday'), (4, 'Friday'), (5, 'Saturday'), (6, 'Sunday')])
    start_time = models.TimeField()
    end_time = models.TimeField()

class StaffTimeOff(models.Model):
    LEAVE_TYPES = (
        ('paid', 'Paid Leave'),
        ('unpaid', 'Unpaid Leave'),
        ('sick', 'Sick Leave'),
    )
    STATUS_CHOICES = (
        ('approved', 'Approved'),
        ('pending', 'Pending'),
        ('rejected', 'Rejected'),
    )
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='time_off')
    start_date = models.DateField()
    end_date = models.DateField()
    leave_type = models.CharField(max_length=20, choices=LEAVE_TYPES, default='unpaid')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='approved')
    reason = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class StaffPayroll(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('partially_paid', 'Partially Paid'),
        ('paid', 'Paid'),
    )
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='payrolls')
    month = models.DateField(help_text="First day of the month this payroll applies to")
    base_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    incentives = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    net_payable = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        from decimal import Decimal
        self.base_amount = Decimal(str(self.base_amount or 0))
        self.incentives = Decimal(str(self.incentives or 0))
        self.deductions = Decimal(str(self.deductions or 0))
        self.amount_paid = Decimal(str(self.amount_paid or 0))
        
        self.net_payable = self.base_amount + self.incentives - self.deductions
        if self.amount_paid >= self.net_payable and self.net_payable > 0:
            self.status = 'paid'
        elif self.amount_paid > 0:
            self.status = 'partially_paid'
        else:
            self.status = 'pending'
        super().save(*args, **kwargs)
        
    def __str__(self):
        return f"{self.staff} - {self.month.strftime('%b %Y')}"

class Booking(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='bookings')
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='bookings', null=True, blank=True)
    services = models.ManyToManyField(Service, related_name='multi_bookings', blank=True)
    staff = models.ForeignKey(Staff, on_delete=models.SET_NULL, null=True, blank=True, related_name='bookings')
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookings')
    customer_phone = models.CharField(max_length=20, blank=True, help_text="Customer phone number for WhatsApp")
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True, help_text="Customer notes")
    business_message = models.TextField(blank=True, help_text="Message from business to customer")
    customer_reply = models.TextField(blank=True, help_text="Reply from customer to business")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total_duration(self):
        if self.services.exists():
            return sum(s.duration for s in self.services.all())
        return self.service.duration if self.service else 0
        
    @property
    def total_price(self):
        if self.services.exists():
            return sum(s.price for s in self.services.all())
        return self.service.price if self.service else 0

    @property
    def service_label(self):
        """Human-readable service name(s) for this booking."""
        if self.service:
            return self.service.service_name
        if self.pk and self.services.exists():
            return ", ".join(s.service_name for s in self.services.all())
        return "Appointment"

    def get_whatsapp_url(self):
        """Generate a pre-filled wa.me link for notifying the customer."""
        import urllib.parse
        phone = self.customer_phone.strip().replace(" ", "").replace("-", "").replace("+", "")
        if not phone:
            return None

        status_messages = {
            'pending':   f"Hello {self.customer.first_name or 'there'}! 👋 We have received your booking request for *{self.service_label}* at *{self.business.business_name}* on *{self.date.strftime('%B %d, %Y')}* at *{self.start_time.strftime('%I:%M %p')}*. We will confirm shortly!",
            'confirmed': f"Great news, {self.customer.first_name or 'there'}! ✅ Your booking for *{self.service_label}* at *{self.business.business_name}* is *Confirmed* for *{self.date.strftime('%B %d, %Y')}* at *{self.start_time.strftime('%I:%M %p')}*. See you soon! 🙌",
            'completed': f"Thank you for visiting *{self.business.business_name}*, {self.customer.first_name or 'there'}! 🌟 Your appointment for *{self.service_label}* is marked as completed. We hope you had a great experience!",
            'cancelled': f"Hi {self.customer.first_name or 'there'}, we regret to inform you that your booking for *{self.service_label}* at *{self.business.business_name}* on *{self.date.strftime('%B %d, %Y')}* has been *Cancelled*. Please contact us to reschedule.",
        }

        message = status_messages.get(self.status, f"Update on your booking at *{self.business.business_name}*: your appointment is now *{self.get_status_display()}*.")

        if self.business_message and self.business_message.strip():
            message += f"\n\n📝 Message from us: {self.business_message.strip()}"

        encoded = urllib.parse.quote(message)
        return f"https://wa.me/{phone}?text={encoded}"

    def __str__(self):
        if self.service:
            return f"{self.service.service_name} on {self.date}"
        elif self.pk and self.services.exists():
            return f"Multi-service booking ({self.services.count()}) on {self.date}"
        return f"Booking on {self.date}"

class BusinessImage(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='gallery_images')
    image = models.ImageField(upload_to='business_gallery/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Gallery image for {self.business.business_name}"

