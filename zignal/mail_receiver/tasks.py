import logging
from celery import shared_task
from .services import EmailProcessingService

logger = logging.getLogger(__name__)

@shared_task
def process_incoming_email_task(mailgun_data):
    """
    Celery task for processing incoming emails from Mailgun
    
    Args:
        mailgun_data (dict): Dictionary containing Mailgun webhook data
    
    Returns:
        str: Status message after processing
    """
    try:
        logger.info(f"Processing email from {mailgun_data.get('sender', 'unknown')}")
        email_service = EmailProcessingService()
        email = email_service.process_incoming_email(mailgun_data)
        
        return f"Successfully processed email: {email.message_id}"
    
    except Exception as e:
        logger.error(f"Error processing email in Celery task: {str(e)}")
        raise 