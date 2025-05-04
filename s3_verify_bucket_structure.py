#!/usr/bin/env python
"""
Verify S3 bucket structure and upload a test file to confirm correct path construction
"""
import os
import boto3
import sys
import uuid
import logging
import django
from pathlib import Path

# Set up Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zignal.config.settings')
django.setup()

from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# AWS credentials from environment
aws_access_key_id = os.environ.get('AWS_ACCESS_KEY_ID')
aws_secret_access_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
aws_storage_bucket_name = os.environ.get('AWS_STORAGE_BUCKET_NAME', 'zignalse')
aws_s3_region_name = os.environ.get('AWS_S3_REGION_NAME', 'eu-west-1')
aws_location = os.environ.get('AWS_LOCATION', 'media')

logger.info(f"S3 Configuration:")
logger.info(f"  Bucket: {aws_storage_bucket_name}")
logger.info(f"  Region: {aws_s3_region_name}")
logger.info(f"  Location prefix: {aws_location}")
logger.info(f"  Access Key: {aws_access_key_id[:4]}...{aws_access_key_id[-4:]}")
logger.info(f"  Using S3: {settings.USE_S3}")
logger.info(f"  Default File Storage: {settings.DEFAULT_FILE_STORAGE}")

try:
    # Test if we can create an S3 client
    s3 = boto3.client(
        's3',
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=aws_s3_region_name
    )
    
    # Check if bucket exists
    s3.head_bucket(Bucket=aws_storage_bucket_name)
    logger.info(f"✅ Successfully connected to S3 bucket: {aws_storage_bucket_name}")
    
    # List objects in bucket
    response = s3.list_objects_v2(Bucket=aws_storage_bucket_name)
    
    if 'Contents' in response:
        count = len(response['Contents'])
        logger.info(f"Found {count} objects in bucket")
        
        # Show first 10 objects
        for i, obj in enumerate(response['Contents'][:10]):
            logger.info(f"  {i+1}. {obj['Key']} ({obj['Size']} bytes)")
    else:
        logger.info("Bucket is empty")
    
    # Try uploading a test file using Django's storage backend
    logger.info("\nTest file upload with Django storage:")
    
    test_content = b"This is a test file to verify S3 upload paths"
    path_1 = f"test_files/django_test_{uuid.uuid4()}.txt"
    path_2 = f"datasilo/company/test/django_test_{uuid.uuid4()}.txt"
    
    # Upload using Django's storage backend
    logger.info(f"Uploading test file to: {path_1}")
    file_1_path = default_storage.save(path_1, ContentFile(test_content))
    file_1_url = default_storage.url(file_1_path)
    
    logger.info(f"Uploading second test file to: {path_2}")
    file_2_path = default_storage.save(path_2, ContentFile(test_content))
    file_2_url = default_storage.url(file_2_path)
    
    logger.info(f"File 1 Saved path: {file_1_path}")
    logger.info(f"File 1 URL: {file_1_url}")
    logger.info(f"File 2 Saved path: {file_2_path}")
    logger.info(f"File 2 URL: {file_2_url}")
    
    # Verify the files exist in S3
    logger.info("\nVerifying files in S3 (actual paths):")
    
    # Try multiple path combinations
    paths_to_check = [
        file_1_path,
        f"{aws_location}/{file_1_path}",
        file_2_path,
        f"{aws_location}/{file_2_path}"
    ]
    
    for path in paths_to_check:
        try:
            s3.head_object(Bucket=aws_storage_bucket_name, Key=path)
            logger.info(f"✅ File exists at: {path}")
        except Exception:
            logger.info(f"❌ File NOT found at: {path}")
    
except Exception as e:
    logger.error(f"Error: {str(e)}")
    sys.exit(1) 