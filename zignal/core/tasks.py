from celery import shared_task
import logging
from django.utils import timezone
from projects.models import Project, UserProjectRelation
from datasilo.models import DataSilo, DataFile
import time
import os
import gc
import tempfile
from django.core.files.storage import default_storage

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
    import tempfile
    from django.core.files.storage import default_storage
    
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
        
        # Log file information
        logger.info(f"File name: {data_file.name}, Storage path: {data_file.file.name}")
        
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
        
        # Better S3 detection method
        using_s3 = False
        
        # Get AWS credentials first (we'll need these throughout the function)
        aws_access_key = os.environ.get('AWS_ACCESS_KEY_ID')
        aws_secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
        aws_region = os.environ.get('AWS_S3_REGION_NAME', 'eu-west-1')
        aws_bucket = os.environ.get('AWS_STORAGE_BUCKET_NAME', 'zignalse')
        aws_location = os.environ.get('AWS_LOCATION', 'media')
        
        try:
            # Use URL method which is more reliable
            test_url = default_storage.url('test-path')
            using_s3 = 's3.amazonaws.com' in test_url or aws_bucket in test_url
            logger.info(f"S3 detection via URL: {using_s3}")
        except Exception as e:
            # Fallback to traditional method
            storage_type = default_storage.__class__.__name__
            using_s3 = 'S3' in storage_type or 'Boto' in storage_type
            logger.info(f"S3 detection via class name: {using_s3}, Storage type: {storage_type}")
        
        # Hardcode for production if we're pretty sure S3 is being used
        if not settings.DEBUG and os.environ.get('USE_S3') == 'TRUE':
            logger.info("Forcing S3 detection based on environment variables")
            using_s3 = True
        
        # If not using S3, check if we should be (try to get direct S3 storage)
        if not using_s3 and hasattr(settings, 'MEDIA_STORAGE_CLASS'):
            logger.info("Detected MEDIA_STORAGE_CLASS in settings, will use for direct S3 operations")
            using_s3 = True
        
        # Create a direct path for files
        # Using MEDIA_STORAGE_CLASS to directly access the file if available
        direct_s3_access = False
        s3_storage = None
        s3_bucket = None
        s3_key = None
        
        if using_s3 and hasattr(settings, 'MEDIA_STORAGE_CLASS'):
            try:
                # Get an instance of the storage class
                s3_storage = settings.MEDIA_STORAGE_CLASS()
                
                # Get the file path (which is already the key)
                s3_key = data_file.file.name
                if aws_location and not s3_key.startswith(f"{aws_location}/"):
                    s3_key = f"{aws_location}/{s3_key}"
                
                s3_bucket = aws_bucket
                
                # Check if we can access the file directly
                direct_s3_access = True
                logger.info(f"Will use direct S3 access with bucket={s3_bucket}, key={s3_key}")
            except Exception as e:
                logger.error(f"Error setting up direct S3 access: {str(e)}")
                direct_s3_access = False
        
        # Create metadata for the file
        metadata = {
            "file_id": str(data_file.id),
            "file_name": data_file.name,
            "file_type": data_file.file_type,
            "data_silo": data_file.data_silo.name if data_file.data_silo else None,
            "company": company.name if company else None,
            "uploaded_at": str(data_file.created_at),
            "source": "s3" if using_s3 else "local"
        }
        
        # We can skip downloading if using direct S3 access
        if not direct_s3_access:
            # Get file path - need different approaches for local vs S3 storage
            temp_file = None
            file_ext = os.path.splitext(data_file.file.name)[1]
            try:
                temp_file = tempfile.NamedTemporaryFile(suffix=file_ext, delete=False)
                # ... [existing file download code] ...
                
                # Process file for vector store
                result = process_file_for_vector_store_core(file_path=temp_file.name, data_file=data_file, metadata=metadata)
            finally:
                # Clean up temporary file
                if temp_file is not None and os.path.exists(temp_file.name):
                    os.unlink(temp_file.name)
                    logger.info("Temporary file deleted")
        else:
            # Use direct S3 access - no need to download file
            result = process_file_for_vector_store_core(
                file_path=None,  # No local file
                data_file=data_file,
                metadata=metadata,
                s3_bucket=s3_bucket,
                s3_key=s3_key
            )
        
        return result
    except Exception as e:
        import traceback
        logger.error(f"Error processing file for vector store: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Clean up temp file if it exists
        if 'temp_file' in locals() and temp_file and os.path.exists(temp_file.name):
            try:
                os.unlink(temp_file.name)
                logger.info(f"Cleaned up temporary file after error: {temp_file.name}")
            except Exception:
                pass
        
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

def process_file_for_vector_store_core(file_path=None, data_file=None, metadata=None, s3_bucket=None, s3_key=None):
    """Core function to process a file for the vector store.
    Can work with either a local file_path OR an S3 file (bucket and key).
    """
    from datasilo.models import DataFile
    from django.utils import timezone
    from companies.services.openai_service import CompanyOpenAIService
    from django.conf import settings
    import gc
    import os
    
    company = data_file.company
    file_id = data_file.id
    logger.info(f"Core processing function for file: {file_id}, S3: {s3_bucket is not None and s3_key is not None}")
    
    # Validate params - need either file_path OR (s3_bucket AND s3_key)
    if not file_path and not (s3_bucket and s3_key):
        logger.error("Neither local file path nor S3 information provided")
        DataFile.objects.filter(id=file_id).update(vector_store_status='failed')
        return {
            "success": False,
            "error": "No file source provided"
        }
    
    # If we're using local file, validate it exists
    if file_path and not os.path.exists(file_path):
        logger.error(f"File not found at path: {file_path}")
        DataFile.objects.filter(id=file_id).update(vector_store_status='failed')
        return {
            "success": False,
            "error": "File not found on disk"
        }
    
    # If using local file, check file size limit (OpenAI has 512MB limit)
    if file_path:
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
    
    try:
        # Create an instance of the OpenAI service
        openai_service = CompanyOpenAIService()
        
        # Upload file to vector store - which method depends on what we have
        if file_path:
            # Use local file path
            result = openai_service.add_file_to_vector_store(
                company,
                file_path,
                data_file.name
            )
        else:
            # Use S3 file directly
            result = openai_service.add_s3_file_to_vector_store(
                company,
                s3_bucket,
                s3_key,
                data_file.name,
                metadata
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
                # This should be handled by the retry mechanism in the outer function
                pass
            
            return {
                "success": False,
                "error": result.get('error')
            }
    except Exception as e:
        logger.error(f"Error in core processing: {str(e)}")
        DataFile.objects.filter(id=file_id).update(vector_store_status='failed')
        return {
            "success": False,
            "error": str(e)
        } 