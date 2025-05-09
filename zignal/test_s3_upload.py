#!/usr/bin/env python
"""
Test script to verify S3 file uploads are working correctly.
Run this with: python manage.py shell < test_s3_upload.py
"""

import os
import uuid
import tempfile
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings

print("Testing S3 file uploads")
print(f"Storage class: {default_storage.__class__.__name__}")

if hasattr(default_storage, '_wrapped'):
    print(f"Wrapped storage class: {default_storage._wrapped.__class__.__name__}")

# Print S3 settings
print(f"AWS_STORAGE_BUCKET_NAME: {settings.AWS_STORAGE_BUCKET_NAME}")
print(f"AWS_S3_REGION_NAME: {settings.AWS_S3_REGION_NAME}")
print(f"AWS_LOCATION: {settings.AWS_LOCATION}")

# Generate test file path
test_id = str(uuid.uuid4())
test_path = f"test_uploads/{test_id}.txt"
print(f"Test file path: {test_path}")

# Create a test file
test_content = f"Test file content: {test_id}".encode('utf-8')

try:
    # Save the file using Django's storage
    print("Saving file using default_storage.save...")
    path = default_storage.save(test_path, ContentFile(test_content))
    print(f"File saved at: {path}")
    
    # Check if the file exists
    print("Checking if file exists...")
    exists = default_storage.exists(path)
    print(f"File exists: {exists}")
    
    # Get the file URL
    try:
        url = default_storage.url(path)
        print(f"File URL: {url}")
    except Exception as e:
        print(f"Error getting URL: {str(e)}")
    
    # Try to read the file
    print("Reading file content...")
    try:
        with default_storage.open(path, 'rb') as f:
            content = f.read()
        print(f"File content (bytes): {len(content)} bytes")
        print(f"File content matches: {content == test_content}")
    except Exception as e:
        print(f"Error reading file: {str(e)}")
    
    # If using S3, verify with boto3 directly
    if 'S3' in default_storage.__class__.__name__ or hasattr(default_storage, '_wrapped') and 'S3' in default_storage._wrapped.__class__.__name__:
        print("\nVerifying with boto3 directly...")
        import boto3
        from botocore.exceptions import ClientError
        
        s3 = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )
        
        # Check if the bucket exists
        try:
            s3.head_bucket(Bucket=settings.AWS_STORAGE_BUCKET_NAME)
            print(f"S3 bucket '{settings.AWS_STORAGE_BUCKET_NAME}' exists")
        except ClientError as e:
            print(f"Bucket check error: {e.response['Error']['Message']}")
        
        # Generate the S3 key
        key = path
        if settings.AWS_LOCATION and not key.startswith(f"{settings.AWS_LOCATION}/"):
            key = f"{settings.AWS_LOCATION}/{key}"
        
        print(f"S3 key to check: {key}")
        
        # Check if the object exists
        try:
            s3.head_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=key)
            print(f"Object exists at key: {key}")
        except ClientError as e:
            print(f"Object check error: {e.response['Error']['Message']}")
            
            # Try alternative key (without location prefix)
            if settings.AWS_LOCATION and key.startswith(f"{settings.AWS_LOCATION}/"):
                alt_key = key[len(f"{settings.AWS_LOCATION}/"):]
                print(f"Trying alternative key: {alt_key}")
                try:
                    s3.head_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=alt_key)
                    print(f"Object exists at alternative key: {alt_key}")
                except ClientError:
                    print(f"Object not found at alternative key either")
    
    # Delete the test file
    print("\nDeleting test file...")
    default_storage.delete(path)
    exists_after_delete = default_storage.exists(path)
    print(f"File exists after delete: {exists_after_delete}")
    
except Exception as e:
    print(f"Error during test: {str(e)}")

print("\nTest completed") 