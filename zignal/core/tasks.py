from celery import shared_task
import logging
from django.utils import timezone
from projects.models import Project, UserProjectRelation
from datasilo.models import DataSilo, DataFile
import time
import os
import gc

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

@shared_task(bind=True, max_retries=3, rate_limit='5/m')
def process_file_for_vector_store(self, file_id):
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
    
    # Configure Redis SSL settings for this task
    try:
        import redis
        import ssl
        from redis.connection import ConnectionPool
        
        # Check if we're in a production environment with SSL Redis
        redis_url = os.environ.get('REDIS_URL', '')
        if redis_url.startswith('rediss://'):
            # Configure SSL settings for Redis
            ssl_settings = {
                'ssl_cert_reqs': ssl.CERT_NONE,
                'ssl_check_hostname': False
            }
            
            # Apply SSL settings to the global connection pool
            default_connection_pool = getattr(ConnectionPool, '_connection_pool_cache', {})
            for url, pool in default_connection_pool.items():
                if url.startswith('rediss://'):
                    pool.connection_kwargs.update(ssl_settings)
                    
            # Create a test connection to ensure settings are applied
            test_client = redis.Redis.from_url(
                redis_url,
                ssl_cert_reqs=None,
                ssl_check_hostname=False
            )
            test_client.ping()
            logger.info("Redis SSL settings configured successfully for vector store task")
    except Exception as e:
        logger.error(f"Error configuring Redis SSL: {str(e)}")
    
    # Force garbage collection to free up memory
    gc.collect()
    
    try:
        logger.info(f"Processing file for vector store: {file_id}")
        
        # Get the file with minimal fields to save memory
        data_file = DataFile.objects.filter(id=file_id).select_related('data_silo', 'project', 'company').first()
        
        if not data_file:
            logger.error(f"File with ID {file_id} not found")
            return {
                "success": False,
                "error": f"File with ID {file_id} not found"
            }
            
        # Check if already processed
        if data_file.vector_store_file_id:
            logger.info(f"File already has a vector store ID: {data_file.vector_store_file_id}")
            return {
                "success": True,
                "message": "File already processed",
                "file_id": data_file.vector_store_file_id
            }
        
        # Update status
        DataFile.objects.filter(id=file_id).update(vector_store_status='processing')
        
        # Try to get company
        company = None
        if hasattr(data_file, 'company') and data_file.company:
            company = data_file.company
        elif hasattr(data_file, 'project') and data_file.project and data_file.project.company:
            company = data_file.project.company
        elif hasattr(data_file, 'data_silo') and data_file.data_silo:
            if data_file.data_silo.company:
                company = data_file.data_silo.company
            elif data_file.data_silo.project and data_file.data_silo.project.company:
                company = data_file.data_silo.project.company
        
        if not company:
            logger.error(f"No company found for file {file_id}")
            DataFile.objects.filter(id=file_id).update(vector_store_status='failed')
            return {
                "success": False,
                "error": "No company found for file"
            }
        
        # Check if company has a vector store
        if not company.openai_vector_store_id:
            logger.warning(f"Company {company.name} has no vector store ID. Creating one...")
            
            try:
                # Create vector store if not exists
                from companies.services.openai_service import CompanyOpenAIService
                openai_service = CompanyOpenAIService()
                setup_result = openai_service.setup_company_ai(company)
                
                if setup_result.get('success') and setup_result.get('vector_store_id'):
                    Company.objects.filter(id=company.id).update(
                        openai_vector_store_id=setup_result.get('vector_store_id'),
                        openai_assistant_id=setup_result.get('assistant_id') or company.openai_assistant_id
                    )
                    # Refresh company from database
                    company = Company.objects.get(id=company.id)
                    logger.info(f"Created vector store for company: {company.openai_vector_store_id}")
                else:
                    logger.error(f"Failed to create vector store: {setup_result.get('error')}")
                    DataFile.objects.filter(id=file_id).update(vector_store_status='failed')
                    return {
                        "success": False,
                        "error": f"Failed to create vector store: {setup_result.get('error')}"
                    }
            except Exception as e:
                logger.error(f"Error creating vector store: {str(e)}")
                DataFile.objects.filter(id=file_id).update(vector_store_status='failed')
                return {
                    "success": False,
                    "error": f"Error creating vector store: {str(e)}"
                }
        
        # Import OpenAI service
        try:
            from companies.services.openai_service import CompanyOpenAIService
            openai_service = CompanyOpenAIService()
        except ImportError as e:
            logger.error(f"OpenAI service not available: {str(e)}")
            DataFile.objects.filter(id=file_id).update(vector_store_status='failed')
            return {
                "success": False,
                "error": f"OpenAI service not available: {str(e)}"
            }
        
        # Process the file
        file_path = data_file.file.path
        
        # Check if file exists and is accessible
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            DataFile.objects.filter(id=file_id).update(vector_store_status='failed')
            return {
                "success": False,
                "error": "File not found on disk"
            }
        
        # Check file size limit (OpenAI has 512MB limit)
        max_file_size = 512 * 1024 * 1024  # 512MB in bytes
        file_size = os.path.getsize(file_path)
        if file_size > max_file_size:
            logger.error(f"File too large: {file_path} ({file_size} bytes)")
            DataFile.objects.filter(id=file_id).update(vector_store_status='failed')
            return {
                "success": False,
                "error": "File too large for OpenAI API (max 512MB)"
            }
            
        # Check if OpenAI API key is configured
        if not settings.OPENAI_API_KEY or len(settings.OPENAI_API_KEY) < 10:
            logger.error("OpenAI API key not configured properly")
            DataFile.objects.filter(id=file_id).update(vector_store_status='failed')
            return {
                "success": False,
                "error": "OpenAI API key not configured"
            }
        
        # Force garbage collection before heavy operation
        gc.collect()
        
        # Upload file to vector store
        result = openai_service.add_file_to_vector_store(
            company,
            file_path,
            data_file.name
        )
        
        if result.get('success'):
            # Update file with vector store ID
            DataFile.objects.filter(id=file_id).update(
                vector_store_file_id=result.get('file_id'),
                vector_store_status='processed',
                vector_store_processed_at=timezone.now()
            )
            logger.info(f"File {file_id} added to vector store with ID: {result.get('file_id')}")
            
            # Force garbage collection
            gc.collect()
            
            return {
                "success": True,
                "file_id": result.get('file_id')
            }
        else:
            # Update file with error
            DataFile.objects.filter(id=file_id).update(vector_store_status='failed')
            logger.error(f"Error adding file to vector store: {result.get('error')}")
            
            # Check if this is a rate limit error or temporary issue that warrants a retry
            error_msg = str(result.get('error', '')).lower()
            if 'rate limit' in error_msg or 'timeout' in error_msg or 'connection' in error_msg:
                # Exponential backoff for retries
                retry_in = 60 * (2 ** self.request.retries)  # 60s, 120s, 240s
                logger.info(f"Temporary error detected. Retrying in {retry_in} seconds...")
                self.retry(countdown=retry_in)
            
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
            DataFile.objects.filter(id=file_id).update(vector_store_status='failed')
        except Exception:
            pass
            
        # Check if this is a temporary error worth retrying
        error_message = str(e).lower()
        if 'timeout' in error_message or 'connection' in error_message or 'memory' in error_message:
            # Retry with backoff
            retry_in = 120 * (2 ** self.request.retries)  # 120s, 240s, 480s
            logger.info(f"Temporary error detected. Retrying in {retry_in} seconds...")
            self.retry(countdown=retry_in)
            
        # Force garbage collection
        gc.collect()
        
        return {
            "success": False,
            "error": str(e)
        } 