import json
import logging
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.dispatch import receiver
from django.db.models.signals import post_save, post_delete
from django.conf import settings

from .models import Notification
from .signals import notification_created, notification_updated, notification_read
from mail_receiver.signals import email_received, email_with_attachments_received, meeting_email_received
from users.models import User
from companies.models import Company

logger = logging.getLogger(__name__)
channel_layer = get_channel_layer()


@receiver(notification_created)
def handle_notification_created(sender, notification, **kwargs):
    """
    Handle notification created signal by sending WebSocket message
    
    Args:
        sender: The sending class
        notification: The Notification instance that was created
    """
    try:
        # Prepare the message
        message = {
            'type': 'notification',
            'action': 'created',
            'id': str(notification.id),
            'title': notification.title,
            'message': notification.message,
            'level': notification.level,
            'created_at': notification.created_at.isoformat(),
            'action_url': notification.action_url,
            'action_text': notification.action_text,
        }
        
        # Send to the user's notification group
        async_to_sync(channel_layer.group_send)(
            f'notifications_{notification.recipient.id}',
            {
                'type': 'notification_message',
                'message': message
            }
        )
        
        # Update the unread count
        unread_count = Notification.objects.filter(
            recipient=notification.recipient, 
            unread=True
        ).count()
        
        async_to_sync(channel_layer.group_send)(
            f'notifications_{notification.recipient.id}',
            {
                'type': 'notification_message',
                'message': {
                    'type': 'unread_count',
                    'count': unread_count
                }
            }
        )
        
        logger.info(f"Sent WebSocket notification to user {notification.recipient.id}")
        
    except Exception as e:
        logger.error(f"Error sending WebSocket notification: {str(e)}")


@receiver(notification_read)
def handle_notification_read(sender, notification, **kwargs):
    """
    Handle notification read signal by sending WebSocket message
    
    Args:
        sender: The sending class
        notification: The Notification instance that was marked as read
    """
    try:
        # Prepare the message
        message = {
            'type': 'notification',
            'action': 'read',
            'id': str(notification.id),
        }
        
        # Send to the user's notification group
        async_to_sync(channel_layer.group_send)(
            f'notifications_{notification.recipient.id}',
            {
                'type': 'notification_message',
                'message': message
            }
        )
        
        # Update the unread count
        unread_count = Notification.objects.filter(
            recipient=notification.recipient, 
            unread=True
        ).count()
        
        async_to_sync(channel_layer.group_send)(
            f'notifications_{notification.recipient.id}',
            {
                'type': 'notification_message',
                'message': {
                    'type': 'unread_count',
                    'count': unread_count
                }
            }
        )
        
        logger.info(f"Sent WebSocket notification read update to user {notification.recipient.id}")
        
    except Exception as e:
        logger.error(f"Error sending WebSocket notification read update: {str(e)}")


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
                        message=f"{instance.get_full_name() or instance.email} has registered",
                        level="info",
                        related_object=instance,
                        action_url=f"/admin/users/user/{instance.id}/change/",
                        action_text="View User"
                    )
        
        except Exception as e:
            logger.error(f"Error creating notification for new user: {str(e)}") 