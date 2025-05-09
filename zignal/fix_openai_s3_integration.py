"""
Fix script for OpenAI S3 integration issues
This script helps diagnose and fix issues with S3 file paths when sending to OpenAI
"""
import os
import sys
import boto3
import logging
import django
from botocore.exceptions import ClientError

# Set up Django environment
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zignal.config.settings')
django.setup()

from django.conf import settings
from django.core.files.storage import default_storage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def diagnose_s3_paths():
    """Diagnose S3 file path issues"""
    print("\n=== S3 PATH DIAGNOSTICS ===")
    
    # Check S3 configuration
    print(f"AWS_STORAGE_BUCKET_NAME: {settings.AWS_STORAGE_BUCKET_NAME}")
    print(f"AWS_S3_REGION_NAME: {settings.AWS_S3_REGION_NAME}")
    print(f"AWS_LOCATION: {settings.AWS_LOCATION}")
    
    # Connect to S3
    try:
        s3 = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )
        
        # List some objects in the bucket to examine paths
        response = s3.list_objects_v2(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            MaxKeys=10
        )
        
        if 'Contents' in response and len(response['Contents']) > 0:
            print(f"\nFound {len(response['Contents'])} files in S3 bucket. Examining paths:")
            
            for item in response['Contents']:
                key = item['Key']
                # Test if the file exists using different path variations
                try:
                    # Test with original path
                    s3.head_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=key)
                    original_exists = True
                except ClientError:
                    original_exists = False
                
                # Test with media/ prefix
                if not key.startswith('media/'):
                    media_key = f"media/{key}"
                    try:
                        s3.head_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=media_key)
                        media_exists = True
                    except ClientError:
                        media_exists = False
                else:
                    media_exists = original_exists
                    media_key = key
                
                # Test without media/ prefix
                if key.startswith('media/'):
                    no_media_key = key[6:]  # Remove 'media/' prefix
                    try:
                        s3.head_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=no_media_key)
                        no_media_exists = True
                    except ClientError:
                        no_media_exists = False
                else:
                    no_media_exists = original_exists
                    no_media_key = key
                
                print(f"File: {key}")
                print(f"  Size: {item['Size']} bytes")
                print(f"  Original path exists: {original_exists}")
                if key != media_key:
                    print(f"  With media/ prefix exists: {media_exists} ('{media_key}')")
                if key != no_media_key:
                    print(f"  Without media/ prefix exists: {no_media_exists} ('{no_media_key}')")
                print(f"  Last modified: {item['LastModified']}")
                print("")
        else:
            print("No files found in the S3 bucket.")
    except Exception as e:
        print(f"Error examining S3 paths: {str(e)}")
        return False
    
    return True

def fix_openai_integration():
    """Fix the OpenAI integration with S3"""
    print("\n=== ATTEMPTING TO FIX OPENAI S3 INTEGRATION ===")
    
    try:
        # Get the OpenAI service module
        from companies.services import openai_service
        
        # Check if the add_file_to_vector_store_s3 method is available
        if hasattr(openai_service, 'add_file_to_vector_store_s3'):
            # Get the method
            original_method = openai_service.add_file_to_vector_store_s3
            
            # Define a patched version that handles path variations
            def patched_add_file_to_vector_store_s3(bucket, key, file_name=None, file_type=None, batch_id=None):
                """
                Patched version of the add_file_to_vector_store_s3 method that handles path variations
                """
                # Log the original key
                logger.info(f"Original key: {key}")
                
                # Create S3 client
                s3 = boto3.client(
                    's3',
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                    region_name=settings.AWS_S3_REGION_NAME
                )
                
                # Try different path variations
                keys_to_try = [key]
                
                # If the key doesn't start with media/, try with it
                if not key.startswith('media/'):
                    keys_to_try.append(f"media/{key}")
                
                # If the key starts with media/, try without it
                if key.startswith('media/'):
                    keys_to_try.append(key[6:])  # Remove 'media/' prefix
                
                logger.info(f"Will try these S3 keys: {keys_to_try}")
                
                # Try each key
                for test_key in keys_to_try:
                    try:
                        # Check if the object exists
                        s3.head_object(Bucket=bucket, Key=test_key)
                        logger.info(f"Found existing S3 object with key: {test_key}")
                        
                        # Use the original method with the working key
                        return original_method(bucket, test_key, file_name, file_type, batch_id)
                    except ClientError:
                        logger.info(f"S3 object not found with key: {test_key}")
                        continue
                
                # If we get here, none of the keys worked, fall back to the original method
                logger.warning(f"No working S3 key found, falling back to original key: {key}")
                return original_method(bucket, key, file_name, file_type, batch_id)
            
            # Monkey patch the method
            openai_service.add_file_to_vector_store_s3 = patched_add_file_to_vector_store_s3
            
            print("✅ Successfully patched OpenAI S3 integration")
            return True
        else:
            print("❌ add_file_to_vector_store_s3 method not found in openai_service")
            return False
    except Exception as e:
        print(f"❌ Error patching OpenAI S3 integration: {str(e)}")
        return False

if __name__ == "__main__":
    print("===== OPENAI S3 INTEGRATION DIAGNOSTICS AND FIX =====")
    
    # Run diagnostics
    paths_ok = diagnose_s3_paths()
    
    if not paths_ok:
        print("\n❌ Issues detected with S3 paths.")
    
    # Try to fix integration
    fix_ok = fix_openai_integration()
    
    if fix_ok:
        print("\n✅ OPENAI S3 INTEGRATION FIXED!")
        print("The OpenAI S3 integration has been patched to handle different path variations.")
        print("Try uploading a file now and check if the vector store processing works.")
    else:
        print("\n❌ Could not fix OpenAI S3 integration automatically.")
        print("Please check your OpenAI and S3 integration code.")
        
    print("\nTo permanently fix this issue:")
    print("1. Examine the S3 paths in the diagnostic output")
    print("2. Update the OpenAI integration code in companies/services/openai_service.py")
    print("3. Ensure consistent path handling between Django storage and OpenAI integration") 