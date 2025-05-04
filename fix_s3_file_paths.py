#!/usr/bin/env python
"""
Script to fix existing file paths in the database to match S3 format.
"""
import os
import django
import logging
import boto3
from django.conf import settings

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zignal.config.settings')
django.setup()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_file_paths():
    """Fix file paths in the database to match S3 format"""
    from datasilo.models import DataFile
    
    # Get AWS settings
    aws_bucket = os.environ.get('AWS_STORAGE_BUCKET_NAME', '')
    aws_location = os.environ.get('AWS_LOCATION', 'media')
    aws_access_key = os.environ.get('AWS_ACCESS_KEY_ID', '')
    aws_secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY', '')
    aws_region = os.environ.get('AWS_S3_REGION_NAME', 'eu-west-1')
    
    # Set up S3 client
    s3_client = boto3.client(
        's3',
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key,
        region_name=aws_region
    )
    
    # Get all DataFile objects
    datafiles = DataFile.objects.all()
    logger.info(f"Found {datafiles.count()} DataFile objects")
    
    # Set up S3 storage if available
    s3_storage = None
    if hasattr(settings, 'MEDIA_STORAGE_CLASS'):
        s3_storage = settings.MEDIA_STORAGE_CLASS()
    
    for datafile in datafiles:
        current_path = datafile.file.name
        logger.info(f"Checking file: {datafile.id} - {datafile.name} - Path: {current_path}")
        
        # Skip files that don't exist in the database
        if not current_path:
            logger.warning(f"File {datafile.id} has no path, skipping")
            continue
        
        # Generate possible S3 paths
        possible_keys = []
        
        # Original key
        possible_keys.append(current_path)
        
        # With media/ prefix if not already there
        if not current_path.startswith('media/'):
            possible_keys.append(f"media/{current_path}")
        
        # Without media/ prefix if it's there
        if current_path.startswith('media/'):
            possible_keys.append(current_path[6:])
        
        # With AWS_LOCATION
        if aws_location and not current_path.startswith(f"{aws_location}/"):
            possible_keys.append(f"{aws_location}/{current_path}")
            
            # Also try with the location but without media/
            if current_path.startswith('media/'):
                possible_keys.append(f"{aws_location}/{current_path[6:]}")
        
        logger.info(f"Checking these S3 keys: {possible_keys}")
        
        # Check if any of these keys exist in S3
        found_key = None
        
        # First try with s3_storage if available
        if s3_storage:
            for key in possible_keys:
                try:
                    if s3_storage.exists(key):
                        found_key = key
                        logger.info(f"Found file with key: {key} using storage.exists")
                        break
                except Exception as e:
                    logger.warning(f"Error checking if key exists with storage: {key} - {str(e)}")
        
        # If not found with storage, try with S3 client
        if not found_key:
            for key in possible_keys:
                try:
                    # Use head_object to check if file exists
                    s3_client.head_object(Bucket=aws_bucket, Key=key)
                    found_key = key
                    logger.info(f"Found file with key: {key} using head_object")
                    break
                except Exception as e:
                    # The file doesn't exist with this key
                    pass
        
        # If a file is found but the path is different, update the database
        if found_key and found_key != current_path:
            # Update the file path in the database
            logger.info(f"Updating path for file {datafile.id} from {current_path} to {found_key}")
            
            # Update the field directly in the database to avoid any side effects
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE datasilo_datafile SET file = %s WHERE id = %s",
                    [found_key, datafile.id]
                )
            
            # Log the update
            logger.info(f"Updated path for file {datafile.id}")
        elif not found_key:
            # If no file was found in S3, log this
            logger.warning(f"No file found in S3 for {datafile.id} - {datafile.name}")
            
            # Check if this was previously processed
            if datafile.vector_store_status != 'failed':
                logger.info(f"Marking file {datafile.id} as failed for vector store")
                datafile.vector_store_status = 'failed'
                datafile.save(update_fields=['vector_store_status'])
        else:
            logger.info(f"Path is already correct for file {datafile.id}")
    
    # Done
    logger.info("Finished fixing file paths")

if __name__ == "__main__":
    fix_file_paths() 