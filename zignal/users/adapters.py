from allauth.account.adapter import DefaultAccountAdapter
import uuid
import logging

logger = logging.getLogger(__name__)

class CustomAccountAdapter(DefaultAccountAdapter):
    """
    Custom adapter for django-allauth to handle username generation and signup issues
    """
    
    def clean_username(self, username, *args, **kwargs):
        """
        Allow blank usernames and generate a unique one if needed
        """
        logger.debug(f"Cleaning username: {username}")
        
        # If no username is provided, generate a unique one based on the email
        if not username:
            # Get the username from email, with fallback to a UUID
            try:
                # Extract username from email
                email = kwargs.get('email', '')
                if email:
                    username = email.split('@')[0]
                else:
                    username = f"user_{uuid.uuid4().hex[:8]}"
                
                logger.debug(f"Generated username from email: {username}")
            except Exception as e:
                # If there's any error, fallback to a simple UUID
                username = f"user_{uuid.uuid4().hex[:8]}"
                logger.debug(f"Generated UUID username: {username}")
        
        return super().clean_username(username, *args, **kwargs)
    
    def save_user(self, request, user, form, commit=True):
        """
        Save the newly created user instance
        """
        logger.debug(f"Saving user with username: {user.username}, email: {user.email}")
        
        # Set user as active by default
        user.is_active = True
        
        # Set default user type
        user.user_type = 'company_user'
        
        # Call the parent save_user method
        result = super().save_user(request, user, form, commit)
        
        logger.debug(f"User saved: {user.id}, username: {user.username}")
        return result
    
    def get_login_redirect_url(self, request):
        """
        Redirect to the appropriate URL after login
        """
        # Use the URL specified in settings
        redirect_url = super().get_login_redirect_url(request)
        
        logger.debug(f"Login redirect URL: {redirect_url}")
        return redirect_url 