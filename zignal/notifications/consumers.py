import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.db.models import Q

from .models import Notification

logger = logging.getLogger(__name__)
User = get_user_model()


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time notifications
    Allows users to receive notifications in real-time
    """
    
    async def connect(self):
        """
        Handle WebSocket connection
        """
        # Get the user from the scope
        self.user = self.scope['user']
        
        # Anonymous users cannot receive notifications
        if self.user.is_anonymous:
            await self.close()
            return
        
        # Create a user-specific channel
        self.user_group_name = f'notifications_{self.user.id}'
        
        # Add the connection to the user's group
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )
        
        # Accept the connection
        await self.accept()
        
        # Send unread count on connection
        unread_count = await self.get_unread_count()
        await self.send(text_data=json.dumps({
            'type': 'unread_count',
            'count': unread_count
        }))
        
        logger.info(f"User {self.user.id} connected to notification WebSocket")
    
    async def disconnect(self, close_code):
        """
        Handle WebSocket disconnection
        """
        if hasattr(self, 'user_group_name'):
            # Remove the connection from the user's group
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )
            
            logger.info(f"User {self.user.id} disconnected from notification WebSocket")
    
    async def receive(self, text_data):
        """
        Handle messages received from WebSocket
        
        Args:
            text_data: JSON string with message data
        """
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type')
            
            # Handle different message types
            if message_type == 'mark_read':
                notification_id = text_data_json.get('id')
                if notification_id:
                    # Mark notification as read
                    success = await self.mark_notification_read(notification_id)
                    
                    if success:
                        # Get updated unread count
                        unread_count = await self.get_unread_count()
                        
                        # Send updated count back to client
                        await self.send(text_data=json.dumps({
                            'type': 'unread_count',
                            'count': unread_count
                        }))
            
            elif message_type == 'mark_all_read':
                # Mark all notifications as read
                count = await self.mark_all_read()
                
                # Send updated count back to client
                await self.send(text_data=json.dumps({
                    'type': 'unread_count',
                    'count': 0,
                    'marked_count': count
                }))
            
            elif message_type == 'get_unread_count':
                # Get unread count
                unread_count = await self.get_unread_count()
                
                # Send count back to client
                await self.send(text_data=json.dumps({
                    'type': 'unread_count',
                    'count': unread_count
                }))
        
        except json.JSONDecodeError:
            logger.warning(f"Received invalid JSON from user {self.user.id}")
        except Exception as e:
            logger.error(f"Error processing WebSocket message: {str(e)}")
    
    async def notification_message(self, event):
        """
        Handle notification messages from the channel layer
        
        Args:
            event: Event data including the notification
        """
        # Extract the message content
        message = event.get('message', {})
        
        # Send the message to the WebSocket
        await self.send(text_data=json.dumps(message))
    
    @database_sync_to_async
    def get_unread_count(self):
        """
        Get count of unread notifications for the user
        
        Returns:
            int: Count of unread notifications
        """
        return Notification.objects.filter(recipient=self.user, unread=True).count()
    
    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        """
        Mark a notification as read
        
        Args:
            notification_id: ID of the notification to mark as read
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            notification = Notification.objects.get(
                id=notification_id, 
                recipient=self.user,
                unread=True
            )
            notification.mark_as_read()
            return True
        except Notification.DoesNotExist:
            return False
    
    @database_sync_to_async
    def mark_all_read(self):
        """
        Mark all unread notifications for the user as read
        
        Returns:
            int: Count of notifications marked as read
        """
        unread_notifications = Notification.objects.filter(
            recipient=self.user, 
            unread=True
        )
        
        count = unread_notifications.count()
        unread_notifications.update(unread=False)
        
        return count 