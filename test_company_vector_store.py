#!/usr/bin/env python
"""
Test script to verify the CompanyOpenAIService vector store functionality
"""
import os
import sys
import django
import logging
import tempfile

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add the zignal directory to the path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "zignal"))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zignal.config.settings')

# Print some debug info
print(f"Python path: {sys.path}")
print(f"Current directory: {os.getcwd()}")
print(f"Django settings module: {os.environ.get('DJANGO_SETTINGS_MODULE')}")

# Initialize Django
django.setup()

# Print some Django debug info
from django.conf import settings
print(f"Django settings initialized: {bool(settings)}")
print(f"OpenAI API key available: {bool(settings.OPENAI_API_KEY)}")
print(f"OpenAI API key first 5 chars: {settings.OPENAI_API_KEY[:5] if settings.OPENAI_API_KEY else 'N/A'}")

from companies.services.openai_service import CompanyOpenAIService
from companies.models import Company

def test_vector_store():
    """
    Test the vector store functionality for companies
    """
    try:
        # Initialize the service
        service = CompanyOpenAIService()
        logger.info("Initialized CompanyOpenAIService")
        
        # Check if vector_stores is available
        has_vector_stores = hasattr(service.client, 'vector_stores')
        logger.info(f"Vector stores available: {has_vector_stores}")
        
        # Get or create a test company
        company_name = "Vector Store Test Company"
        company = Company.objects.filter(name=company_name).first()
        if not company:
            logger.info(f"Creating test company: {company_name}")
            company = Company(name=company_name)
            company.save()
        else:
            logger.info(f"Using existing company: {company.name} (ID: {company.id})")
            
        # Set up the AI resources for the company
        if not company.openai_assistant_id or not company.openai_vector_store_id:
            logger.info("Setting up OpenAI resources for company...")
            result = service.setup_company_ai(company)
            if result["success"]:
                company.openai_assistant_id = result['assistant_id']
                company.openai_vector_store_id = result['vector_store_id']
                company.save()
                logger.info(f"Successfully set up AI resources:")
                logger.info(f"  - Assistant ID: {company.openai_assistant_id}")
                logger.info(f"  - Vector Store ID: {company.openai_vector_store_id}")
            else:
                logger.error(f"Failed to set up AI resources: {result['error']}")
                print(f"Failed to set up AI resources: {result['error']}")
                return
        else:
            logger.info("Company already has OpenAI resources set up:")
            logger.info(f"  - Assistant ID: {company.openai_assistant_id}")
            logger.info(f"  - Vector Store ID: {company.openai_vector_store_id}")
            
        # Test adding a file to the vector store
        logger.info("Creating a temporary test file...")
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as temp_file:
            temp_file.write(b"This is a test document for vector store testing. It contains information about AI and machine learning.")
            test_file_path = temp_file.name
            
        logger.info(f"Adding file to vector store: {test_file_path}")
        result = service.add_file_to_vector_store(company, test_file_path)
        
        if result["success"]:
            logger.info("Successfully added file to vector store:")
            for key, value in result.items():
                logger.info(f"  - {key}: {value}")
        else:
            logger.error(f"Failed to add file to vector store: {result['error']}")
            print(f"Failed to add file to vector store: {result['error']}")
            
        # Clean up the temporary file
        os.unlink(test_file_path)
        logger.info("Test completed")
            
    except Exception as e:
        logger.error(f"Error in test_vector_store: {str(e)}")
        print(f"Error in test_vector_store: {str(e)}")

if __name__ == "__main__":
    print("Starting vector store test...")
    test_vector_store()
    print("Test finished.") 