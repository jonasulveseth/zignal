import logging
import hmac
import hashlib
import json
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import HttpResponse, JsonResponse
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views import View

from .services import EmailProcessingService

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
            
            # Add files to webhook data
            for key, file_obj in files.items():
                webhook_data[key] = file_obj
            
            # Process the email data
            self.email_service.process_incoming_email(webhook_data)
            
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