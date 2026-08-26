import re
from django.conf import settings
from django.shortcuts import render
from apps.dashboard.models import Business

class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        hostname = request.get_host().split(":")[0].lower()
        
        base_domain = getattr(settings, 'BASE_DOMAIN', 'localhost').split(":")[0].lower()
        
        # Check if the request is for the main domain
        if hostname == base_domain or hostname == '127.0.0.1':
            request.tenant = None
            return self.get_response(request)
            
        # Extract subdomain
        subdomain = hostname.replace(f".{base_domain}", "")
        
        # Special case for lvh.me
        if hostname.endswith('.lvh.me'):
            subdomain = hostname.replace('.lvh.me', "")
            
        reserved_subdomains = ['www', 'admin', 'api', 'app', 'auth', 'login', 'register', 'dashboard', 'static', 'media', 'support', 'help', 'mail', 'smtp', 'blog', 'discover', 'bookingcloud']
        
        if subdomain in reserved_subdomains or not subdomain:
            request.tenant = None
            return self.get_response(request)
            
        try:
            business = Business.objects.get(slug=subdomain)
            request.tenant = business
            request.urlconf = 'bookingsaas.tenant_urls'
        except Business.DoesNotExist:
            return render(request, 'tenant/not_found.html', status=404)
            
        return self.get_response(request)
