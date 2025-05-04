"""
Task functions for the core app.
These were previously Celery tasks but have been converted to regular Python functions
for synchronous execution.
"""
import logging
from django.utils import timezone
import time
import os
import gc
import tempfile
from django.core.files.storage import default_storage

logger = logging.getLogger(__name__)

def sample_task(arg):
    """
    A sample task (previously a Celery task)
    """
    logger.info(f"Sample task executed with arg: {arg}")
    return f"Task completed with arg: {arg}"

def process_data(data_id):
    """
    Process data synchronously (previously a Celery task)
    """
    logger.info(f"Processing data with ID: {data_id}")
    # Add actual processing logic here
    return f"Data processing complete for ID: {data_id}"

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
    from projects.models import Project, UserProjectRelation
    from datasilo.models import DataSilo
    
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
            logger.debug(f"Debug mode enabled")
        
        return {
            "success": False,
            "error": str(e)
        }

def process_file_for_vector_store(file_id, max_retries=3):
    """
    Process a data file for the vector store
    """
    import os
    import tempfile
    import traceback
    import gc
    import time
    from django.utils import timezone
    from django.conf import settings
    from datasilo.models import DataFile
    import logging
    
    logger = logging.getLogger(__name__)
    logger.info(f"====== STARTING VECTOR STORE PROCESSING FOR FILE ID: {file_id} ======")
    
    # Track retries
    retry_count = 0
    last_error = None
    
    # Use cache to prevent duplicate processing
    from django.core.cache import cache
    processing_key = f"processing_file_{file_id}"
    
    # Check if this file is already being processed
    if cache.get(processing_key):
        logger.warning(f"File {file_id} is already being processed. Skipping duplicate processing.")
        return {"success": False, "error": "File is already being processed"}
    
    # Set a processing flag with timeout (10 minutes)
    cache.set(processing_key, True, 600)
    
    # Define temp_file here to make it available for cleanup in all code paths
    temp_file = None
    
    while retry_count <= max_retries:
        try:
            # Get the data file
            try:
                data_file = DataFile.objects.get(id=file_id)
            except DataFile.DoesNotExist:
                logger.error(f"File with ID {file_id} does not exist")
                cache.delete(processing_key)  # Release the lock
                return {"success": False, "error": "File not found"}
            
            # Update status to processing
            data_file.vector_store_status = 'processing'
            data_file.save(update_fields=['vector_store_status'])
            
            # Now call the core processing function
            # (Rest of the existing function code goes here)
            
            # Add debugging to detect duplicate calls
            logger.info(f"Processing file for vector store: {file_id} (Attempt {retry_count + 1})")
            
            # If successful, break out of the retry loop
            break
            
        except Exception as e:
            logger.error(f"Error processing file for vector store: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Clean up temp file if it exists
            if temp_file and os.path.exists(temp_file.name):
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
            last_error = e
            error_message = str(e).lower()
            if 'timeout' in error_message or 'connection' in error_message or 'memory' in error_message:
                # Retry with backoff
                if retry_count < max_retries:
                    retry_count += 1
                    retry_delay = 120 * (2 ** retry_count)  # 120s, 240s, 480s
                    logger.info(f"Temporary error detected. Retrying in {retry_delay} seconds... (Attempt {retry_count + 1})")
                    time.sleep(retry_delay)
                    continue  # Try again
            
            # If we get here, either it's not a temporary error or we're out of retries
            # Force garbage collection
            gc.collect()
            
            # Release the processing lock
            cache.delete(processing_key)
                
            return {
                "success": False,
                "error": str(e)
            }
    
    # Release the processing lock on success path
    cache.delete(processing_key)
    
    return {
        "success": True,
        "file_id": file_id
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
    
    logger = logging.getLogger(__name__)
    
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