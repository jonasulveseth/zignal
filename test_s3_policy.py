#!/usr/bin/env python
"""
Test S3 permissions and diagnose IAM policy issues
"""
import os
import sys
import json
import django
import logging
import tempfile
import datetime
import argparse
from botocore.exceptions import ClientError

# Parse command line arguments
parser = argparse.ArgumentParser(description='Test S3 permissions and generate IAM policy')
parser.add_argument('--bucket', help='S3 bucket name (overrides settings)')
parser.add_argument('--region', help='S3 region name (overrides settings)')
parser.add_argument('--key-id', help='AWS access key ID (overrides settings)')
parser.add_argument('--secret-key', help='AWS secret access key (overrides settings)')
parser.add_argument('--location', help='Location prefix in bucket (overrides settings)')
args = parser.parse_args()

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zignal.config.settings')
django.setup()

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('s3_policy_test')

# Import settings
from django.conf import settings

def create_minimal_iam_policy(bucket_name, location_prefix):
    """Create a minimal IAM policy for S3 access"""
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "s3:ListBucket"
                ],
                "Resource": [
                    f"arn:aws:s3:::{bucket_name}"
                ]
            },
            {
                "Effect": "Allow",
                "Action": [
                    "s3:PutObject",
                    "s3:GetObject",
                    "s3:DeleteObject",
                    "s3:PutObjectAcl"
                ],
                "Resource": [
                    f"arn:aws:s3:::{bucket_name}/{location_prefix}/*"
                ]
            }
        ]
    }
    
    return json.dumps(policy, indent=4)

def test_s3_permissions():
    """Test S3 permissions and generate recommended IAM policy"""
    try:
        import boto3
        
        # Get settings from args or Django settings
        aws_access_key_id = args.key_id or getattr(settings, 'AWS_ACCESS_KEY_ID', '')
        aws_secret_access_key = args.secret_key or getattr(settings, 'AWS_SECRET_ACCESS_KEY', '')
        aws_region = args.region or getattr(settings, 'AWS_S3_REGION_NAME', 'eu-north-1')
        bucket_name = args.bucket or getattr(settings, 'AWS_STORAGE_BUCKET_NAME', '')
        location_prefix = args.location or getattr(settings, 'AWS_LOCATION', '')
        
        if not bucket_name:
            logger.error("No bucket name provided or configured")
            return False
            
        if not aws_access_key_id or not aws_secret_access_key:
            logger.error("AWS credentials not provided or configured")
            return False
            
        # Log settings
        logger.info(f"AWS Region: {aws_region}")
        logger.info(f"S3 Bucket: {bucket_name}")
        logger.info(f"Using prefix: {location_prefix}")
        logger.info(f"AWS Access Key ID: {aws_access_key_id[:4]}...{aws_access_key_id[-4:]}")
            
        # Create S3 client
        s3 = boto3.client(
            's3',
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=aws_region
        )
        
        # Create resource for higher-level operations
        s3_resource = boto3.resource(
            's3',
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=aws_region
        )
        
        # Test operations and track results
        test_results = {}
        
        # Test 1: List buckets (requires global s3:ListAllMyBuckets permission)
        try:
            logger.info("Testing s3:ListAllMyBuckets permission...")
            response = s3.list_buckets()
            buckets = [bucket['Name'] for bucket in response['Buckets']]
            test_results['list_buckets'] = {
                'success': True,
                'buckets': buckets,
                'message': f"Found {len(buckets)} buckets"
            }
            logger.info(f"SUCCESS: Found {len(buckets)} buckets")
            for bucket in buckets:
                logger.info(f"  - {bucket}")
        except ClientError as e:
            error = e.response['Error']
            test_results['list_buckets'] = {
                'success': False,
                'error_code': error['Code'],
                'message': error['Message']
            }
            logger.error(f"FAILED: Cannot list buckets - {error['Code']}: {error['Message']}")
        
        # Test 2: List objects in bucket (requires s3:ListBucket permission)
        try:
            logger.info(f"Testing s3:ListBucket permission on {bucket_name}...")
            prefix = f"{location_prefix}/" if location_prefix else ""
            objects = list(s3_resource.Bucket(bucket_name).objects.filter(Prefix=prefix).limit(10))
            
            test_results['list_objects'] = {
                'success': True,
                'count': len(objects),
                'message': f"Found {len(objects)} objects with prefix '{prefix}'"
            }
            logger.info(f"SUCCESS: Found {len(objects)} objects with prefix '{prefix}'")
            for obj in objects[:5]:  # Show at most 5 objects
                logger.info(f"  - {obj.key} ({obj.size} bytes)")
            if len(objects) > 5:
                logger.info(f"  ... and {len(objects) - 5} more")
        except ClientError as e:
            error = e.response['Error']
            test_results['list_objects'] = {
                'success': False,
                'error_code': error['Code'],
                'message': error['Message']
            }
            logger.error(f"FAILED: Cannot list objects - {error['Code']}: {error['Message']}")
        
        # Test 3: Upload object (requires s3:PutObject permission)
        try:
            logger.info(f"Testing s3:PutObject permission on {bucket_name}...")
            
            # Create a test file
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            test_filename = f"test_file_{timestamp}.txt"
            test_content = f"This is a test file created at {datetime.datetime.now().isoformat()}"
            
            with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp:
                temp.write(test_content)
                temp_path = temp.name
            
            # Define S3 key with prefix if provided
            s3_key = test_filename
            if location_prefix:
                s3_key = f"{location_prefix}/{test_filename}"
                
            logger.info(f"Uploading test file to S3 key: {s3_key}")
            
            s3.upload_file(
                Filename=temp_path,
                Bucket=bucket_name,
                Key=s3_key
            )
            
            test_results['put_object'] = {
                'success': True,
                'key': s3_key,
                'message': f"Successfully uploaded test file to {s3_key}"
            }
            logger.info(f"SUCCESS: Uploaded test file to {s3_key}")
            
            # Clean up temp file
            os.unlink(temp_path)
            
            # Test 4: Get object (requires s3:GetObject permission)
            try:
                logger.info(f"Testing s3:GetObject permission on {bucket_name}/{s3_key}...")
                
                response = s3.get_object(
                    Bucket=bucket_name,
                    Key=s3_key
                )
                
                downloaded_content = response['Body'].read().decode('utf-8')
                content_match = downloaded_content == test_content
                
                test_results['get_object'] = {
                    'success': True,
                    'content_match': content_match,
                    'message': f"Downloaded file content {'matches' if content_match else 'does not match'}"
                }
                logger.info(f"SUCCESS: Downloaded file content {'matches' if content_match else 'does not match'}")
                
            except ClientError as e:
                error = e.response['Error']
                test_results['get_object'] = {
                    'success': False,
                    'error_code': error['Code'],
                    'message': error['Message']
                }
                logger.error(f"FAILED: Cannot get object - {error['Code']}: {error['Message']}")
            
            # Test 5: Delete object (requires s3:DeleteObject permission)
            try:
                logger.info(f"Testing s3:DeleteObject permission on {bucket_name}/{s3_key}...")
                
                s3.delete_object(
                    Bucket=bucket_name,
                    Key=s3_key
                )
                
                test_results['delete_object'] = {
                    'success': True,
                    'message': f"Successfully deleted test file {s3_key}"
                }
                logger.info(f"SUCCESS: Deleted test file {s3_key}")
                
            except ClientError as e:
                error = e.response['Error']
                test_results['delete_object'] = {
                    'success': False,
                    'error_code': error['Code'],
                    'message': error['Message']
                }
                logger.error(f"FAILED: Cannot delete object - {error['Code']}: {error['Message']}")
            
        except ClientError as e:
            error = e.response['Error']
            test_results['put_object'] = {
                'success': False,
                'error_code': error['Code'],
                'message': error['Message']
            }
            logger.error(f"FAILED: Cannot upload object - {error['Code']}: {error['Message']}")
            
        # Analyze results and generate recommendations
        logger.info("\n--- TEST RESULTS SUMMARY ---")
        permissions_needed = []
        
        if not test_results.get('list_buckets', {}).get('success', False):
            logger.info("❌ s3:ListAllMyBuckets permission missing or denied")
            permissions_needed.append("s3:ListAllMyBuckets")
        else:
            logger.info("✅ s3:ListAllMyBuckets permission granted")
            
        if not test_results.get('list_objects', {}).get('success', False):
            logger.info("❌ s3:ListBucket permission missing or denied")
            permissions_needed.append("s3:ListBucket")
        else:
            logger.info("✅ s3:ListBucket permission granted")
            
        if not test_results.get('put_object', {}).get('success', False):
            logger.info("❌ s3:PutObject permission missing or denied")
            permissions_needed.append("s3:PutObject")
        else:
            logger.info("✅ s3:PutObject permission granted")
            
        if not test_results.get('get_object', {}).get('success', False):
            logger.info("❌ s3:GetObject permission missing or denied")
            permissions_needed.append("s3:GetObject")
        else:
            logger.info("✅ s3:GetObject permission granted")
            
        if not test_results.get('delete_object', {}).get('success', False):
            logger.info("❌ s3:DeleteObject permission missing or denied")
            permissions_needed.append("s3:DeleteObject")
        else:
            logger.info("✅ s3:DeleteObject permission granted")
            
        # Generate recommended IAM policy
        logger.info("\n--- RECOMMENDED IAM POLICY ---")
        policy = create_minimal_iam_policy(bucket_name, location_prefix)
        logger.info(policy)
        
        return True
        
    except Exception as e:
        import traceback
        logger.error(f"Error testing S3 permissions: {str(e)}")
        logger.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    # Run the test
    success = test_s3_permissions()
    sys.exit(0 if success else 1) 