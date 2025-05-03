from celery import shared_task
import logging
from django.utils import timezone
from projects.models import Project, UserProjectRelation
from datasilo.models import DataSilo, DataFile
import time
import os

logger = logging.getLogger(__name__)

@shared_task
def sample_task(arg):
    """
    A sample task to verify Celery is working
    """
    logger.info(f"Sample task executed with arg: {arg}")
    return f"Task completed with arg: {arg}"

@shared_task
def process_data(data_id):
    """
    Process data asynchronously
    """
    logger.info(f"Processing data with ID: {data_id}")
    # Add actual processing logic here
    return f"Data processing complete for ID: {data_id}"

@shared_task
def create_default_project_and_silo(company_id, user_id):
    """
    Create a default project and data silo for a newly created company
    
    Args:
        company_id (int): ID of the company
        user_id (int): ID of the user who created the company
        
    Returns:
        dict: Information about the created resources
    """
    from companies.models import Company
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    try:
        logger.info(f"Creating default project and silo for company ID: {company_id}")
        
        # Get company and user
        company = Company.objects.get(id=company_id)
        user = User.objects.get(id=user_id)
        
        # Create unique project name with timestamp to avoid slug collision
        timestamp = int(time.time())
        project_name = f"Default Project - {company.name} {timestamp}"
        
        # Create default project
        project = Project.objects.create(
            name=project_name,
            description=f"Default project for {company.name}",
            company=company,
            status='active',
            start_date=timezone.now().date(),
            created_by=user
        )
        
        # Create user-project relation
        UserProjectRelation.objects.create(
            user=user,
            project=project,
            role='manager'
        )
        
        logger.info(f"Created default project: {project.name} (ID: {project.id})")
        
        # Create default data silo linked to the project
        data_silo = DataSilo.objects.create(
            name=f"General Documents - {timestamp}",
            description=f"General document storage for {project.name}",
            project=project,
            company=company,
            created_by=user
        )
        
        logger.info(f"Created default data silo: {data_silo.name} (ID: {data_silo.id})")
        
        # Create default company-level data silo (not linked to project)
        company_silo = DataSilo.objects.create(
            name=f"Company Documents - {company.name} {timestamp}",
            description=f"Company-wide document storage for {company.name}",
            company=company,
            created_by=user
        )
        
        logger.info(f"Created company-level data silo: {company_silo.name} (ID: {company_silo.id})")
        
        return {
            "success": True,
            "project_id": project.id,
            "project_silo_id": data_silo.id,
            "company_silo_id": company_silo.id
        }
        
    except Exception as e:
        # Log detailed error info for easier debugging
        import traceback
        logger.error(f"Error creating default project and silo: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Log environment variables for debugging (only in non-production)
        from django.conf import settings
        if settings.DEBUG:
            redis_url = os.environ.get('REDIS_URL', 'not_set')
            celery_broker = os.environ.get('CELERY_BROKER_URL', 'not_set')
            celery_backend = os.environ.get('CELERY_RESULT_BACKEND', 'not_set')
            logger.debug(f"REDIS_URL: {redis_url[:10]}***")
            logger.debug(f"CELERY_BROKER_URL: {celery_broker[:10]}***")
            logger.debug(f"CELERY_RESULT_BACKEND: {celery_backend[:10]}***")
        
        return {
            "success": False,
            "error": str(e)
        }

@shared_task
def process_file_for_vector_store(file_id):
    """
    Process a file for the OpenAI Vector Store
    
    Args:
        file_id (int): ID of the DataFile to process
        
    Returns:
        dict: Result of the processing
    """
    from datasilo.models import DataFile
    from companies.models import Company
    from django.conf import settings
    from django.utils import timezone
    import os
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Configure Redis SSL settings for this task if necessary
    try:
        import redis
        import ssl
        from django.conf import settings
        
        # Check if we're using SSL Redis
        redis_url = os.environ.get('REDIS_URL', '')
        if redis_url.startswith('rediss://'):
            # Configure Redis to accept SSL connections without cert verification
            redis_ssl_settings = {
                'ssl_cert_reqs': ssl.CERT_NONE,
                'ssl_check_hostname': False,
            }
            # Patch Redis connection pool to use these settings
            from redis.connection import ConnectionPool
            
            # Apply SSL settings to the global default connection pool
            default_connection_pool = getattr(ConnectionPool, '_connection_pool_cache', {})
            for url, pool in default_connection_pool.items():
                if url.startswith('rediss://'):
                    pool.connection_kwargs.update(redis_ssl_settings)
            
            logger.info("Redis SSL settings applied for vector store processing")
    except Exception as e:
        logger.warning(f"Failed to configure Redis SSL settings: {str(e)}")
    
    try:
        logger.info(f"Processing file for vector store: {file_id}")
        
        # Get the file
        data_file = DataFile.objects.get(id=file_id)
        
        # Check if already processed
        if data_file.vector_store_file_id:
            logger.info(f"File already has a vector store ID: {data_file.vector_store_file_id}")
            return {
                "success": True,
                "message": "File already processed",
                "file_id": data_file.vector_store_file_id
            }
        
        # Update status
        data_file.vector_store_status = 'processing'
        data_file.save(update_fields=['vector_store_status'])
        
        # Try to get company
        company = None
        if data_file.company:
            company = data_file.company
        elif data_file.project and data_file.project.company:
            company = data_file.project.company
        elif data_file.data_silo and data_file.data_silo.company:
            company = data_file.data_silo.company
        
        if not company:
            logger.error(f"No company found for file {file_id}")
            data_file.vector_store_status = 'failed'
            data_file.save(update_fields=['vector_store_status'])
            return {
                "success": False,
                "error": "No company found for file"
            }
        
        # Check if company has a vector store
        if not company.openai_vector_store_id:
            logger.error(f"Company {company.name} has no vector store ID")
            data_file.vector_store_status = 'failed'
            data_file.save(update_fields=['vector_store_status'])
            return {
                "success": False,
                "error": "Company has no vector store"
            }
        
        # Import OpenAI service
        try:
            from companies.services.openai_service import CompanyOpenAIService
            openai_service = CompanyOpenAIService()
        except ImportError:
            logger.error("OpenAI service not available")
            data_file.vector_store_status = 'failed'
            data_file.save(update_fields=['vector_store_status'])
            return {
                "success": False,
                "error": "OpenAI service not available"
            }
        
        # Process the file
        file_path = data_file.file.path
        
        # Check if file exists and is accessible
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            data_file.vector_store_status = 'failed'
            data_file.save(update_fields=['vector_store_status'])
            return {
                "success": False,
                "error": "File not found on disk"
            }
        
        # Upload file to vector store
        result = openai_service.add_file_to_vector_store(
            company,
            file_path,
            data_file.name
        )
        
        if result.get('success'):
            # Update file with vector store ID
            data_file.vector_store_file_id = result.get('file_id')
            data_file.vector_store_status = 'processed'
            data_file.vector_store_processed_at = timezone.now()
            data_file.save(update_fields=[
                'vector_store_file_id', 
                'vector_store_status', 
                'vector_store_processed_at'
            ])
            logger.info(f"File {file_id} added to vector store with ID: {result.get('file_id')}")
            return {
                "success": True,
                "file_id": result.get('file_id')
            }
        else:
            # Update file with error
            data_file.vector_store_status = 'failed'
            data_file.save(update_fields=['vector_store_status'])
            logger.error(f"Error adding file to vector store: {result.get('error')}")
            return {
                "success": False,
                "error": result.get('error')
            }
            
    except Exception as e:
        import traceback
        logger.error(f"Error processing file for vector store: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Try to update file status if possible
        try:
            data_file = DataFile.objects.get(id=file_id)
            data_file.vector_store_status = 'failed'
            data_file.save(update_fields=['vector_store_status'])
        except:
            pass
            
        return {
            "success": False,
            "error": str(e)
        } 