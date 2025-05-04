#!/usr/bin/env python
"""
Script to directly fix S3 file paths in production using direct database access.
Run this on Heroku with: heroku run python fix_s3_storage_production.py
"""
import os
import django
import sys
import logging
import time
import boto3
import psycopg2
import dj_database_url

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zignal.config.settings')
django.setup()

# Now we can import Django-specific modules
from django.core.files.storage import default_storage
from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage

def fix_s3_storage():
    """Main function to fix S3 storage configuration and file paths"""
    logger.info("==== S3 Storage Direct DB Fixer ====")
    
    # Force S3 to be used
    os.environ['USE_S3'] = 'TRUE'
    
    # Get AWS settings
    aws_access_key = os.environ.get('AWS_ACCESS_KEY_ID', '')
    aws_secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY', '')
    aws_bucket = os.environ.get('AWS_STORAGE_BUCKET_NAME', '')
    aws_location = os.environ.get('AWS_LOCATION', 'media')
    aws_region = os.environ.get('AWS_S3_REGION_NAME', 'eu-west-1')
    
    logger.info(f"S3 Settings: Bucket={aws_bucket}, Region={aws_region}, Location={aws_location}")
    
    # Check the default storage
    logger.info(f"Current default_storage: {default_storage.__class__.__name__}")
    if hasattr(default_storage, '_wrapped'):
        logger.info(f"Wrapped storage: {default_storage._wrapped.__class__.__name__}")
    
    # Fix storage configuration
    if hasattr(settings, 'MEDIA_STORAGE_CLASS'):
        logger.info("Found MEDIA_STORAGE_CLASS in settings")
        storage_class = settings.MEDIA_STORAGE_CLASS
        s3_storage = storage_class()
        
        # Replace default_storage._wrapped with our S3 storage
        if hasattr(default_storage, '_wrapped'):
            default_storage._wrapped = s3_storage
            logger.info(f"Replaced default_storage with {s3_storage.__class__.__name__}")
    
    # Fix file paths through direct database access
    fix_file_paths_direct(aws_bucket, aws_location, aws_access_key, aws_secret_key, aws_region)
    
    # Test S3 storage
    test_s3_storage()

def fix_file_paths_direct(aws_bucket, aws_location, aws_access_key, aws_secret_key, aws_region):
    """Fix file paths directly using database connection and S3 client"""
    logger.info("Fixing file paths using direct database access...")
    
    # Create S3 client
    s3_client = boto3.client(
        's3',
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key,
        region_name=aws_region
    )
    
    # Get database connection from environment
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        logger.error("DATABASE_URL environment variable not set")
        return
    
    # Parse the database URL to get connection parameters
    db_config = dj_database_url.parse(database_url)
    
    # Connect to the database
    try:
        conn = psycopg2.connect(
            dbname=db_config['NAME'],
            user=db_config['USER'],
            password=db_config['PASSWORD'],
            host=db_config['HOST'],
            port=db_config['PORT']
        )
        conn.autocommit = True
        
        # Create a cursor
        cursor = conn.cursor()
        
        # First, query for failed files
        logger.info("Looking for files with vector_store_status='failed'...")
        cursor.execute("SELECT id, file, name FROM datasilo_datafile WHERE vector_store_status = 'failed'")
        failed_files = cursor.fetchall()
        logger.info(f"Found {len(failed_files)} failed files")
        
        # Process failed files
        for file_id, file_path, file_name in failed_files:
            logger.info(f"Processing failed file {file_id}: {file_name}")
            fixed_path = check_file_paths(s3_client, aws_bucket, aws_location, file_path, file_id)
            
            if fixed_path and fixed_path != file_path:
                # Update the path in the database
                logger.info(f"Updating file {file_id} path from '{file_path}' to '{fixed_path}'")
                cursor.execute(
                    "UPDATE datasilo_datafile SET file = %s, vector_store_status = 'pending' WHERE id = %s", 
                    (fixed_path, file_id)
                )
                logger.info(f"Updated path and reset status for file {file_id}")
        
        # Query for all files to check paths
        logger.info("Checking paths for all files...")
        cursor.execute("SELECT id, file, name FROM datasilo_datafile WHERE id NOT IN (SELECT id FROM datasilo_datafile WHERE vector_store_status = 'failed')")
        all_files = cursor.fetchall()
        logger.info(f"Found {len(all_files)} additional files to check")
        
        # Process files in batches with progress updates
        batch_size = 10
        for i in range(0, len(all_files), batch_size):
            batch = all_files[i:i+batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}/{(len(all_files) + batch_size - 1)//batch_size}")
            
            for file_id, file_path, file_name in batch:
                fixed_path = check_file_paths(s3_client, aws_bucket, aws_location, file_path, file_id)
                
                if fixed_path and fixed_path != file_path:
                    # Update the path in the database
                    logger.info(f"Updating file {file_id} path from '{file_path}' to '{fixed_path}'")
                    cursor.execute(
                        "UPDATE datasilo_datafile SET file = %s WHERE id = %s", 
                        (fixed_path, file_id)
                    )
        
        cursor.close()
        conn.close()
        logger.info("Database operations completed")
        
    except Exception as e:
        logger.error(f"Database error: {str(e)}")

def check_file_paths(s3_client, aws_bucket, aws_location, file_path, file_id):
    """Check if a file exists in S3 with various possible paths"""
    if not file_path:
        return None
    
    # Generate possible S3 keys to try
    possible_keys = []
    
    # Original key
    possible_keys.append(file_path)
    
    # With media/ prefix if not already there
    if not file_path.startswith('media/'):
        possible_keys.append(f"media/{file_path}")
    
    # Without media/ prefix if it's there
    if file_path.startswith('media/'):
        possible_keys.append(file_path[6:])
    
    # With AWS_LOCATION prefix
    if aws_location and not file_path.startswith(f"{aws_location}/"):
        possible_keys.append(f"{aws_location}/{file_path}")
        
        # Also with location but without media/ if it has that
        if file_path.startswith('media/'):
            possible_keys.append(f"{aws_location}/{file_path[6:]}")
    
    # Remove duplicates but preserve order
    possible_keys = list(dict.fromkeys(possible_keys))
    
    # Try each key to see if the file exists
    for key in possible_keys:
        try:
            s3_client.head_object(Bucket=aws_bucket, Key=key)
            # If we found the file with this key, return it
            return key
        except Exception:
            pass
    
    # If no match found, try listing objects to find closest match
    try:
        # Get the filename from the path
        filename = os.path.basename(file_path)
        
        # Get directory part
        dir_parts = file_path.split('/')
        if len(dir_parts) > 1:
            directory = '/'.join(dir_parts[:-1]) + '/'
        else:
            directory = ''
        
        # Try different prefixes
        search_prefixes = [
            directory,
            f"media/{directory}",
            f"{aws_location}/{directory}",
            "datasilo/"
        ]
        
        for prefix in search_prefixes:
            response = s3_client.list_objects_v2(
                Bucket=aws_bucket,
                Prefix=prefix,
                MaxKeys=100
            )
            
            if 'Contents' in response:
                for obj in response['Contents']:
                    # Check if this object's key contains our filename
                    if filename in obj['Key']:
                        logger.info(f"Found potential match for file {file_id}: {obj['Key']}")
                        return obj['Key']
    
    except Exception as e:
        logger.error(f"Error searching for file {file_id}: {str(e)}")
    
    return None

def test_s3_storage():
    """Test if S3 storage is working by creating and deleting a test file"""
    logger.info("Testing S3 storage configuration...")
    
    test_file = f"test_s3_fix_{int(time.time())}.txt"
    test_content = f"Test content created at {time.time()}"
    
    try:
        # Save file to storage
        path = default_storage.save(test_file, test_content.encode('utf-8'))
        logger.info(f"Test file saved at: {path}")
        
        # Get file URL
        url = default_storage.url(path)
        logger.info(f"File URL: {url}")
        
        # Check if file exists
        exists = default_storage.exists(path)
        logger.info(f"File exists: {exists}")
        
        if exists:
            # Delete the test file
            default_storage.delete(path)
            logger.info("Test file deleted")
            return True
        else:
            logger.error("Test file doesn't exist after saving")
            return False
    except Exception as e:
        logger.error(f"Error testing S3 storage: {str(e)}")
        return False

if __name__ == "__main__":
    try:
        fix_s3_storage()
        logger.info("S3 storage fix completed successfully")
    except Exception as e:
        logger.error(f"Error during S3 storage fix: {str(e)}")
        import traceback
        logger.error(traceback.format_exc()) 