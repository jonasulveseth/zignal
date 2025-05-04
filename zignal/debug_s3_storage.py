#!/usr/bin/env python
"""
Debug script to verify S3 storage configuration
"""
import os
import sys
import django
import boto3
import tempfile
import uuid
from datetime import datetime

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zignal.config.settings')
django.setup()

from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

print("=== S3 Storage Debug ===")
print(f"Django version: {django.get_version()}")
print(f"Default storage: {default_storage.__class__.__name__}")

if hasattr(default_storage, '_wrapped'):
    print(f"Wrapped storage: {default_storage._wrapped.__class__.__name__}")

# Get AWS settings
aws_access_key = settings.AWS_ACCESS_KEY_ID
aws_secret_key = settings.AWS_SECRET_ACCESS_KEY
aws_region = settings.AWS_S3_REGION_NAME
aws_bucket = settings.AWS_STORAGE_BUCKET_NAME
aws_location = settings.AWS_LOCATION

# Print settings
print("\n=== AWS Settings ===")
print(f"AWS_ACCESS_KEY_ID: {'Configured' if aws_access_key else 'Missing'}")
print(f"AWS_SECRET_ACCESS_KEY: {'Configured' if aws_secret_key else 'Missing'}")
print(f"AWS_S3_REGION_NAME: {aws_region}")
print(f"AWS_STORAGE_BUCKET_NAME: {aws_bucket}")
print(f"AWS_LOCATION: {aws_location}")

# Test boto3 connection
print("\n=== Testing boto3 connection ===")
try:
    s3 = boto3.client(
        's3',
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key,
        region_name=aws_region
    )
    buckets = s3.list_buckets()
    print(f"Successfully connected to S3. Found {len(buckets['Buckets'])} buckets:")
    for bucket in buckets['Buckets']:
        print(f"  - {bucket['Name']}")
        
    # Check if our bucket exists
    if aws_bucket:
        found = False
        for bucket in buckets['Buckets']:
            if bucket['Name'] == aws_bucket:
                found = True
                print(f"✅ Bucket '{aws_bucket}' found")
                break
        if not found:
            print(f"❌ Bucket '{aws_bucket}' not found in your account")
    
    # Test bucket access
    if aws_bucket:
        print(f"\nTesting access to bucket '{aws_bucket}'...")
        try:
            response = s3.list_objects_v2(
                Bucket=aws_bucket,
                MaxKeys=5
            )
            count = response.get('KeyCount', 0)
            print(f"Listed objects in bucket. Found {count} objects.")
            if count > 0:
                print("Sample objects:")
                for obj in response.get('Contents', []):
                    print(f"  - {obj['Key']} ({obj['Size']} bytes)")
        except Exception as e:
            print(f"Error listing objects: {str(e)}")
            
        # Test writing and reading a file
        print("\nTesting file operations...")
        test_key = f"test/s3_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.txt"
        test_content = f"S3 Storage Debug Test\nTimestamp: {datetime.now().isoformat()}\nRandom: {uuid.uuid4()}\n"
        
        try:
            # Using boto3 directly
            print(f"Writing test file to {test_key}...")
            with tempfile.NamedTemporaryFile(mode='w+b', delete=False) as temp:
                temp.write(test_content.encode('utf-8'))
                temp.flush()
                temp_path = temp.name
                
            s3.upload_file(temp_path, aws_bucket, test_key)
            os.unlink(temp_path)
            print("✅ File uploaded successfully with boto3")
            
            # Reading back
            with tempfile.NamedTemporaryFile(delete=False) as temp:
                temp_path = temp.name
            
            s3.download_file(aws_bucket, test_key, temp_path)
            with open(temp_path, 'r') as f:
                content = f.read()
            os.unlink(temp_path)
            
            print(f"✅ File read successfully with boto3: {len(content)} bytes")
            
            # Test Django storage
            print("\nTesting Django storage...")
            django_test_path = f"test/django_storage_test_{uuid.uuid4().hex[:8]}.txt"
            django_content = f"Django S3 Storage Test\nTimestamp: {datetime.now().isoformat()}\nRandom: {uuid.uuid4()}\n"
            
            # Write file
            storage_path = default_storage.save(django_test_path, ContentFile(django_content.encode('utf-8')))
            print(f"File saved to: {storage_path}")
            
            # Check if exists
            exists = default_storage.exists(storage_path)
            print(f"Storage reports file exists: {exists}")
            
            # Read back
            content = default_storage.open(storage_path).read().decode('utf-8')
            print(f"✅ File read successfully with Django storage: {len(content)} bytes")
            
            # Check paths
            print("\n=== Checking paths ===")
            for path_format in [
                django_test_path,
                f"media/{django_test_path}",
                django_test_path.replace('media/', '') if django_test_path.startswith('media/') else django_test_path,
                f"{aws_location}/{django_test_path}" if aws_location and not django_test_path.startswith(f"{aws_location}/") else django_test_path
            ]:
                print(f"Checking if path exists: {path_format}")
                try:
                    exists_django = default_storage.exists(path_format)
                    print(f"  - Django storage: {exists_django}")
                except Exception as e:
                    print(f"  - Django storage error: {str(e)}")
                
                try:
                    s3.head_object(Bucket=aws_bucket, Key=path_format)
                    print(f"  - S3 boto3: ✅")
                except Exception as e:
                    print(f"  - S3 boto3: ❌ ({str(e)})")
            
            # Clean up test files
            print("\nCleaning up test files...")
            try:
                s3.delete_object(Bucket=aws_bucket, Key=test_key)
                print(f"Deleted boto3 test file: {test_key}")
            except Exception as e:
                print(f"Error deleting boto3 test file: {str(e)}")
                
            try:
                default_storage.delete(storage_path)
                print(f"Deleted Django storage test file: {storage_path}")
            except Exception as e:
                print(f"Error deleting Django storage test file: {str(e)}")
                
        except Exception as e:
            print(f"Error during file operations: {str(e)}")
        
except Exception as e:
    print(f"Error connecting to S3: {str(e)}")

print("\n=== Debug Complete ===") 