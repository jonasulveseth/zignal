#!/usr/bin/env python
"""
Debug script for testing storage functionality (local or S3)
"""
import os
import sys
import django
import argparse

# Parse command line arguments
parser = argparse.ArgumentParser(description='Test storage functionality')
parser.add_argument('--s3', action='store_true', help='Use S3 storage for testing')
parser.add_argument('--local', action='store_true', help='Use local storage for testing')
args = parser.parse_args()

# Configure environment for the test
if args.s3:
    # Force S3 storage to be used for testing
    os.environ['USE_S3'] = 'TRUE'
elif args.local:
    # Force local storage
    os.environ['USE_S3'] = 'FALSE'
    
# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zignal.config.settings')
django.setup()

# Configure logging
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('storage_debug')

# Import needed modules after Django setup
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage


def test_storage():
    """Test storage by uploading, retrieving, and deleting a file"""
    logger.info("Testing storage configuration...")
    
    # Log environment settings 
    logger.info(f"DEBUG setting: {settings.DEBUG}")
    if hasattr(settings, 'DEFAULT_FILE_STORAGE'):
        logger.info(f"Current file storage: {settings.DEFAULT_FILE_STORAGE}")
        logger.info(f"Active storage class: {default_storage.__class__.__name__}")
    else:
        logger.warning("DEFAULT_FILE_STORAGE not explicitly set")
    
    # Determine if we're using S3
    is_s3 = isinstance(default_storage, S3Boto3Storage)
    logger.info(f"Using S3 storage: {is_s3}")
    
    # If using S3, log S3-specific settings
    if is_s3 and hasattr(settings, 'AWS_STORAGE_BUCKET_NAME'):
        logger.info(f"S3 bucket: {settings.AWS_STORAGE_BUCKET_NAME}")
        logger.info(f"S3 region: {getattr(settings, 'AWS_S3_REGION_NAME', 'not set')}")
        logger.info(f"AWS_ACCESS_KEY_ID: {'Set' if settings.AWS_ACCESS_KEY_ID else 'Not set'}")
        logger.info(f"AWS_SECRET_ACCESS_KEY: {'Set' if settings.AWS_SECRET_ACCESS_KEY else 'Not set'}")
        if hasattr(settings, 'AWS_S3_CUSTOM_DOMAIN'):
            logger.info(f"AWS_S3_CUSTOM_DOMAIN: {settings.AWS_S3_CUSTOM_DOMAIN}")
        
    logger.info(f"MEDIA_URL: {settings.MEDIA_URL}")
    logger.info(f"MEDIA_ROOT: {settings.MEDIA_ROOT}")
    
    # Create a test file path
    test_dir = "test"
    timestamp = django.utils.timezone.now().strftime("%Y%m%d_%H%M%S")
    test_path = f'{test_dir}/storage_test_{timestamp}.txt'
    test_content = f"Storage test file created at {django.utils.timezone.now().isoformat()}"
    
    try:
        # Create test directory if local storage
        if not is_s3 and test_dir:
            os.makedirs(os.path.join(settings.MEDIA_ROOT, test_dir), exist_ok=True)
            
        # 1. Save a test file
        logger.info(f"Saving test file to {test_path}")
        path = default_storage.save(test_path, ContentFile(test_content.encode('utf-8')))
        logger.info(f"File saved at: {path}")
        
        # 2. Check if file exists
        exists = default_storage.exists(path)
        logger.info(f"File exists in storage: {exists}")
        
        # 3. Get file URL
        url = default_storage.url(path)
        logger.info(f"File URL: {url}")
        
        # 4. Read file content
        logger.info("Reading file content...")
        content = default_storage.open(path).read().decode('utf-8')
        logger.info(f"Content: {content}")
        if content == test_content:
            logger.info("Content verification: SUCCESS")
        else:
            logger.error("Content verification: FAILED - content does not match")
            
        # 5. Get file size
        size = default_storage.size(path)
        logger.info(f"File size: {size} bytes")
        
        # 6. Delete the test file
        logger.info("Deleting test file...")
        default_storage.delete(path)
        
        # 7. Verify deletion
        exists_after_delete = default_storage.exists(path)
        logger.info(f"File exists after delete: {exists_after_delete}")
        if not exists_after_delete:
            logger.info("Delete verification: SUCCESS")
        else:
            logger.error("Delete verification: FAILED - file still exists")
        
        logger.info("Storage test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Error testing storage: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    # Run the tests
    if not args.s3 and not args.local:
        print("Please specify storage type: --s3 or --local")
        print("Example: python test_s3_storage.py --local")
        sys.exit(1)
        
    success = test_storage()
    sys.exit(0 if success else 1) 