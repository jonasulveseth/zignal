#!/usr/bin/env python
"""
List contents of the S3 bucket to verify file uploads
"""
import os
import logging
import boto3

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def list_s3_contents():
    """List contents of the S3 bucket"""
    aws_access_key = os.environ.get('AWS_ACCESS_KEY_ID')
    aws_secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
    aws_region = os.environ.get('AWS_S3_REGION_NAME', 'eu-west-1')
    aws_bucket = os.environ.get('AWS_STORAGE_BUCKET_NAME', 'zignalse')
    
    try:
        # Create S3 client
        s3 = boto3.client(
            's3', 
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=aws_region
        )
        
        logger.info(f"Listing contents of S3 bucket: {aws_bucket}")
        
        # List all objects
        paginator = s3.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=aws_bucket)
        
        # Collect all objects
        all_objects = []
        for page in pages:
            if 'Contents' in page:
                all_objects.extend(page['Contents'])
        
        # Log summary
        logger.info(f"Found {len(all_objects)} objects in bucket {aws_bucket}")
        
        # Show all files
        logger.info("All files in bucket:")
        for i, obj in enumerate(all_objects):
            logger.info(f"  {i+1}. {obj['Key']} ({obj['Size']} bytes)")
        
        # Check for media/datasilo paths
        media_datasilo_objects = [obj for obj in all_objects if 'media/datasilo/' in obj['Key']]
        logger.info(f"Found {len(media_datasilo_objects)} objects in media/datasilo folder")
        
        return all_objects
    
    except Exception as e:
        logger.error(f"Error listing S3 contents: {str(e)}")
        return []

if __name__ == "__main__":
    list_s3_contents() 