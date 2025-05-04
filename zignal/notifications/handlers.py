import json
import logging
from django.dispatch import receiver
from django.db.models.signals import post_save, post_delete
from django.conf import settings

from .models import Notification
from .signals import notification_created, notification_updated, notification_read
from mail_receiver.signals import email_received, email_with_attachments_received, meeting_email_received
from users.models import User
from companies.models import Company

logger = logging.getLogger(__name__)


@receiver(notification_created)
def handle_notification_created(sender, notification, **kwargs):
    """
    Handle notification created signal
    
    Args:
        sender: The sending class
        notification: The Notification instance that was created
    """
    try:
        logger.info(f"New notification created for user {notification.recipient.id}: {notification.title}")
    except Exception as e:
        logger.error(f"Error handling notification created: {str(e)}")


@receiver(notification_read)
def handle_notification_read(sender, notification, **kwargs):
    """
    Handle notification read signal
    
    Args:
        sender: The sending class
        notification: The Notification instance that was marked as read
    """
    try:
        logger.info(f"Notification marked as read for user {notification.recipient.id}: {notification.id}")
    except Exception as e:
        logger.error(f"Error handling notification read: {str(e)}")


# Integration with mail_receiver signals
@receiver(email_received)
def handle_email_received(sender, email, **kwargs):
    """
    Create notification when a new email is received
    
    Args:
        sender: The sending class
        email: The IncomingEmail instance
    """
    from .services import NotificationService
    
    try:
        # Get admin users to notify
        admin_users = User.objects.filter(user_type='admin')
        
        if admin_users.exists():
            # Create notification for admins
            for admin in admin_users:
                NotificationService.create_notification(
                    recipient=admin,
                    title="New Email Received",
                    message=f"Email from {email.sender} with subject: {email.subject}",
                    level="info",
                    related_object=email,
                    action_url=f"/admin/mail_receiver/incomingemail/{email.id}/change/",
                    action_text="View Email"
                )
            
            logger.info(f"Created notifications for new email {email.id}")
    
    except Exception as e:
        logger.error(f"Error creating notification for email: {str(e)}")


@receiver(email_with_attachments_received)
def handle_email_with_attachments(sender, email, attachments, **kwargs):
    """
    Create notification when an email with attachments is received
    
    Args:
        sender: The sending class
        email: The IncomingEmail instance
        attachments: List of EmailAttachment instances
    """
    from .services import NotificationService
    
    try:
        # Get admin users to notify
        admin_users = User.objects.filter(user_type='admin')
        
        if admin_users.exists() and attachments:
            # Create notification for admins
            for admin in admin_users:
                NotificationService.create_notification(
                    recipient=admin,
                    title="Email With Attachments Received",
                    message=f"Email from {email.sender} with {len(attachments)} attachment(s)",
                    level="info",
                    related_object=email,
                    action_url=f"/admin/mail_receiver/incomingemail/{email.id}/change/",
                    action_text="View Email"
                )
            
            logger.info(f"Created notifications for email {email.id} with attachments")
    
    except Exception as e:
        logger.error(f"Error creating notification for email with attachments: {str(e)}")


@receiver(meeting_email_received)
def handle_meeting_email(sender, email, meeting, **kwargs):
    """
    Create notification when an email creates a meeting
    
    Args:
        sender: The sending class
        email: The IncomingEmail instance
        meeting: The MeetingTranscript instance
    """
    from .services import NotificationService
    
    try:
        # Get users to notify - admins and company users
        admin_users = User.objects.filter(user_type__in=['admin', 'portfolio_manager'])
        
        # Also notify company users if the meeting has a company
        company_users = []
        if meeting.company:
            company_users = User.objects.filter(
                user_type='company_user',
                company=meeting.company
            )
        
        users_to_notify = list(admin_users) + list(company_users)
        
        # Create notifications
        for user in users_to_notify:
            NotificationService.create_notification(
                recipient=user,
                title="New Meeting Scheduled",
                message=f"Meeting '{meeting.meeting_title}' has been scheduled via email",
                level="success",
                related_object=meeting,
                action_url=f"/meeting/{meeting.id}/",
                action_text="View Meeting"
            )
        
        logger.info(f"Created notifications for meeting {meeting.id} created from email")
    
    except Exception as e:
        logger.error(f"Error creating notification for meeting email: {str(e)}")


# Listen for model post-save signals to create notifications for related users
@receiver(post_save, sender=User)
def handle_user_created(sender, instance, created, **kwargs):
    """Create notification when a new user is created"""
    from .services import NotificationService
    
    if created:
        try:
            # Notify admins about new user
            admin_users = User.objects.filter(
                user_type='admin'
            ).exclude(id=instance.id)
            
            if admin_users.exists():
                for admin in admin_users:
                    NotificationService.create_notification(
                        recipient=admin,
                        title="New User Registered",
                        message=f"User {instance.email} has registered.",
                        level="info",
                        related_object=instance,
                        action_url=f"/admin/users/user/{instance.id}/change/",
                        action_text="View User"
                    )
                
                logger.info(f"Created notifications for new user {instance.id}")
        
        except Exception as e:
            logger.error(f"Error creating notification for new user: {str(e)}")


@receiver(post_save, sender=Company)
def handle_company_created(sender, instance, created, **kwargs):
    """Create notification when a new company is created"""
    from .services import NotificationService
    
    if created:
        try:
            # Notify portfolio managers about new company
            portfolio_managers = User.objects.filter(
                user_type='portfolio_manager'
            )
            
            if portfolio_managers.exists():
                for manager in portfolio_managers:
                    NotificationService.create_notification(
                        recipient=manager,
                        title="New Company Added",
                        message=f"Company {instance.name} has been added.",
                        level="info",
                        related_object=instance,
                        action_url=f"/companies/{instance.id}/",
                        action_text="View Company"
                    )
                
                logger.info(f"Created notifications for new company {instance.id}")
        
        except Exception as e:
            logger.error(f"Error creating notification for new company: {str(e)}") 