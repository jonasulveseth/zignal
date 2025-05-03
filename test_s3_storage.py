#!/usr/bin/env python
"""
Debug script for testing S3 storage functionality
"""
import os
import sys
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zignal.config.settings')
django.setup()

# Configure logging
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('s3_storage_debug')

# Import needed modules after Django setup
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings


def test_s3_storage():
    """Test S3 storage by uploading, retrieving, and deleting a file"""
    logger.info("Testing S3 storage configuration...")
    
    # Log environment settings 
    logger.info(f"DEBUG setting: {settings.DEBUG}")
    if hasattr(settings, 'DEFAULT_FILE_STORAGE'):
        logger.info(f"Current file storage: {settings.DEFAULT_FILE_STORAGE}")
    else:
        logger.warning("DEFAULT_FILE_STORAGE not explicitly set")
    
    if hasattr(settings, 'AWS_STORAGE_BUCKET_NAME'):
        logger.info(f"S3 bucket: {settings.AWS_STORAGE_BUCKET_NAME}")
        logger.info(f"S3 region: {getattr(settings, 'AWS_S3_REGION_NAME', 'not set')}")
    else:
        logger.warning("AWS_STORAGE_BUCKET_NAME not set")
        
    logger.info(f"MEDIA_URL: {settings.MEDIA_URL}")
    logger.info(f"MEDIA_ROOT: {settings.MEDIA_ROOT}")
    
    # Create a test file path
    test_path = 'test/s3_test.txt'
    test_content = f"S3 test file created at {django.utils.timezone.now().isoformat()}"
    
    try:
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
        
        logger.info("S3 storage test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Error testing S3 storage: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    # Run the tests
    success = test_s3_storage()
    sys.exit(0 if success else 1) 