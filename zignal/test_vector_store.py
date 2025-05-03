#!/usr/bin/env python
"""
Debug script for testing vector store processing directly
"""
import os
import sys
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zignal.settings')
django.setup()

# Import needed models after Django setup
from datasilo.models import DataFile
from core.tasks import process_file_for_vector_store
from django.contrib.auth import get_user_model
from companies.services.openai_service import CompanyOpenAIService

# Configure logging
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('vector_store_debug')

def test_file_processing():
    """Test vector store processing with the most recent file"""
    try:
        # Get the most recent file
        files = DataFile.objects.order_by('-created_at')
        if not files.exists():
            logger.error("No files found in the database")
            return
        
        file = files.first()
        logger.info(f"Testing with file: {file.name} (ID: {file.id})")
        
        # Check vector store status
        logger.info(f"Current vector store status: {file.vector_store_status}")
        logger.info(f"Vector store file ID: {file.vector_store_file_id}")
        
        # Check company info
        company = None
        company_path = ""
        
        if hasattr(file, 'company') and file.company:
            company = file.company
            company_path = "direct company relation"
        elif hasattr(file, 'project') and file.project and file.project.company:
            company = file.project.company
            company_path = "project -> company relation"
        elif hasattr(file, 'data_silo') and file.data_silo:
            if file.data_silo.company:
                company = file.data_silo.company
                company_path = "data_silo -> company relation"
            elif file.data_silo.project and file.data_silo.project.company:
                company = file.data_silo.project.company
                company_path = "data_silo -> project -> company relation"
        
        if company:
            logger.info(f"Found company: {company.name} (ID: {company.id}) via {company_path}")
            logger.info(f"Company OpenAI vector store ID: {company.openai_vector_store_id}")
            logger.info(f"Company OpenAI assistant ID: {company.openai_assistant_id}")
        else:
            logger.error("No company found for file")
            return
            
        # Check OpenAI API key
        from django.conf import settings
        api_key = getattr(settings, 'OPENAI_API_KEY', None)
        if api_key:
            # Only show first few chars for security
            logger.info(f"OpenAI API key exists: {api_key[:4]}...{api_key[-4:] if len(api_key) > 8 else ''}")
        else:
            logger.error("No OpenAI API key found in settings")
            return
            
        # Check if the file exists on disk
        if os.path.exists(file.file.path):
            logger.info(f"File exists at path: {file.file.path}")
            logger.info(f"File size: {os.path.getsize(file.file.path)} bytes")
        else:
            logger.error(f"File does not exist at path: {file.file.path}")
            return
        
        # Test create vector store directly
        service = CompanyOpenAIService()
        if not company.openai_vector_store_id:
            logger.info("Creating vector store for company...")
            result = service.setup_company_ai(company)
            logger.info(f"Setup result: {result}")
            if result.get('success'):
                company.openai_vector_store_id = result.get('vector_store_id')
                company.openai_assistant_id = result.get('assistant_id')
                company.save(update_fields=['openai_vector_store_id', 'openai_assistant_id'])
                logger.info(f"Updated company with vector store ID: {company.openai_vector_store_id}")
        
        # Try direct file upload to vector store
        logger.info("Uploading file to vector store directly...")
        result = service.add_file_to_vector_store(company, file.file.path, file.name)
        logger.info(f"Upload result: {result}")
        
        # Now try with the Celery task (but run synchronously)
        logger.info("Running Celery task synchronously...")
        task_result = process_file_for_vector_store(file.id)
        logger.info(f"Task result: {task_result}")
        
        # Check final status
        file.refresh_from_db()
        logger.info(f"Final vector store status: {file.vector_store_status}")
        logger.info(f"Final vector store file ID: {file.vector_store_file_id}")
        
    except Exception as e:
        import traceback
        logger.error(f"Error in test: {str(e)}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    logger.info("Starting vector store debug test")
    test_file_processing()
    logger.info("Finished vector store debug test") 