#!/usr/bin/env python
"""
Test script to verify S3 connection using Heroku environment variables
"""
import os
import boto3
import sys
from botocore.exceptions import ClientError

# AWS credentials from environment
aws_access_key_id = os.environ.get('AWS_ACCESS_KEY_ID')
aws_secret_access_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
aws_storage_bucket_name = os.environ.get('AWS_STORAGE_BUCKET_NAME', 'zignalse')
aws_s3_region_name = os.environ.get('AWS_S3_REGION_NAME', 'eu-west-1')
aws_location = os.environ.get('AWS_LOCATION', 'media')

print(f"Testing S3 connection with:")
print(f"  Bucket: {aws_storage_bucket_name}")
print(f"  Region: {aws_s3_region_name}")
print(f"  Location prefix: {aws_location}")
print(f"  Access Key ID: {aws_access_key_id[:4]}...{aws_access_key_id[-4:]}")

# Create S3 client
try:
    s3 = boto3.client(
        's3',
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=aws_s3_region_name
    )
    print("Successfully created S3 client")
    
    # Test bucket access
    try:
        s3.head_bucket(Bucket=aws_storage_bucket_name)
        print(f"✅ Successfully connected to bucket: {aws_storage_bucket_name}")
    except ClientError as e:
        print(f"❌ Error accessing bucket: {e.response['Error']['Message']}")
        print(f"   Error code: {e.response['Error']['Code']}")
        sys.exit(1)
    
    # Try to list objects in bucket
    try:
        objects = s3.list_objects_v2(
            Bucket=aws_storage_bucket_name,
            Prefix=aws_location,
            MaxKeys=5
        )
        
        if 'Contents' in objects:
            print(f"✅ Successfully listed objects in {aws_location}/")
            print(f"   Found {len(objects['Contents'])} objects:")
            for obj in objects['Contents']:
                print(f"   - {obj['Key']} ({obj['Size']} bytes)")
        else:
            print(f"✅ Bucket exists but no objects found in {aws_location}/")
            
        # Try to upload a test file
        test_key = f"{aws_location}/test_file.txt"
        try:
            s3.put_object(
                Bucket=aws_storage_bucket_name,
                Key=test_key,
                Body=b'This is a test file',
                ContentType='text/plain'
            )
            print(f"✅ Successfully uploaded test file to {test_key}")
            
            # Delete the test file
            s3.delete_object(
                Bucket=aws_storage_bucket_name,
                Key=test_key
            )
            print(f"✅ Successfully deleted test file {test_key}")
            
        except ClientError as e:
            print(f"❌ Error uploading test file: {e.response['Error']['Message']}")
    
    except ClientError as e:
        print(f"❌ Error listing objects: {e.response['Error']['Message']}")

except Exception as e:
    print(f"❌ Error creating S3 client: {str(e)}")
    sys.exit(1)

print("✅ S3 connection test completed successfully") 