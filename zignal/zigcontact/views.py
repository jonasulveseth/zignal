from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

from .models import Support

def contact_form(request):
    """View for displaying and processing the contact form"""
    if request.method == 'POST':
        title = request.POST.get('title')
        name = request.POST.get('name')
        email = request.POST.get('email')
        message = request.POST.get('message')
        
        # Basic validation
        if not all([title, name, email, message]):
            messages.error(request, "All fields are required")
            return render(request, 'zigcontact/contact_form.html')
        
        # Create support request
        support = Support.objects.create(
            title=title,
            name=name,
            email=email,
            message=message
        )
        
        # Send notification email to admin (if in production)
        if not settings.DEBUG:
            try:
                subject = f"New Contact Form Submission: {title}"
                html_message = render_to_string('zigcontact/email/contact_notification.html', {
                    'support': support
                })
                plain_message = f"New contact form submission from {name} ({email})\n\nTitle: {title}\n\nMessage: {message}"
                
                send_mail(
                    subject=subject,
                    message=plain_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[settings.DEFAULT_FROM_EMAIL],  # Send to admin email 
                    html_message=html_message,
                    fail_silently=True,
                )
            except Exception as e:
                # Log the error but don't show to user
                print(f"Failed to send notification email: {e}")
        
        # Redirect to success page
        return redirect('contact_success')
    
    return render(request, 'zigcontact/contact_form.html')

def contact_success(request):
    """Success page after contact form submission"""
    return render(request, 'zigcontact/contact_success.html')
