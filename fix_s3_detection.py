#!/usr/bin/env python
"""
Diagnose and fix S3 storage detection issues
"""
import os
import django
import sys
from django.conf import settings

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zignal.config.settings')
django.setup()

from django.core.files.storage import default_storage
import boto3
from storages.backends.s3boto3 import S3Boto3Storage

print("Django S3 Storage Diagnostic")
print("=" * 50)

# Check Django settings
print("Django Settings:")
print(f"DEBUG: {settings.DEBUG}")
print(f"USE_S3: {os.environ.get('USE_S3', 'Not set')}")
print(f"DEFAULT_FILE_STORAGE: {getattr(settings, 'DEFAULT_FILE_STORAGE', 'Not set')}")

# Check actual storage class
print("\nStorage Class Info:")
print(f"default_storage class: {default_storage.__class__.__name__}")
print(f"storage module: {default_storage.__class__.__module__}")

# Check if S3 is detected correctly
s3_class = 'S3' in default_storage.__class__.__name__ or 'Boto' in default_storage.__class__.__name__
s3_module = 'boto' in default_storage.__class__.__module__ or 's3' in default_storage.__class__.__module__.lower()
print(f"S3 detected by class name: {s3_class}")
print(f"S3 detected by module name: {s3_module}")

# Check S3 settings
if hasattr(settings, 'AWS_STORAGE_BUCKET_NAME'):
    print("\nAWS Settings:")
    print(f"AWS_STORAGE_BUCKET_NAME: {settings.AWS_STORAGE_BUCKET_NAME}")
    print(f"AWS_S3_REGION_NAME: {settings.AWS_S3_REGION_NAME}")
    print(f"AWS_LOCATION: {settings.AWS_LOCATION}")

# Test file operations
print("\nTesting file operations:")
try:
    from django.core.files.base import ContentFile
    test_path = default_storage.save('test.txt', ContentFile(b'test content'))
    print(f"File saved at: {test_path}")
    
    # Get URL
    file_url = default_storage.url(test_path)
    print(f"File URL: {file_url}")
    
    # Check if URL is an S3 URL
    is_s3_url = 's3.amazonaws.com' in file_url or settings.AWS_STORAGE_BUCKET_NAME in file_url
    print(f"URL appears to be S3: {is_s3_url}")
    
    # Delete test file
    default_storage.delete(test_path)
    print("Test file deleted")
except Exception as e:
    print(f"Error in file operations: {str(e)}")

# Recommendation
print("\nDiagnosis:")
if is_s3_url and not s3_class:
    print("Your Django application is correctly saving files to S3,")
    print("but there's a detection issue in your code that's causing it to misidentify the storage backend.")
    print("The fix is to modify how you detect S3 storage in your code.")
    
    print("\nRecommended fix:")
    print("In core/tasks.py and other files, replace the S3 detection code with:")
    print("    # The best way to detect S3 storage")
    print("    using_s3 = True  # Hardcode for production environment")
    print("    try:")
    print("        # Alternative detection method")
    print("        file_url = default_storage.url('test-path')")
    print("        using_s3 = 's3.amazonaws.com' in file_url or settings.AWS_STORAGE_BUCKET_NAME in file_url")
    print("    except Exception:")
    print("        # Fallback to class name detection if URL method fails")
    print("        storage_type = default_storage.__class__.__name__")
    print("        using_s3 = 'S3' in storage_type or 'Boto' in storage_type") 