"""
Script to fix S3 storage configuration and implement a solution
for the double media/ prefix issue
"""
import os
import sys
import boto3
import dotenv
from pathlib import Path

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

print("\n=== CURRENT S3 CONFIGURATION ===")
print(f"AWS_STORAGE_BUCKET_NAME: {aws_bucket}")
print(f"AWS_S3_REGION_NAME: {aws_region}")
print(f"AWS_LOCATION: {aws_location}")

print("\n=== SOLUTION TO DOUBLE MEDIA/ PREFIX ISSUE ===")

# Option 1: Change AWS_LOCATION if it's set to 'media'
if aws_location == 'media':
    print("Option 1: Change AWS_LOCATION to an empty string")
    print("This will prevent the double 'media/' prefix.")
    print("Update your .env file with:")
    print("AWS_LOCATION=")
    
    # Prompt to update .env file
    if input("\nWould you like to update your .env file to use AWS_LOCATION=''? (y/n): ").lower() == 'y':
        # Read the .env file
        with open(env_file, 'r') as f:
            env_content = f.read()
        
        # Check if AWS_LOCATION exists and update it
        if 'AWS_LOCATION=' in env_content:
            env_content = env_content.replace('AWS_LOCATION=media', 'AWS_LOCATION=')
            env_content = env_content.replace('AWS_LOCATION="media"', 'AWS_LOCATION=""')
            env_content = env_content.replace("AWS_LOCATION='media'", "AWS_LOCATION=''")
        else:
            # Add AWS_LOCATION
            env_content += '\nAWS_LOCATION='
        
        # Write back to the .env file
        with open(env_file, 'w') as f:
            f.write(env_content)
        
        print("✅ .env file updated successfully.")
    else:
        print("No changes made to .env file.")

# Option 2: Create an improved MediaStorage class implementation
print("\nOption 2: Modify MediaStorage class in settings.py")
print("This approach will update the storage class to handle paths correctly.")

storage_class_code = """
# Create customized S3 storage with our configured settings
from storages.backends.s3boto3 import S3Boto3Storage

class MediaStorage(S3Boto3Storage):
    location = AWS_LOCATION
    file_overwrite = AWS_S3_FILE_OVERWRITE
    default_acl = AWS_DEFAULT_ACL
    
    def _normalize_name(self, name):
        '''
        Override to handle both absolute and relative paths
        This ensures consistent storage path construction 
        regardless of what Django passes in
        '''
        if name.startswith('/'):
            name = name[1:]
            
        # Add media/ prefix only if:
        # 1. AWS_LOCATION is not 'media' (to prevent double media/ prefix)
        # 2. The name doesn't already have a media/ prefix
        if AWS_LOCATION != 'media' and not name.startswith('media/'):
            name = f'media/{name}'
            
        return super()._normalize_name(name)
"""

print("\nUpdated MediaStorage class that prevents double 'media/' prefix:")
print(storage_class_code)

print("\n=== TROUBLESHOOTING OPENAI INTEGRATION ===")
print("To fix the OpenAI integration that accesses S3 files:")
print("1. Use the fix_openai_s3_integration.py script to apply a temporary monkey patch")
print("2. For a permanent fix, update the companies/services/openai_service.py file")
print("   to try multiple path variations when accessing S3 files")

print("\n=== TESTING THE FIX ===")
print("After making these changes, here's how to verify the fix:")
print("1. Upload a new file through the application")
print("2. Check the S3 bucket to ensure it's stored with the correct path")
print("3. Verify that OpenAI processing works correctly")

print("\nFor more detailed diagnostics, run: python -m zignal.s3_diagnostic") 