import logging
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from .models import Notification
from .signals import notification_created, notification_updated, notification_read

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Service for managing notifications
    """
    
    @classmethod
    def create_notification(cls, recipient, title, message, level='info', **kwargs):
        """
        Create a notification for a user
        
        Args:
            recipient: User to notify
            title: Notification title
            message: Notification message
            level: Notification level (info, success, warning, error)
            **kwargs: Additional fields for the notification
                - related_object: Object to link to the notification
                - action_url: URL for the notification action
                - action_text: Text for the action button
                
        Returns:
            Notification: The created notification
        """
        with transaction.atomic():
            # Extract related object if provided
            related_object = kwargs.pop('related_object', None)
            content_type = None
            object_id = None
            
            if related_object:
                content_type = ContentType.objects.get_for_model(related_object)
                object_id = str(related_object.pk)
            
            # Create the notification
            notification = Notification.objects.create(
                recipient=recipient,
                title=title,
                message=message,
                level=level,
                content_type=content_type,
                object_id=object_id,
                **kwargs
            )
            
            # Send signal
            notification_created.send(sender=cls, notification=notification)
            
            logger.info(f"Created notification '{title}' for user {recipient}")
            
            return notification
    
    @classmethod
    def create_notification_for_users(cls, recipients, title, message, level='info', **kwargs):
        """
        Create a notification for multiple users
        
        Args:
            recipients: Queryset or list of users to notify
            title: Notification title
            message: Notification message
            level: Notification level (info, success, warning, error)
            **kwargs: Additional fields for the notification
                
        Returns:
            list: List of created notifications
        """
        notifications = []
        for recipient in recipients:
            notifications.append(
                cls.create_notification(
                    recipient=recipient,
                    title=title,
                    message=message,
                    level=level,
                    **kwargs
                )
            )
        return notifications
    
    @classmethod
    def mark_as_read(cls, notification):
        """
        Mark a notification as read
        
        Args:
            notification: Notification instance to mark as read
            
        Returns:
            Notification: The updated notification
        """
        if notification.unread:
            notification.unread = False
            notification.save(update_fields=['unread', 'updated_at'])
            
            # Send signal
            notification_read.send(sender=cls, notification=notification)
            
            logger.debug(f"Marked notification {notification.id} as read")
        
        return notification
    
    @classmethod
    def mark_all_as_read(cls, user):
        """
        Mark all unread notifications for a user as read
        
        Args:
            user: User whose notifications to mark as read
            
        Returns:
            int: Number of notifications marked as read
        """
        with transaction.atomic():
            unread_notifications = Notification.objects.filter(
                recipient=user, 
                unread=True
            )
            
            count = unread_notifications.count()
            
            if count > 0:
                # Update the notifications
                unread_notifications.update(unread=False)
                
                # Send signals for each notification
                for notification in unread_notifications:
                    notification_read.send(sender=cls, notification=notification)
                
                logger.info(f"Marked {count} notifications as read for user {user}")
            
            return count 