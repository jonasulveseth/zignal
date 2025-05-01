"""
Test script to verify OpenAI integration with assistants
"""
import os
import django
import logging
import datetime

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zignal.config.settings')
django.setup()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import Django models
from django.contrib.auth import get_user_model
from companies.models import Company, UserCompanyRelation
from companies.services.openai_service import CompanyOpenAIService

User = get_user_model()

def test_create_assistant():
    """Test the creation of an OpenAI assistant for a company"""
    try:
        # Get the first user
        user = User.objects.first()
        if not user:
            logger.error("No users found in the database")
            return False
        
        # Create a test company
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        company_name = f"Test Company {timestamp}"
        
        company = Company.objects.create(
            name=company_name,
            description="A test company for OpenAI integration",
            created_by=user
        )
        logger.info(f"Created company: {company.name} (ID: {company.id})")
        
        # Create relation between user and company
        UserCompanyRelation.objects.create(
            user=user,
            company=company,
            role='owner'
        )
        
        # Create assistant
        service = CompanyOpenAIService()
        result = service.setup_company_ai(company)
        
        if result['success']:
            logger.info(f"Successfully created assistant: {result['assistant_id']}")
            
            # Update company with OpenAI resource IDs
            company.openai_assistant_id = result['assistant_id']
            company.openai_vector_store_id = result['vector_store_id']
            company.save()
            
            logger.info(f"Company {company.name} updated with OpenAI IDs")
            logger.info(f"  - Assistant ID: {company.openai_assistant_id}")
            logger.info(f"  - Vector Store ID: {company.openai_vector_store_id}")
            
            return True
        else:
            logger.error(f"Failed to create assistant: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        logger.error(f"Error in test_create_assistant: {str(e)}")
        return False

def test_add_file():
    """Test adding a file to a company's assistant"""
    try:
        # Get the most recently created company
        company = Company.objects.exclude(openai_assistant_id__isnull=True).exclude(openai_assistant_id="").order_by('-created_at').first()
        
        if not company:
            logger.error("No company with OpenAI assistant found")
            return False
        
        logger.info(f"Using company: {company.name} (ID: {company.id})")
        logger.info(f"  - Assistant ID: {company.openai_assistant_id}")
        logger.info(f"  - Vector Store ID: {company.openai_vector_store_id}")
        
        # Create a test file
        test_file_path = "/tmp/test_document.md"
        with open(test_file_path, "w") as f:
            f.write(f"""# Test Document for {company.name}

This is a test document created at {datetime.datetime.now().isoformat()}.

It contains some information about the company:
- Company name: {company.name}
- Company ID: {company.id}
- Description: {company.description}

This document should be searchable by the OpenAI assistant.
""")
        
        # Add the file to the assistant
        service = CompanyOpenAIService()
        result = service.add_file_to_vector_store(company, test_file_path)
        
        # Clean up
        os.remove(test_file_path)
        
        if result['success']:
            logger.info(f"Successfully added file to assistant")
            logger.info(f"  - File ID: {result['file_id']}")
            logger.info(f"  - File Attachment ID: {result['file_attachment_id']}")
            return True
        else:
            logger.error(f"Failed to add file: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        logger.error(f"Error in test_add_file: {str(e)}")
        return False

if __name__ == "__main__":
    # Test creating a company with an assistant
    logger.info("==== Testing Assistant Creation ====")
    success = test_create_assistant()
    logger.info(f"Test result: {'SUCCESS' if success else 'FAILED'}")
    
    # Test adding a file to the assistant
    logger.info("\n==== Testing File Addition ====")
    success = test_add_file()
    logger.info(f"Test result: {'SUCCESS' if success else 'FAILED'}") 