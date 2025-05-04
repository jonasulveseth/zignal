#!/usr/bin/env python
"""
Script to fix S3 storage configuration on production.
Run this on Heroku with: heroku run python fix_s3_storage_production.py
"""
import os
import django
import sys
import logging
import time

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zignal.config.settings')
django.setup()

from django.core.files.storage import default_storage
from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage
import boto3

def fix_s3_storage():
    """Fix S3 storage configuration and adjust file paths"""
    logger.info("==== S3 Storage Production Fixer ====")
    
    # Force S3 to be used
    os.environ['USE_S3'] = 'TRUE'
    
    # Get AWS settings
    aws_access_key = os.environ.get('AWS_ACCESS_KEY_ID', '')
    aws_secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY', '')
    aws_bucket = os.environ.get('AWS_STORAGE_BUCKET_NAME', '')
    aws_location = os.environ.get('AWS_LOCATION', 'media')
    aws_region = os.environ.get('AWS_S3_REGION_NAME', 'eu-west-1')
    
    logger.info(f"S3 Settings: Bucket={aws_bucket}, Region={aws_region}, Location={aws_location}")
    
    # Check current default storage
    logger.info(f"Current default_storage: {default_storage.__class__.__name__}")
    if hasattr(default_storage, '_wrapped'):
        logger.info(f"Wrapped storage: {default_storage._wrapped.__class__.__name__}")
    
    # Step 1: Ensure we have a MediaStorage class
    s3_storage = None
    if hasattr(settings, 'MEDIA_STORAGE_CLASS'):
        logger.info("Found MEDIA_STORAGE_CLASS in settings")
        storage_class = settings.MEDIA_STORAGE_CLASS
        s3_storage = storage_class()
    else:
        logger.error("MEDIA_STORAGE_CLASS not defined in settings!")
        
        # Define it ourselves
        class MediaStorage(S3Boto3Storage):
            location = aws_location
            file_overwrite = False
            default_acl = 'private'
            
            def _normalize_name(self, name):
                """
                Override to handle both absolute and relative paths
                """
                if name.startswith('/'):
                    name = name[1:]
                
                # Ensure media/ prefix if AWS_LOCATION is 'media'
                if aws_location == 'media' and not name.startswith('media/'):
                    name = f'media/{name}'
                
                return super()._normalize_name(name)
                
        logger.info("Created temporary MediaStorage class")
        s3_storage = MediaStorage()
    
    # Step 2: Force default_storage to use our S3 storage
    if hasattr(default_storage, '_wrapped'):
        default_storage._wrapped = s3_storage
        logger.info(f"Replaced default_storage with {s3_storage.__class__.__name__}")
    else:
        logger.error("Could not replace default_storage - no _wrapped attribute!")
    
    # Step 3: Fix existing file paths in the database
    fix_file_paths()
    
    # Step 4: Verify storage configuration
    test_s3_storage()
    
    logger.info("S3 storage fix completed")

def fix_file_paths():
    """Fix existing file paths in the database to match S3 storage requirements"""
    from zignal.datasilo.models import DataFile
    
    logger.info("Fixing existing file paths in database...")
    
    # Get AWS settings
    aws_bucket = os.environ.get('AWS_STORAGE_BUCKET_NAME', '')
    aws_location = os.environ.get('AWS_LOCATION', 'media')
    aws_access_key = os.environ.get('AWS_ACCESS_KEY_ID', '')
    aws_secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY', '')
    aws_region = os.environ.get('AWS_S3_REGION_NAME', 'eu-west-1')
    
    # Get a boto3 client
    s3_client = boto3.client(
        's3', 
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key,
        region_name=aws_region
    )
    
    # Get all files with vector_store_status='failed'
    failed_files = DataFile.objects.filter(vector_store_status='failed')
    logger.info(f"Found {failed_files.count()} failed files to fix")
    
    # Get all files regardless of status
    all_files = DataFile.objects.all()
    logger.info(f"Found {all_files.count()} total files in database")
    
    # Process failed files first
    for i, data_file in enumerate(failed_files):
        logger.info(f"Processing failed file {i+1}/{failed_files.count()}: {data_file.id} - {data_file.name}")
        process_file_path(data_file, s3_client, aws_bucket, aws_location)
    
    # Process remaining files
    remaining_files = all_files.exclude(id__in=[f.id for f in failed_files])
    logger.info(f"Processing {remaining_files.count()} remaining files")
    
    for i, data_file in enumerate(remaining_files):
        if i % 10 == 0:  # Log progress every 10 files
            logger.info(f"Processing file {i+1}/{remaining_files.count()}")
        process_file_path(data_file, s3_client, aws_bucket, aws_location)

def process_file_path(data_file, s3_client, aws_bucket, aws_location):
    """Process an individual file's path"""
    current_path = data_file.file.name
    
    # Skip empty paths
    if not current_path:
        return
    
    # Create possible S3 keys to check
    possible_keys = []
    
    # Original key
    possible_keys.append(current_path)
    
    # With media/ prefix if not already there
    if not current_path.startswith('media/'):
        possible_keys.append(f"media/{current_path}")
    
    # Without media/ prefix if it's there
    if current_path.startswith('media/'):
        possible_keys.append(current_path[6:])
    
    # With AWS_LOCATION prefix
    if aws_location and not current_path.startswith(f"{aws_location}/"):
        possible_keys.append(f"{aws_location}/{current_path}")
        
        # Also with location but without media/ if it has that
        if current_path.startswith('media/'):
            possible_keys.append(f"{aws_location}/{current_path[6:]}")
    
    # Remove duplicates but preserve order
    possible_keys = list(dict.fromkeys(possible_keys))
    
    # Find which path exists in S3
    found_key = None
    try:
        for key in possible_keys:
            try:
                s3_client.head_object(Bucket=aws_bucket, Key=key)
                found_key = key
                break
            except Exception:
                continue
        
        if found_key and found_key != current_path:
            # Update the path in the database
            logger.info(f"Updating file {data_file.id} path from '{current_path}' to '{found_key}'")
            data_file.file.name = found_key
            data_file.save(update_fields=['file'])
            
            # If this was a failed vector store processing, reset its status
            if data_file.vector_store_status == 'failed':
                data_file.vector_store_status = 'pending'
                data_file.save(update_fields=['vector_store_status'])
                logger.info(f"Reset vector_store_status to pending for file {data_file.id}")
    
    except Exception as e:
        logger.error(f"Error processing file {data_file.id}: {str(e)}")

def test_s3_storage():
    """Test S3 storage configuration by creating and deleting a test file"""
    logger.info("Testing S3 storage configuration...")
    
    # Create a unique test file
    test_file = f"test_s3_fix_{int(time.time())}.txt"
    test_content = f"Test content created at {time.time()}"
    
    try:
        # Save file
        path = default_storage.save(test_file, test_content.encode('utf-8'))
        logger.info(f"Test file saved at: {path}")
        
        # Get URL
        url = default_storage.url(path)
        logger.info(f"Test file URL: {url}")
        
        # Check exists
        exists = default_storage.exists(path)
        logger.info(f"File exists: {exists}")
        
        if exists:
            # Delete test file
            default_storage.delete(path)
            logger.info("Test file deleted")
            return True
        else:
            logger.error("Test file doesn't exist after saving!")
            return False
            
    except Exception as e:
        logger.error(f"Error testing S3 storage: {str(e)}")
        return False

if __name__ == "__main__":
    fix_s3_storage() 