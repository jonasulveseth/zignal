from django.urls import path
from . import views

app_name = 'mail_receiver'

urlpatterns = [
    # Mailgun webhook for inbound emails
    path('webhook/', views.MailgunWebhookView.as_view(), name='mailgun_webhook'),
    
    # Test endpoint
    path('webhook-test/', views.webhook_test_view, name='webhook_test'),
] 