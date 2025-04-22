from django.dispatch import Signal

# Signal sent when a new notification is created
# Provides: notification (Notification instance)
notification_created = Signal()

# Signal sent when a notification is updated
# Provides: notification (Notification instance)
notification_updated = Signal()

# Signal sent when a notification is read
# Provides: notification (Notification instance)
notification_read = Signal() 