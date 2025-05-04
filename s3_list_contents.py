#!/usr/bin/env python
"""
List all objects in S3 bucket to find where files are actually stored
"""
import os
import boto3
import sys

# AWS credentials from environment
aws_access_key_id = os.environ.get('AWS_ACCESS_KEY_ID')
aws_secret_access_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
aws_storage_bucket_name = os.environ.get('AWS_STORAGE_BUCKET_NAME', 'zignalse')
aws_s3_region_name = os.environ.get('AWS_S3_REGION_NAME', 'eu-west-1')

print(f"Listing all objects in S3 bucket: {aws_storage_bucket_name}")
print(f"Region: {aws_s3_region_name}")
print(f"Access Key ID: {aws_access_key_id[:4]}...{aws_access_key_id[-4:]}")

try:
    # Create S3 client
    s3 = boto3.client(
        's3',
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=aws_s3_region_name
    )
    
    # List objects in bucket using pagination
    paginator = s3.get_paginator('list_objects_v2')
    page_iterator = paginator.paginate(Bucket=aws_storage_bucket_name)
    
    count = 0
    pdf_files = []
    
    for page in page_iterator:
        if 'Contents' in page:
            for obj in page['Contents']:
                count += 1
                key = obj['Key']
                
                # Save PDF files to list to display later
                if key.lower().endswith('.pdf'):
                    pdf_files.append({
                        'key': key,
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'].strftime('%Y-%m-%d %H:%M:%S')
                    })
    
    print(f"\nFound {count} total objects in bucket")
    
    if pdf_files:
        print(f"\nFound {len(pdf_files)} PDF files:")
        for i, pdf in enumerate(pdf_files, 1):
            print(f"{i}. {pdf['key']} ({pdf['size']} bytes, modified: {pdf['last_modified']})")
    else:
        print("\nNo PDF files found in bucket")
        
except Exception as e:
    print(f"Error: {str(e)}")
    sys.exit(1) 