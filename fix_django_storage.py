#!/usr/bin/env python
"""
Diagnose and fix Django's storage backend, ensuring S3Boto3Storage is used.
"""
import os
import logging
import django

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zignal.config.settings')
django.setup()

# Import Django modules
from django.core.files.storage import default_storage
from django.conf import settings
from django.core.files.base import ContentFile

def diagnose_storage():
    """Diagnose the storage configuration"""
    logger.info("=== STORAGE CONFIGURATION DIAGNOSIS ===")
    
    # Check settings
    logger.info(f"DEBUG: {settings.DEBUG}")
    logger.info(f"USE_S3: {getattr(settings, 'USE_S3', False)}")
    logger.info(f"DEFAULT_FILE_STORAGE: {settings.DEFAULT_FILE_STORAGE}")
    
    # Check actual storage class
    logger.info(f"Storage class: {default_storage.__class__.__name__}")
    
    # Check if we have the expected S3 storage class
    try:
        from storages.backends.s3boto3 import S3Boto3Storage
        logger.info(f"Is S3Boto3Storage: {isinstance(default_storage, S3Boto3Storage)}")
    except ImportError:
        logger.error("django-storages not installed, S3Boto3Storage not available")
    
    # Check custom storage class
    if hasattr(settings, 'MEDIA_STORAGE_CLASS'):
        logger.info(f"MEDIA_STORAGE_CLASS: {settings.MEDIA_STORAGE_CLASS.__name__}")
        
        # Create instance of custom storage class
        custom_storage = settings.MEDIA_STORAGE_CLASS()
        logger.info(f"Custom storage class type: {type(custom_storage).__name__}")
    else:
        logger.info("No MEDIA_STORAGE_CLASS found in settings")
    
    # Test file storage
    test_content = b"Test content for storage diagnosis"
    test_path = "test_storage_diagnosis.txt"
    
    try:
        # Save test file
        path = default_storage.save(test_path, ContentFile(test_content))
        url = default_storage.url(path)
        
        logger.info(f"Test file saved at: {path}")
        logger.info(f"Test file URL: {url}")
        
        # Check if file exists
        exists = default_storage.exists(path)
        logger.info(f"File exists in storage: {exists}")
        
        # Clean up
        default_storage.delete(path)
        logger.info("Test file deleted")
    except Exception as e:
        logger.error(f"Error testing storage: {str(e)}")
    
    # Check if boto3 is properly configured
    try:
        import boto3
        
        s3 = boto3.client(
            's3', 
            aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
            region_name=os.environ.get('AWS_S3_REGION_NAME', 'eu-west-1')
        )
        
        # Test S3 connection
        response = s3.list_buckets()
        buckets = [bucket['Name'] for bucket in response['Buckets']]
        logger.info(f"S3 buckets accessible: {buckets}")
        
        # Check specific bucket
        bucket_name = os.environ.get('AWS_STORAGE_BUCKET_NAME', 'zignalse')
        if bucket_name in buckets:
            logger.info(f"Target bucket '{bucket_name}' is accessible")
        else:
            logger.warning(f"Target bucket '{bucket_name}' not found in accessible buckets")
    except Exception as e:
        logger.error(f"Error checking boto3 configuration: {str(e)}")

def fix_storage_issue():
    """Attempt to fix common storage configuration issues"""
    logger.info("\n=== ATTEMPTING TO FIX STORAGE ISSUES ===")
    
    try:
        # Ensure django-storages is installed
        try:
            import storages
            logger.info("django-storages is installed")
        except ImportError:
            logger.error("django-storages is not installed - please install it with pip")
            return
            
        # Ensure boto3 is installed
        try:
            import boto3
            logger.info("boto3 is installed")
        except ImportError:
            logger.error("boto3 is not installed - please install it with pip")
            return
            
        # Get required AWS settings
        aws_access_key = os.environ.get('AWS_ACCESS_KEY_ID')
        aws_secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
        aws_bucket = os.environ.get('AWS_STORAGE_BUCKET_NAME')
        
        if not all([aws_access_key, aws_secret_key, aws_bucket]):
            logger.error("AWS credentials or bucket name missing from environment")
            return
            
        logger.info("AWS credentials are set in environment")
        
        # Force Django to use S3 storage
        os.environ['USE_S3'] = 'TRUE'
        
        # Reload settings
        from django.core.files.storage import default_storage
        from django.utils.module_loading import import_string
        from django.conf import settings
        
        # Manually create S3 storage instance
        from storages.backends.s3boto3 import S3Boto3Storage
        
        class MediaStorage(S3Boto3Storage):
            location = os.environ.get('AWS_LOCATION', 'media')
            file_overwrite = False
            default_acl = 'private'
        
        # Create test file with direct S3 storage
        test_storage = MediaStorage()
        test_content = b"Test content for S3 storage fix"
        test_path = "storage_fix_test.txt"
        
        path = test_storage.save(test_path, ContentFile(test_content))
        url = test_storage.url(path)
        
        logger.info(f"Test file saved with custom S3 storage at: {path}")
        logger.info(f"Test file URL: {url}")
        
        # Check if file exists
        exists = test_storage.exists(path)
        logger.info(f"File exists in S3 storage: {exists}")
        
        # Clean up
        test_storage.delete(path)
        logger.info("Test file deleted")
        
        logger.info("\nRECOMMENDATIONS:")
        logger.info("1. Ensure DEFAULT_FILE_STORAGE is set to 'storages.backends.s3boto3.S3Boto3Storage'")
        logger.info("2. Set USE_S3=TRUE in environment variables")
        logger.info("3. Make sure all AWS_* environment variables are correctly set")
        logger.info("4. Restart the application to apply changes")
        
    except Exception as e:
        logger.error(f"Error fixing storage: {str(e)}")

if __name__ == "__main__":
    diagnose_storage()
    fix_storage_issue() 