"""
Test script to verify S3 configuration and connection.
This helps diagnose issues with S3 storage in Django.
"""
import os
import sys
import boto3
from botocore.exceptions import ClientError
import django
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

# Set up Django environment
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zignal.config.settings')
django.setup()

def test_s3_credentials():
    """Test S3 credentials and bucket access"""
    print("\n=== S3 CREDENTIALS TEST ===")
    print(f"AWS_ACCESS_KEY_ID: {'*' * 6 + settings.AWS_ACCESS_KEY_ID[-4:] if settings.AWS_ACCESS_KEY_ID else 'Not set'}")
    print(f"AWS_SECRET_ACCESS_KEY: {'*' * 6 + '****' if settings.AWS_SECRET_ACCESS_KEY else 'Not set'}")
    print(f"AWS_STORAGE_BUCKET_NAME: {settings.AWS_STORAGE_BUCKET_NAME}")
    print(f"AWS_S3_REGION_NAME: {settings.AWS_S3_REGION_NAME}")
    print(f"AWS_LOCATION: {settings.AWS_LOCATION}")
    
    if not settings.AWS_ACCESS_KEY_ID or not settings.AWS_SECRET_ACCESS_KEY:
        print("❌ AWS credentials not properly set in environment")
        return False

    try:
        # Create S3 client
        s3 = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )
        
        # Check if we can list buckets (verifies credentials)
        response = s3.list_buckets()
        print(f"✅ Successfully connected to S3. Found {len(response['Buckets'])} buckets")
        
        # Check if specified bucket exists
        if settings.AWS_STORAGE_BUCKET_NAME:
            try:
                s3.head_bucket(Bucket=settings.AWS_STORAGE_BUCKET_NAME)
                print(f"✅ Bucket '{settings.AWS_STORAGE_BUCKET_NAME}' exists and is accessible")
                
                # Try to list objects in the bucket
                response = s3.list_objects_v2(
                    Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                    MaxKeys=5
                )
                object_count = response.get('KeyCount', 0)
                print(f"Found {object_count} objects in bucket")
                if object_count > 0:
                    for obj in response.get('Contents', []):
                        print(f"  - {obj['Key']} ({obj['Size']} bytes)")
                
                return True
            except ClientError as e:
                print(f"❌ Error accessing bucket: {e}")
                return False
        else:
            print("❌ AWS_STORAGE_BUCKET_NAME not set")
            return False
    except Exception as e:
        print(f"❌ Error connecting to S3: {str(e)}")
        return False

def test_django_storage():
    """Test Django's default_storage configuration"""
    print("\n=== DJANGO STORAGE TEST ===")
    
    # Check storage class
    storage_class = default_storage.__class__.__name__
    print(f"Default storage class: {storage_class}")
    print(f"Storage is S3-based: {'Yes' if 'S3' in storage_class or 'Boto' in storage_class else 'No'}")
    
    if 'S3' not in storage_class and 'Boto' not in storage_class:
        print("❌ Django storage is not using S3")
        return False
    
    # Test file upload
    try:
        test_path = f"test/{os.urandom(4).hex()}.txt"
        test_content = f"Test content created at {django.utils.timezone.now()}"
        
        print(f"Uploading test file to: {test_path}")
        path = default_storage.save(test_path, ContentFile(test_content.encode()))
        
        # Verify the file exists
        exists = default_storage.exists(path)
        print(f"File exists check: {'✅ Yes' if exists else '❌ No'}")
        
        if exists:
            # Get file URL
            url = default_storage.url(path)
            print(f"File URL: {url}")
            
            # Clean up
            default_storage.delete(path)
            print("Test file deleted")
            return True
        return False
    except Exception as e:
        print(f"❌ Error testing Django storage: {str(e)}")
        return False

def fix_s3_storage():
    """Attempt to fix S3 storage configuration"""
    print("\n=== ATTEMPTING TO FIX STORAGE ===")
    
    try:
        # Create direct S3Boto3Storage instance
        from storages.backends.s3boto3 import S3Boto3Storage
        
        class FixedS3Storage(S3Boto3Storage):
            location = settings.AWS_LOCATION
            file_overwrite = settings.AWS_S3_FILE_OVERWRITE
            default_acl = settings.AWS_DEFAULT_ACL
        
        # Create instance
        fixed_storage = FixedS3Storage()
        
        # Force Django to use this storage
        from django.core.files.storage import default_storage
        default_storage._wrapped = fixed_storage
        
        print("✅ Storage fixed and replaced with direct S3Boto3Storage instance")
        print(f"New storage class: {default_storage.__class__.__name__}")
        
        # Test it
        return test_django_storage()
    except Exception as e:
        print(f"❌ Error fixing storage: {str(e)}")
        return False

if __name__ == "__main__":
    print("===== S3 CONFIGURATION TEST =====")
    
    # Run tests
    creds_ok = test_s3_credentials()
    storage_ok = test_django_storage()
    
    if not creds_ok or not storage_ok:
        print("\n❌ Issues detected with S3 configuration.")
        
        # Try to fix storage
        fix_ok = fix_s3_storage()
        
        if fix_ok:
            print("\n✅ S3 STORAGE FIXED SUCCESSFULLY!")
            print("You may need to make changes to settings.py to make this fix permanent.")
        else:
            print("\n❌ Could not fix S3 storage automatically.")
            print("Please check your AWS credentials and Django settings.")
    else:
        print("\n✅ S3 CONFIGURATION IS WORKING PROPERLY") 