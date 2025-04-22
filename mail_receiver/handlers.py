import logging
from django.dispatch import receiver
from .signals import email_received, email_with_attachments_received, meeting_email_received

logger = logging.getLogger(__name__)


@receiver(email_received)
def handle_email_received(sender, email, **kwargs):
    """
    Handler for when a new email is received and processed
    
    Args:
        sender: The sending class (usually EmailProcessingService)
        email: The IncomingEmail instance that was processed
    """
    logger.info(f"Email received and processed: {email.id} - {email.subject}")
    # Add your custom logic here for handling new emails
    

@receiver(email_with_attachments_received)
def handle_email_with_attachments(sender, email, attachments, **kwargs):
    """
    Handler for when an email with attachments is received
    
    Args:
        sender: The sending class (usually EmailProcessingService)
        email: The IncomingEmail instance that was processed
        attachments: List of EmailAttachment instances
    """
    attachment_count = len(attachments)
    logger.info(f"Email received with {attachment_count} attachments: {email.id} - {email.subject}")
    # Add your custom logic here for handling emails with attachments
    

@receiver(meeting_email_received)
def handle_meeting_email(sender, email, meeting, **kwargs):
    """
    Handler for when an email results in a meeting being created
    
    Args:
        sender: The sending class (usually EmailProcessingService)
        email: The IncomingEmail instance that was processed
        meeting: The MeetingTranscript instance that was created
    """
    logger.info(f"Meeting created from email: {email.id} -> Meeting {meeting.id} ({meeting.meeting_title})")
    # Add your custom logic here for handling meeting creation from emails
    # For example, you could notify stakeholders or update related records 