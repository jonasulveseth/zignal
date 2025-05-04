#!/usr/bin/env python
"""
Test uploading a file through the actual DataFile model to verify S3 storage works
"""
import os
import uuid
import logging
import django
import tempfile
from pathlib import Path

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zignal.config.settings')
django.setup()

from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.core.files import File

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_datasilo_file_upload():
    """Test uploading a file through the DataFile model"""
    from datasilo.models import DataSilo, DataFile
    from companies.models import Company
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    # Get admin user
    admin = User.objects.filter(is_superuser=True).first()
    if not admin:
        logger.error("No admin user found, cannot run test")
        return
    
    # Get or create a test company
    company, created = Company.objects.get_or_create(
        name="Test Company",
        defaults={
            "slug": "test-company",
            "created_by": admin
        }
    )
    logger.info(f"Using company: {company.name} (ID: {company.id})")
    
    # Get or create a test data silo
    data_silo, created = DataSilo.objects.get_or_create(
        name="Test Data Silo",
        company=company,
        defaults={
            "description": "Test data silo for S3 upload test",
            "created_by": admin
        }
    )
    logger.info(f"Using data silo: {data_silo.name} (ID: {data_silo.id})")
    
    # Create a temporary file with unique content
    test_id = uuid.uuid4().hex[:8]
    test_content = f"Test content for S3 upload test {test_id}"
    
    with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as temp_file:
        temp_file.write(test_content.encode())
        temp_file_path = temp_file.name
    
    try:
        # Create a DataFile object
        logger.info(f"Creating DataFile with test file: {temp_file_path}")
        
        with open(temp_file_path, 'rb') as file_obj:
            data_file = DataFile(
                name=f"Test File {test_id}",
                description="Test file for S3 upload test",
                data_silo=data_silo,
                company=company,
                file_type='document',
                uploaded_by=admin
            )
            
            # Assign file manually - this will trigger upload
            data_file.file = File(file_obj, name=f"test_upload_{test_id}.txt")
            data_file.save()
        
        logger.info(f"DataFile created with ID: {data_file.id}")
        logger.info(f"File path: {data_file.file.name}")
        logger.info(f"File URL: {data_file.file.url}")
        
        # Verify file exists in storage
        exists = default_storage.exists(data_file.file.name)
        logger.info(f"File exists in storage: {exists}")
        
        # If it exists, try to read content
        if exists:
            content = default_storage.open(data_file.file.name).read().decode()
            content_matches = content == test_content
            logger.info(f"File content matches original: {content_matches}")
        
        # Check if storage is S3
        logger.info(f"Storage class: {default_storage.__class__.__name__}")
        logger.info(f"Is using S3: {'s3.amazonaws.com' in data_file.file.url}")
        
        return data_file
    
    finally:
        # Clean up temp file
        os.unlink(temp_file_path)

if __name__ == "__main__":
    data_file = test_datasilo_file_upload()
    
    # Simulate vector store processing
    from core.tasks import process_file_for_vector_store
    if data_file:
        logger.info(f"Testing process_file_for_vector_store with file ID: {data_file.id}")
        result = process_file_for_vector_store(data_file.id)
        logger.info(f"Result: {result}")
    
    logger.info("Test completed") 