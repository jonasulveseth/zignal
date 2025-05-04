#!/usr/bin/env python
"""
Debug script for testing direct S3 operations with boto3
"""
import os
import sys
import django
import argparse
import logging

# Parse command line arguments
parser = argparse.ArgumentParser(description='Test direct S3 operations')
parser.add_argument('--bucket', help='S3 bucket name (overrides settings)')
parser.add_argument('--region', help='S3 region name (overrides settings)')
parser.add_argument('--key-id', help='AWS access key ID (overrides settings)')
parser.add_argument('--secret-key', help='AWS secret access key (overrides settings)')
parser.add_argument('--list-files', action='store_true', help='List files in the bucket')
parser.add_argument('--upload-test-file', action='store_true', help='Upload a test file to S3')
parser.add_argument('--prefix', default='', help='Prefix to list files under or upload test file to')
args = parser.parse_args()

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zignal.config.settings')
django.setup()

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('s3_direct_debug')

# Import settings
from django.conf import settings

def test_s3_direct():
    """Test direct S3 operations with boto3"""
    try:
        import boto3
        from botocore.exceptions import ClientError
        
        # Get settings from args or Django settings
        aws_access_key_id = args.key_id or getattr(settings, 'AWS_ACCESS_KEY_ID', '')
        aws_secret_access_key = args.secret_key or getattr(settings, 'AWS_SECRET_ACCESS_KEY', '')
        aws_region = args.region or getattr(settings, 'AWS_S3_REGION_NAME', 'eu-north-1')
        bucket_name = args.bucket or getattr(settings, 'AWS_STORAGE_BUCKET_NAME', '')
        prefix = args.prefix or getattr(settings, 'AWS_LOCATION', '')
        
        if not bucket_name:
            logger.error("No bucket name provided or configured")
            return False
            
        if not aws_access_key_id or not aws_secret_access_key:
            logger.error("AWS credentials not provided or configured")
            return False
            
        # Log settings
        logger.info(f"AWS Region: {aws_region}")
        logger.info(f"S3 Bucket: {bucket_name}")
        logger.info(f"Using prefix: {prefix}")
        logger.info(f"AWS Access Key ID: {aws_access_key_id[:4]}...{aws_access_key_id[-4:]}")
            
        # Create S3 client
        s3 = boto3.client(
            's3',
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=aws_region
        )
        
        # Test bucket access
        try:
            s3.head_bucket(Bucket=bucket_name)
            logger.info(f"Successfully connected to bucket: {bucket_name}")
        except ClientError as e:
            logger.error(f"Error accessing bucket: {e.response['Error']['Message']}")
            logger.error(f"Error code: {e.response['Error']['Code']}")
            return False
        
        # List buckets
        response = s3.list_buckets()
        logger.info(f"Found {len(response['Buckets'])} buckets")
        for bucket in response['Buckets']:
            logger.info(f"  - {bucket['Name']}")
            
        # List files in bucket (if requested)
        if args.list_files:
            logger.info(f"Listing files in bucket {bucket_name} with prefix '{prefix}':")
            
            try:
                paginator = s3.get_paginator('list_objects_v2')
                page_iterator = paginator.paginate(
                    Bucket=bucket_name,
                    Prefix=prefix
                )
                
                file_count = 0
                for page in page_iterator:
                    if 'Contents' in page:
                        for obj in page['Contents']:
                            logger.info(f"  - {obj['Key']} ({obj['Size']} bytes)")
                            file_count += 1
                
                if file_count == 0:
                    logger.warning(f"No files found in bucket with prefix '{prefix}'")
                else:
                    logger.info(f"Found {file_count} file(s) in total")
            except ClientError as e:
                logger.error(f"Error listing files: {e.response['Error']['Message']}")
                return False
                
        # Upload test file (if requested)
        if args.upload_test_file:
            import tempfile
            import datetime
            
            # Create a test file
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            test_filename = f"test_file_{timestamp}.txt"
            test_content = f"This is a test file created at {datetime.datetime.now().isoformat()}"
            
            with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp:
                temp.write(test_content)
                temp_path = temp.name
            
            # Define S3 key with prefix if provided
            s3_key = test_filename
            if prefix:
                s3_key = f"{prefix}/{test_filename}"
                
            logger.info(f"Uploading test file to S3 key: {s3_key}")
            
            try:
                # Upload the file
                s3.upload_file(
                    Filename=temp_path,
                    Bucket=bucket_name,
                    Key=s3_key
                )
                
                logger.info(f"Successfully uploaded test file to {s3_key}")
                
                # Verify upload
                try:
                    head = s3.head_object(Bucket=bucket_name, Key=s3_key)
                    logger.info(f"Verified file upload: size {head['ContentLength']} bytes")
                    logger.info(f"S3 URL: https://{bucket_name}.s3.{aws_region}.amazonaws.com/{s3_key}")
                except ClientError as e:
                    logger.error(f"Error verifying upload: {e.response['Error']['Message']}")
            
            except ClientError as e:
                logger.error(f"Error uploading file: {e.response['Error']['Message']}")
                
            finally:
                # Clean up temp file
                os.unlink(temp_path)
                
        return True
        
    except Exception as e:
        import traceback
        logger.error(f"Error in S3 direct test: {str(e)}")
        logger.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    # Run the test
    success = test_s3_direct()
    sys.exit(0 if success else 1) 