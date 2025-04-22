from django.apps import AppConfig


class MailReceiverConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'mail_receiver'

    def ready(self):
        # Import and register signal handlers
        import mail_receiver.handlers 