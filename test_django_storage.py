#!/usr/bin/env python
"""
Test script to verify Django's storage configuration
"""
import os
import django
import sys

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zignal.config.settings')
django.setup()

# Import Django settings and storage
from django.conf import settings
from django.core.files.storage import default_storage

def test_django_storage():
    """Test Django storage configuration"""
    print("Django storage configuration test")
    print("=" * 40)
    
    # Check DEBUG setting
    print(f"DEBUG: {settings.DEBUG}")
    
    # Check USE_S3 setting
    use_s3 = getattr(settings, 'USE_S3', os.environ.get('USE_S3', '') == 'TRUE')
    print(f"USE_S3: {use_s3}")
    
    # Check storage backend
    storage_class = default_storage.__class__.__name__
    storage_module = default_storage.__class__.__module__
    print(f"Storage backend: {storage_module}.{storage_class}")
    
    # Check if using S3
    using_s3 = 'S3' in storage_class or 'Boto' in storage_class
    print(f"Using S3 storage: {using_s3}")
    
    # Check AWS settings if using S3
    if using_s3:
        print("\nAWS settings:")
        print(f"  AWS_ACCESS_KEY_ID: {settings.AWS_ACCESS_KEY_ID[:4]}...{settings.AWS_ACCESS_KEY_ID[-4:]}")
        print(f"  AWS_SECRET_ACCESS_KEY: {'*' * 20}")
        print(f"  AWS_STORAGE_BUCKET_NAME: {settings.AWS_STORAGE_BUCKET_NAME}")
        print(f"  AWS_S3_REGION_NAME: {settings.AWS_S3_REGION_NAME}")
        print(f"  AWS_LOCATION: {settings.AWS_LOCATION}")
        print(f"  MEDIA_URL: {settings.MEDIA_URL}")
    
    # Try creating a test file
    print("\nTesting file upload:")
    from django.core.files.base import ContentFile
    
    test_content = b"This is a test file created by Django storage test"
    path = default_storage.save('test_django_storage.txt', ContentFile(test_content))
    
    print(f"  File saved at: {path}")
    
    # Verify file exists
    file_exists = default_storage.exists(path)
    print(f"  File exists: {file_exists}")
    
    # Get file URL
    try:
        file_url = default_storage.url(path)
        print(f"  File URL: {file_url}")
    except Exception as e:
        print(f"  Error getting URL: {str(e)}")
    
    # Try to read file
    try:
        with default_storage.open(path, 'rb') as f:
            content = f.read()
            content_matches = content == test_content
            print(f"  Content matches: {content_matches}")
    except Exception as e:
        print(f"  Error reading file: {str(e)}")
    
    # Delete test file
    try:
        default_storage.delete(path)
        print(f"  File deleted successfully")
        
        # Verify deletion
        file_exists_after_delete = default_storage.exists(path)
        print(f"  File exists after delete: {file_exists_after_delete}")
    except Exception as e:
        print(f"  Error deleting file: {str(e)}")
    
    print("\nStorage test completed")

if __name__ == "__main__":
    test_django_storage() 