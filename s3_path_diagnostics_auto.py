#!/usr/bin/env python
"""
Perform comprehensive S3 path diagnostics to diagnose file storage issues
Automatic version - no user input required
"""
import os
import uuid
import logging
import django
import boto3
import time
from pathlib import Path

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zignal.config.settings')
django.setup()

from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from storages.backends.s3boto3 import S3Boto3Storage

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# AWS credentials from environment
aws_access_key_id = os.environ.get('AWS_ACCESS_KEY_ID')
aws_secret_access_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
aws_storage_bucket_name = os.environ.get('AWS_STORAGE_BUCKET_NAME', 'zignalse')
aws_s3_region_name = os.environ.get('AWS_S3_REGION_NAME', 'eu-west-1')
aws_location = os.environ.get('AWS_LOCATION', 'media')

# Create S3 client
s3 = boto3.client(
    's3',
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key,
    region_name=aws_s3_region_name
)

# Test ID to make files unique
test_id = uuid.uuid4().hex[:8]

def get_all_files_in_bucket():
    """List all files in the bucket"""
    logger.info(f"Listing all files in {aws_storage_bucket_name}:")
    
    paginator = s3.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=aws_storage_bucket_name)
    
    files = []
    for page in pages:
        if 'Contents' in page:
            for obj in page['Contents']:
                files.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified']
                })
    
    if files:
        logger.info(f"Found {len(files)} files in bucket")
        for i, f in enumerate(files[:20]):  # Show first 20 files
            logger.info(f"  {i+1}. {f['key']} ({f['size']} bytes)")
        if len(files) > 20:
            logger.info(f"  ... and {len(files) - 20} more files")
    else:
        logger.info("No files found in bucket")
    
    return files

def delete_test_files(test_files):
    """Delete test files we created"""
    if not test_files:
        return
    
    logger.info(f"Deleting {len(test_files)} test files...")
    
    for key in test_files:
        try:
            s3.delete_object(Bucket=aws_storage_bucket_name, Key=key)
            logger.info(f"  Deleted: {key}")
        except Exception as e:
            logger.error(f"  Error deleting {key}: {str(e)}")

def examine_settings():
    """Examine Django settings related to S3"""
    logger.info("\n=== DJANGO SETTINGS EXAMINATION ===")
    logger.info(f"DEBUG: {settings.DEBUG}")
    logger.info(f"USE_S3: {settings.USE_S3}")
    logger.info(f"DEFAULT_FILE_STORAGE: {settings.DEFAULT_FILE_STORAGE}")
    logger.info(f"AWS_STORAGE_BUCKET_NAME: {settings.AWS_STORAGE_BUCKET_NAME}")
    logger.info(f"AWS_S3_REGION_NAME: {settings.AWS_S3_REGION_NAME}")
    logger.info(f"AWS_LOCATION: {settings.AWS_LOCATION}")
    logger.info(f"MEDIA_URL: {settings.MEDIA_URL}")
    
    # Check how StorageClass is initialized
    storage_class = default_storage.__class__
    logger.info(f"Storage class: {storage_class.__name__}")
    
    if hasattr(default_storage, 'location'):
        logger.info(f"Storage location: {default_storage.location}")
    
    # Check if Django is prepending location
    test_path = "test_examine_path.txt"
    if hasattr(default_storage, 'get_modified_name'):
        try:
            modified_name = default_storage.get_modified_name(test_path)
            logger.info(f"Modified name method found. Test path '{test_path}' becomes '{modified_name}'")
        except Exception as e:
            logger.error(f"Error calling get_modified_name: {str(e)}")
    
    if hasattr(default_storage, '_normalize_name'):
        try:
            normalized_name = default_storage._normalize_name(test_path)
            logger.info(f"Normalized name method found. Test path '{test_path}' becomes '{normalized_name}'")
        except Exception as e:
            logger.error(f"Error calling _normalize_name: {str(e)}")

def test_upload_methods():
    """Test different upload methods to see where files are stored"""
    test_files = []
    
    # Create test content
    test_content = f"S3 path test file {test_id} - created at {time.strftime('%Y-%m-%d %H:%M:%S')}".encode()
    
    try:
        logger.info("\n=== TEST 1: Default Django Storage ===")
        # Test 1: Default Django storage
        path1 = f"test_file_{test_id}_1.txt"
        file1_path = default_storage.save(path1, ContentFile(test_content))
        file1_url = default_storage.url(file1_path)
        test_files.append(file1_path)
        logger.info(f"1. Path requested: {path1}")
        logger.info(f"   Path returned: {file1_path}")
        logger.info(f"   URL returned: {file1_url}")
        
        logger.info("\n=== TEST 2: Django Storage with datasilo path ===")
        # Test 2: With datasilo path
        path2 = f"datasilo/company/test/test_file_{test_id}_2.txt"
        file2_path = default_storage.save(path2, ContentFile(test_content))
        file2_url = default_storage.url(file2_path)
        test_files.append(file2_path)
        logger.info(f"2. Path requested: {path2}")
        logger.info(f"   Path returned: {file2_path}")
        logger.info(f"   URL returned: {file2_url}")
        
        logger.info("\n=== TEST 3: Direct S3 Storage ===")
        # Test 3: Direct S3 storage
        s3_storage = S3Boto3Storage(
            access_key=aws_access_key_id,
            secret_key=aws_secret_access_key,
            bucket_name=aws_storage_bucket_name,
            region_name=aws_s3_region_name,
            location=aws_location,  # Use media prefix
        )
        path3 = f"test_file_{test_id}_3.txt"
        file3_path = s3_storage.save(path3, ContentFile(test_content))
        file3_url = s3_storage.url(file3_path)
        test_files.append(file3_path)
        logger.info(f"3. Path requested: {path3}")
        logger.info(f"   Path returned: {file3_path}")
        logger.info(f"   URL returned: {file3_url}")
        
        logger.info("\n=== TEST 4: Direct S3 Storage with full path ===")
        # Test 4: With full path including location
        full_path = f"{aws_location}/test_file_{test_id}_4.txt"
        s3.put_object(
            Bucket=aws_storage_bucket_name,
            Key=full_path,
            Body=test_content
        )
        test_files.append(full_path)
        url = f"https://{aws_storage_bucket_name}.s3.{aws_s3_region_name}.amazonaws.com/{full_path}"
        logger.info(f"4. Path requested: {full_path}")
        logger.info(f"   Path used: {full_path}")
        logger.info(f"   URL constructed: {url}")
    
    except Exception as e:
        logger.error(f"Error in upload tests: {str(e)}")
    
    # Wait a moment for files to be available
    time.sleep(2)
    
    try:
        # Get all files from bucket
        all_files = get_all_files_in_bucket()
        
        # Find our test files
        logger.info("\n=== SEARCHING FOR TEST FILES ===")
        for f in all_files:
            if test_id in f['key']:
                logger.info(f"Found test file: {f['key']}")
    except Exception as e:
        logger.error(f"Error listing bucket contents: {str(e)}")
    
    # Auto-clean test files (no user input needed)
    logger.info("\n=== AUTO-CLEANING TEST FILES ===")
    delete_test_files(test_files)
    
    return test_files

def main():
    """Main diagnostic function"""
    logger.info("=== S3 PATH DIAGNOSTICS ===")
    logger.info(f"Bucket: {aws_storage_bucket_name}")
    logger.info(f"Region: {aws_s3_region_name}")
    logger.info(f"Location: {aws_location}")
    
    # Check settings first
    examine_settings()
    
    # Run upload tests
    test_upload_methods()

if __name__ == "__main__":
    main() 