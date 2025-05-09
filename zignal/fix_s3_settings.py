"""
Fix script to ensure S3 storage is properly configured in Django.
This module should be imported at the end of settings.py.
"""
import os
import sys
import logging
from django.core.files.storage import default_storage

logger = logging.getLogger(__name__)

def ensure_s3_storage():
    """
    Force Django to use S3 storage regardless of initialization order
    This is a more robust approach than relying on Django's init process
    """
    from django.conf import settings
    
    # Only proceed if we have AWS credentials and bucket name
    if not (settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY and settings.AWS_STORAGE_BUCKET_NAME):
        print("WARNING: AWS S3 credentials or bucket name not set correctly. S3 storage will not be used.")
        return False
    
    try:
        # Import the S3 storage class
        from storages.backends.s3boto3 import S3Boto3Storage
        
        # Create a custom S3 storage class with our settings
        class ForcedS3Storage(S3Boto3Storage):
            location = settings.AWS_LOCATION
            file_overwrite = settings.AWS_S3_FILE_OVERWRITE
            default_acl = settings.AWS_DEFAULT_ACL
            
            def _normalize_name(self, name):
                """
                Override to handle both absolute and relative paths
                This ensures consistent storage path construction 
                regardless of what Django passes in
                """
                if name.startswith('/'):
                    name = name[1:]
                    
                # Ensure media/ prefix if AWS_LOCATION is 'media'
                if settings.AWS_LOCATION == 'media' and not name.startswith('media/'):
                    name = f'media/{name}'
                    
                return super()._normalize_name(name)
        
        # Create an instance of our storage class
        forced_storage = ForcedS3Storage()
        
        # Check the current storage type
        current_storage_type = default_storage.__class__.__name__
        
        # Only force if not already using S3
        if 'S3' not in current_storage_type and 'Boto' not in current_storage_type:
            # Replace the default storage
            default_storage._wrapped = forced_storage
            print(f"Successfully forced S3 storage (was: {current_storage_type}, now: {default_storage.__class__.__name__})")
            return True
        else:
            print(f"Already using S3 storage: {current_storage_type}")
            return True
            
    except Exception as e:
        print(f"Error forcing S3 storage: {str(e)}")
        logger.exception("Error forcing S3 storage")
        return False

# Call the function immediately when imported
ensure_s3_storage() 