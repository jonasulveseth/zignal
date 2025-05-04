"""
Manual test script for OpenAI assistant creation
"""
import os
import logging
import datetime
import django

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

def create_test_company():
    """Create a test company for a user"""
    try:
        # Get a user (create one if none exists)
        user = User.objects.first()
        if not user:
            user_email = input("No users found. Enter an email for a new test user: ")
            user = User.objects.create_user(
                username=user_email,
                email=user_email,
                password="testpassword123"
            )
            logger.info(f"Created test user: {user.email}")
        
        # Create a test company
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        company_name = input(f"Enter company name (default: Test Company {timestamp}): ") or f"Test Company {timestamp}"
        
        company = Company.objects.create(
            name=company_name,
            description=f"A test company created at {timestamp}",
            created_by=user
        )
        logger.info(f"Created test company: {company.name} (ID: {company.id})")
        
        # Create relation between user and company
        UserCompanyRelation.objects.create(
            user=user,
            company=company,
            role='owner'
        )
        logger.info(f"Created user-company relation for user {user.email} and company {company.name}")
        
        return company
    except Exception as e:
        logger.error(f"Error creating test company: {str(e)}")
        return None

def setup_openai_assistant(company):
    """Set up OpenAI assistant for the company"""
    try:
        if not company:
            logger.error("No company provided")
            return False
        
        logger.info(f"Setting up OpenAI assistant for company: {company.name}")
        
        # Create OpenAI assistant
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
        logger.error(f"Error setting up OpenAI assistant: {str(e)}")
        return False

def add_test_file(company):
    """Add a test file to the company's assistant"""
    try:
        if not company:
            logger.error("No company provided")
            return False
        
        if not company.openai_assistant_id:
            logger.error(f"Company {company.name} does not have an OpenAI assistant")
            return False
        
        logger.info(f"Adding test file to company {company.name}'s assistant")
        
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
        logger.error(f"Error adding test file: {str(e)}")
        return False

def run_tests():
    """Run all tests"""
    logger.info("==== Testing OpenAI Assistant Creation ====")
    
    # Check if OpenAI API key is set
    if not os.environ.get("OPENAI_API_KEY"):
        api_key = input("Enter your OpenAI API key: ")
        os.environ["OPENAI_API_KEY"] = api_key
    
    # Create a test company
    company = create_test_company()
    if not company:
        logger.error("Failed to create test company")
        return
    
    # Set up OpenAI assistant
    if not setup_openai_assistant(company):
        logger.error("Failed to set up OpenAI assistant")
        return
    
    # Add a test file
    if not add_test_file(company):
        logger.error("Failed to add test file")
        return
    
    logger.info("==== All tests completed successfully ====")
    logger.info(f"Company ID: {company.id}")
    logger.info(f"Assistant ID: {company.openai_assistant_id}")
    logger.info(f"Vector Store ID: {company.openai_vector_store_id}")

if __name__ == "__main__":
    run_tests() 