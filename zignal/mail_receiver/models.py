from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid
import os

class IncomingEmail(models.Model):
    """
    A model to store incoming emails received through Mailgun
    """
    STATUS_CHOICES = (
        ('new', 'New'),
        ('processing', 'Processing'),
        ('processed', 'Processed'),
        ('failed', 'Failed'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sender = models.EmailField(max_length=255)
    recipient = models.EmailField(max_length=255)
    subject = models.CharField(max_length=512, blank=True)
    body_plain = models.TextField(blank=True)
    body_html = models.TextField(blank=True)
    stripped_text = models.TextField(blank=True)
    stripped_html = models.TextField(blank=True)
    message_id = models.CharField(max_length=255, blank=True)
    mailgun_timestamp = models.IntegerField(null=True, blank=True)
    mailgun_id = models.CharField(max_length=255, blank=True)
    
    # Storage tracking
    data_silo = models.ForeignKey(
        'datasilo.DataSilo',
        on_delete=models.SET_NULL,
        related_name='received_emails',
        null=True,
        blank=True
    )
    
    # For MeetingBaaS integration
    meeting_created = models.BooleanField(default=False)
    meeting_transcript = models.ForeignKey(
        'agents.MeetingTranscript',
        on_delete=models.SET_NULL,
        related_name='source_emails',
        null=True,
        blank=True
    )
    
    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='new'
    )
    received_at = models.DateTimeField(default=timezone.now)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Incoming Email'
        verbose_name_plural = 'Incoming Emails'
        ordering = ['-received_at']
    
    def __str__(self):
        return f"Email from {self.sender}: {self.subject}"
    
    def mark_as_processed(self):
        """Mark email as processed and record timestamp"""
        self.status = 'processed'
        self.processed_at = timezone.now()
        self.save()
    
    def mark_as_failed(self):
        """Mark email as failed and record timestamp"""
        self.status = 'failed'
        self.processed_at = timezone.now()
        self.save()


def email_attachment_path(instance, filename):
    """
    Generate file path for email attachments
    Format: email_attachments/<year>/<month>/<email_id>/<filename>
    """
    date = timezone.now()
    return os.path.join(
        'email_attachments',
        str(date.year),
        str(date.month),
        str(instance.email.id),
        filename
    )


class EmailAttachment(models.Model):
    """
    Model to store email attachments
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.ForeignKey(
        IncomingEmail,
        on_delete=models.CASCADE,
        related_name='attachments'
    )
    file = models.FileField(upload_to=email_attachment_path)
    content_type = models.CharField(max_length=255, blank=True)
    filename = models.CharField(max_length=255, blank=True)
    size = models.IntegerField(default=0)
    
    # Reference to data file if stored in data silo
    data_file = models.ForeignKey(
        'datasilo.DataFile',
        on_delete=models.SET_NULL,
        related_name='email_attachments',
        null=True,
        blank=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Email Attachment'
        verbose_name_plural = 'Email Attachments'
    
    def __str__(self):
        return f"{self.filename} ({self.size} bytes)" 