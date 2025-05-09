"""
Simple S3 path diagnostic script
"""
import os
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

print("\n=== S3 CONFIGURATION ===")
print(f"AWS_STORAGE_BUCKET_NAME: {aws_bucket}")
print(f"AWS_S3_REGION_NAME: {aws_region}")
print(f"AWS_LOCATION: {aws_location}")

if not aws_access_key or not aws_secret_key or not aws_bucket:
    print("Missing AWS credentials or bucket name")
    exit(1)

# Create S3 client
try:
    print("\nConnecting to S3...")
    s3 = boto3.client(
        's3',
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key,
        region_name=aws_region
    )
    
    # List objects in the bucket
    print(f"\nListing objects in bucket: {aws_bucket}")
    response = s3.list_objects_v2(
        Bucket=aws_bucket,
        MaxKeys=20
    )
    
    if 'Contents' in response and len(response['Contents']) > 0:
        print(f"\nFound {len(response['Contents'])} files in S3 bucket:")
        
        # Print file paths and check for media/ prefix
        media_prefixed = 0
        double_media_prefixed = 0
        other_paths = 0
        
        # Dictionary to count files by path structure
        path_patterns = {}
        
        for item in response['Contents']:
            key = item['Key']
            size = item['Size']
            last_modified = item['LastModified']
            
            # Count files by path pattern
            if key.startswith('media/media/'):
                double_media_prefixed += 1
                pattern = "media/media/*"
            elif key.startswith('media/'):
                media_prefixed += 1
                pattern = "media/*"
            else:
                other_paths += 1
                pattern = "other"
            
            # Add to path patterns
            if pattern in path_patterns:
                path_patterns[pattern] += 1
            else:
                path_patterns[pattern] = 1
            
            print(f"File: {key}")
            print(f"  Size: {size} bytes")
            print(f"  Last modified: {last_modified}")
            
        # Print summary
        print("\n=== SUMMARY ===")
        print(f"Total files: {len(response['Contents'])}")
        print(f"Files with 'media/media/' prefix: {double_media_prefixed}")
        print(f"Files with 'media/' prefix (not double): {media_prefixed}")
        print(f"Files with other paths: {other_paths}")
        
        print("\nPath patterns:")
        for pattern, count in path_patterns.items():
            print(f"  {pattern}: {count} files")
        
        # Recommendation
        print("\n=== RECOMMENDATION ===")
        if double_media_prefixed > 0:
            print("Problem detected: Files are being saved with double 'media/' prefix.")
            print("This is likely because AWS_LOCATION is set to 'media' in settings,")
            print("and the MediaStorage class is adding 'media/' prefix again.")
            print("\nSolution options:")
            print("1. Change AWS_LOCATION to an empty string or a different value.")
            print("2. Modify the MediaStorage class to not add 'media/' prefix when AWS_LOCATION is 'media'.")
        else:
            print("No obvious path issues detected.")
    else:
        print("No files found in the S3 bucket.")
except Exception as e:
    print(f"Error: {str(e)}") 