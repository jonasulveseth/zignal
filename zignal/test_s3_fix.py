"""
Test script for verifying S3 file access after fixes
"""
import os
import sys
import boto3
import dotenv
from pathlib import Path
import tempfile

# Load environment variables from .env file
env_file = Path(__file__).resolve().parent.parent / '.env'
if env_file.exists():
    print(f"Loading environment from {env_file}")
    dotenv.load_dotenv(env_file)
else:
    print("No .env file found")

# Get AWS credentials from environment variables
aws_access_key = os.environ.get('AWS_ACCESS_KEY_ID')
aws_secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
aws_bucket = os.environ.get('AWS_STORAGE_BUCKET_NAME')
aws_region = os.environ.get('AWS_S3_REGION_NAME', 'eu-west-1')
aws_location = os.environ.get('AWS_LOCATION', 'media')

print("\n=== S3 CONFIGURATION ===")
print(f"AWS_STORAGE_BUCKET_NAME: {aws_bucket}")
print(f"AWS_S3_REGION_NAME: {aws_region}")
print(f"AWS_LOCATION: {aws_location}")

if not aws_access_key or not aws_secret_key or not aws_bucket:
    print("Missing AWS credentials or bucket name")
    exit(1)

# Connect to S3
s3 = boto3.client(
    's3',
    aws_access_key_id=aws_access_key,
    aws_secret_access_key=aws_secret_key,
    region_name=aws_region
)

# Function to test if a file exists at a given path
def test_s3_path(s3_key):
    try:
        s3.head_object(Bucket=aws_bucket, Key=s3_key)
        return True
    except Exception:
        return False

# Function to get the size of a file at a given path
def get_s3_file_size(s3_key):
    try:
        response = s3.head_object(Bucket=aws_bucket, Key=s3_key)
        return response.get('ContentLength', 0)
    except Exception:
        return 0

# Function to test downloading a file
def test_download(s3_key):
    try:
        tmp_file = tempfile.NamedTemporaryFile(delete=False)
        tmp_file.close()
        
        s3.download_file(aws_bucket, s3_key, tmp_file.name)
        file_size = os.path.getsize(tmp_file.name)
        os.unlink(tmp_file.name)
        
        return True, file_size
    except Exception as e:
        print(f"Error downloading {s3_key}: {str(e)}")
        if os.path.exists(tmp_file.name):
            os.unlink(tmp_file.name)
        return False, 0

print("\n=== LISTING RECENT FILES ===")
response = s3.list_objects_v2(
    Bucket=aws_bucket,
    MaxKeys=5
)

if 'Contents' in response and len(response['Contents']) > 0:
    # Test file access with different path variations
    print("\n=== TESTING FILE ACCESS WITH DIFFERENT PATH VARIATIONS ===")
    
    for item in response['Contents']:
        original_key = item['Key']
        file_size = item['Size']
        
        # Generate all path variations
        path_variations = [original_key]
        
        # If the key doesn't start with media/, try with it
        if not original_key.startswith('media/'):
            path_variations.append(f"media/{original_key}")
        
        # If the key starts with media/, try without it
        if original_key.startswith('media/'):
            path_variations.append(original_key[6:])  # Remove 'media/' prefix
        
        # Also try media/media/ prefix (double media)
        if not original_key.startswith('media/media/') and not original_key.startswith('media/'):
            path_variations.append(f"media/media/{original_key}")
        
        # Test all path variations
        print(f"\nOriginal file: {original_key} ({file_size} bytes)")
        print("Path variations:")
        
        for test_key in path_variations:
            exists = test_s3_path(test_key)
            s3_size = get_s3_file_size(test_key)
            print(f"  {test_key}: {'✅ EXISTS' if exists else '❌ NOT FOUND'} (size: {s3_size} bytes)")
            
            # Try to download the file if it exists
            if exists:
                download_success, downloaded_size = test_download(test_key)
                print(f"    Download: {'✅ SUCCESS' if download_success else '❌ FAILED'} (size: {downloaded_size} bytes)")
                
    print("\n=== EVALUATION ===")
    print("If multiple path variations succeed (✅) for the same original file,")
    print("that means your S3 setup has inconsistent path handling.")
    print("If only one path variation works, that's good - it means your storage is consistent.")
    print("The OpenAI integration can now handle all path variations.")
    print("\nNext steps:")
    print("1. When uploading a new file, check that it's stored with the correct path.")
    print("2. If you need to fix historical files, you might want to run a migration script.")
else:
    print("No files found in the S3 bucket.") 