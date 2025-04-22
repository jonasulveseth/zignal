import logging
import hmac
import hashlib
import json
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import HttpResponse, JsonResponse
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib.auth.decorators import login_required

from .services import EmailProcessingService
from .tasks import process_incoming_email_task
from .models import IncomingEmail, EmailAttachment
from profiles.models import Profile

logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name='dispatch')
class MailgunWebhookView(View):
    """
    View for handling inbound email webhooks from Mailgun
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.email_service = EmailProcessingService()
    
    def post(self, request, *args, **kwargs):
        """
        Handle POST requests for inbound email webhooks
        
        Args:
            request: HttpRequest object
            
        Returns:
            HttpResponse: 200 OK if successful, 4xx if error
        """
        try:
            # Verify webhook signature
            if not self._verify_mailgun_signature(request):
                logger.warning("Mailgun webhook signature verification failed")
                return HttpResponse("Invalid signature", status=401)
            
            # Process webhook data
            webhook_data = request.POST.dict()
            files = request.FILES
            
            # Add files to webhook data - this is for sync processing
            # NOTE: For async processing, files need to be handled differently
            
            # For synchronous processing (debugging or small attachments)
            if settings.DEBUG and getattr(settings, 'PROCESS_EMAILS_SYNC', False):
                # Add files to webhook data for sync processing
                for key, file_obj in files.items():
                    webhook_data[key] = file_obj
                
                # Process the email data synchronously
                self.email_service.process_incoming_email(webhook_data)
            else:
                # For async processing, we need to handle files separately
                # This is a simplified approach - in production you'd need to 
                # store files temporarily and pass references to the task
                
                # Process asynchronously using Celery (without file attachments for now)
                process_incoming_email_task.delay(webhook_data)
                logger.info(f"Email task queued: {webhook_data.get('Message-Id', 'unknown')}")
            
            return HttpResponse("OK", status=200)
            
        except Exception as e:
            logger.error(f"Error processing Mailgun webhook: {str(e)}")
            return HttpResponse("Error processing webhook", status=500)
    
    def _verify_mailgun_signature(self, request):
        """
        Verify the Mailgun webhook signature
        
        Args:
            request: HttpRequest object
            
        Returns:
            bool: True if signature is valid, False otherwise
        """
        # Skip verification if MAILGUN_API_KEY is not set or in DEBUG mode
        if settings.DEBUG and not getattr(settings, 'MAILGUN_API_KEY', None):
            return True
        
        # Get signature data from request
        token = request.POST.get('token', '')
        timestamp = request.POST.get('timestamp', '')
        signature = request.POST.get('signature', '')
        
        if not token or not timestamp or not signature:
            logger.warning("Mailgun webhook missing signature data")
            return False
        
        # Get API key
        api_key = getattr(settings, 'MAILGUN_API_KEY', '')
        
        # Verify signature
        expected_signature = hmac.new(
            key=api_key.encode('utf-8'),
            msg=f"{timestamp}{token}".encode('utf-8'),
            digestmod=hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)


# For testing and debugging
def webhook_test_view(request):
    """Simple view for testing the webhook handling"""
    return JsonResponse({
        "message": "Mailgun webhook test endpoint is working",
        "info": "Send a POST request to /webhook/ to test the webhook handler"
    })

@login_required
def mail_dashboard(request):
    """
    View for displaying the mail receiver dashboard
    Shows received emails for the user's company
    """
    # Get the user's company
    company = None
    if hasattr(request.user, 'profile') and request.user.profile and hasattr(request.user.profile, 'company'):
        company = request.user.profile.company
    
    if not company:
        # Try to get it from company relations
        relation = request.user.company_relations.first()
        if relation:
            company = relation.company
    
    if not company:
        # No company found
        return render(request, 'mail_receiver/mail_dashboard.html', {
            'has_company': False,
            'company_email': None,
            'emails': [],
        })
    
    # Get emails from data silos associated with this company
    emails = []
    if company:
        # Get all data silos for this company
        from datasilo.models import DataSilo
        silos = DataSilo.objects.filter(company=company, name='Emails')
        
        # Get emails from these silos
        if silos.exists():
            emails = IncomingEmail.objects.filter(data_silo__in=silos).order_by('-received_at')[:30]
    
    # Check if email integration is set up
    company_email = None
    if company and company.company_email:
        company_email = company.get_full_email_address()
    
    return render(request, 'mail_receiver/mail_dashboard.html', {
        'has_company': True,
        'company': company,
        'company_email': company_email,
        'emails': emails,
    }) 