from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
import uuid


class Notification(models.Model):
    """
    Model for storing user notifications
    
    Notifications can be linked to any model via GenericForeignKey
    and have different levels (info, success, warning, error)
    """
    LEVELS = (
        ('info', 'Information'),
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('error', 'Error'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    level = models.CharField(max_length=10, choices=LEVELS, default='info')
    
    # Optional link to related object
    content_type = models.ForeignKey(
        ContentType, 
        on_delete=models.CASCADE,
        null=True, 
        blank=True
    )
    object_id = models.CharField(max_length=255, blank=True, null=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Action URL (optional)
    action_url = models.CharField(max_length=255, blank=True)
    action_text = models.CharField(max_length=50, blank=True)
    
    # Status tracking
    unread = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'unread']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.get_level_display()})"
    
    def mark_as_read(self):
        """Mark the notification as read"""
        if self.unread:
            self.unread = False
            self.save(update_fields=['unread', 'updated_at'])
    
    @classmethod
    def create_for_user(cls, user, title, message, level='info', **kwargs):
        """
        Convenience method to create a notification for a user
        
        Args:
            user: User to notify
            title: Notification title
            message: Notification message
            level: Notification level (info, success, warning, error)
            **kwargs: Additional fields for the notification
            
        Returns:
            Notification: The created notification
        """
        return cls.objects.create(
            recipient=user, 
            title=title, 
            message=message, 
            level=level, 
            **kwargs
        )
    
    @classmethod
    def create_for_users(cls, users, title, message, level='info', **kwargs):
        """
        Create a notification for multiple users
        
        Args:
            users: Queryset or list of users to notify
            title: Notification title
            message: Notification message
            level: Notification level (info, success, warning, error)
            **kwargs: Additional fields for the notification
            
        Returns:
            list: List of created notifications
        """
        notifications = []
        for user in users:
            notifications.append(
                cls.objects.create(
                    recipient=user,
                    title=title,
                    message=message,
                    level=level,
                    **kwargs
                )
            )
        return notifications 