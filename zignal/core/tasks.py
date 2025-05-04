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
    Process a file for the OpenAI Vector Store
    
    Args:
        file_id (int): ID of the DataFile to process
        max_retries (int): Maximum number of retry attempts
        
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
    
    # Add debugging to detect duplicate calls
    print(f"====== STARTING VECTOR STORE PROCESSING FOR FILE ID: {file_id} ======")
    
    # Force garbage collection to free up memory
    gc.collect()
    
    retry_count = 0
    while retry_count <= max_retries:
        try:
            logger.info(f"Processing file for vector store: {file_id} (Attempt {retry_count + 1})")
            
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
                print(f"====== SKIPPING - ALREADY PROCESSED: File ID {file_id} already has vector store ID: {data_file.vector_store_file_id} ======")
                return {
                    "success": True,
                    "message": "File already processed",
                    "file_id": data_file.vector_store_file_id
                }
            
            # If this file was already being processed, we may have a duplicate call
            if data_file.vector_store_status == 'processing':
                logger.warning(f"File ID {file_id} was already in 'processing' state - possible duplicate call!")
                print(f"====== WARNING - DUPLICATE CALL DETECTED: File ID {file_id} already in 'processing' state ======")
                # Continue processing anyway in case the previous attempt failed
                
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
            
            # Check what type of storage is being used
            is_s3_storage = False
            
            # Check if default_storage is S3Boto3Storage or MediaStorage
            storage_class_name = default_storage.__class__.__name__
            if hasattr(default_storage, '_wrapped'):
                storage_class_name = default_storage._wrapped.__class__.__name__
            
            is_s3_storage = 'S3' in storage_class_name or 'Boto' in storage_class_name or 'Media' in storage_class_name
            logger.info(f"Using S3 storage: {is_s3_storage} (Storage class: {storage_class_name})")
            
            # Also check environment variables as a backup check
            if not is_s3_storage and os.environ.get('USE_S3') == 'TRUE':
                logger.info("Forcing S3 detection from USE_S3 environment variable")
                is_s3_storage = True
            
            # Get AWS credentials 
            aws_access_key = os.environ.get('AWS_ACCESS_KEY_ID')
            aws_secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
            aws_region = os.environ.get('AWS_S3_REGION_NAME', 'eu-west-1')
            aws_bucket = os.environ.get('AWS_STORAGE_BUCKET_NAME', 'zignalse')
            aws_location = os.environ.get('AWS_LOCATION', 'media')
            
            logger.info(f"AWS settings: bucket={aws_bucket}, region={aws_region}, location={aws_location}")
            
            # Create a direct path for files using S3 storage class if available
            direct_s3_access = False
            s3_storage = None
            s3_bucket = None
            s3_key = None
            
            if is_s3_storage:
                try:
                    # Get the S3 storage class - try from settings or use default_storage
                    if hasattr(settings, 'MEDIA_STORAGE_CLASS'):
                        s3_storage = settings.MEDIA_STORAGE_CLASS()
                    elif hasattr(default_storage, '_wrapped') and 'S3' in default_storage._wrapped.__class__.__name__:
                        s3_storage = default_storage._wrapped
                    
                    if s3_storage:
                        # Get the original file path (key)
                        original_key = data_file.file.name
                        logger.info(f"Original file path: {original_key}")
                        
                        # Generate all possible S3 key formats to try
                        possible_keys = []
                        
                        # 1. Original key
                        possible_keys.append(original_key)
                        
                        # 2. With media/ prefix if not already there
                        if not original_key.startswith('media/'):
                            possible_keys.append(f"media/{original_key}")
                        
                        # 3. Without media/ prefix if it's there
                        if original_key.startswith('media/'):
                            possible_keys.append(original_key[6:])  # Remove 'media/'
                        
                        # 4. Try with AWS_LOCATION prefix
                        if aws_location and not original_key.startswith(f"{aws_location}/"):
                            possible_keys.append(f"{aws_location}/{original_key}")
                            
                            # 5. Also try with location but without media/ if it has that
                            if original_key.startswith('media/'):
                                possible_keys.append(f"{aws_location}/{original_key[6:]}")
                        
                        # Remove duplicates but preserve order
                        possible_keys = list(dict.fromkeys(possible_keys))
                        logger.info(f"Will try these S3 keys for direct access: {possible_keys}")
                        
                        # First check which key exists
                        found_key = None
                        for key in possible_keys:
                            try:
                                if s3_storage.exists(key):
                                    found_key = key
                                    logger.info(f"Found existing S3 object with key: {key}")
                                    break
                            except Exception as e:
                                logger.warning(f"Error checking if key exists: {key} - {str(e)}")
                        
                        if found_key:
                            s3_key = found_key
                            s3_bucket = aws_bucket
                            direct_s3_access = True
                            logger.info(f"Using direct S3 access with bucket={s3_bucket}, key={s3_key}")
                        else:
                            # If we couldn't find the file with the storage class, try direct boto3
                            logger.warning("File not found with storage.exists, trying direct boto3 access")
                            import boto3
                            s3_client = boto3.client(
                                's3',
                                aws_access_key_id=aws_access_key,
                                aws_secret_access_key=aws_secret_key,
                                region_name=aws_region
                            )
                            
                            # Try each key with boto3
                            for key in possible_keys:
                                try:
                                    # Use head_object to check if key exists
                                    s3_client.head_object(Bucket=aws_bucket, Key=key)
                                    found_key = key
                                    logger.info(f"Found existing S3 object with boto3 key: {key}")
                                    break
                                except Exception as e:
                                    logger.warning(f"Boto3 head_object failed for key: {key} - {str(e)}")
                            
                            if found_key:
                                s3_key = found_key
                                s3_bucket = aws_bucket
                                direct_s3_access = True
                                logger.info(f"Using direct boto3 S3 access with bucket={s3_bucket}, key={s3_key}")
                            else:
                                logger.error("Could not find file in S3 with any path")
                                # We'll fall back to download method below
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
                "source": "s3" if is_s3_storage else "local"
            }
            
            # The rest of the processing function continues with either direct S3 access or file download
            # Implement the rest of the functionality or call to another function
            
            # We can skip downloading if using direct S3 access
            if not direct_s3_access:
                # Download the file to a temporary location
                temp_file = None
                file_ext = os.path.splitext(data_file.file.name)[1]
                try:
                    temp_file = tempfile.NamedTemporaryFile(suffix=file_ext, delete=False)
                    
                    # Download the file content
                    if is_s3_storage:
                        # Use boto3 to download from S3
                        import boto3
                        s3_client = boto3.client(
                            's3',
                            aws_access_key_id=aws_access_key,
                            aws_secret_access_key=aws_secret_key,
                            region_name=aws_region
                        )
                        
                        # Determine the correct S3 key path
                        file_key = data_file.file.name
                        
                        # List of possible S3 key formats to try
                        possible_keys = []
                        
                        # Start with the original key from the file
                        possible_keys.append(file_key)
                        
                        # Check for double datasilo prefix case
                        if 'datasilo/datasilo/' in file_key:
                            # Add a version without the doubled prefix
                            fixed_key = file_key.replace('datasilo/datasilo/', 'datasilo/')
                            possible_keys.append(fixed_key)
                            logger.info(f"Detected duplicate datasilo prefix, adding alternative path: {fixed_key}")
                        elif 'datasilo/' in file_key and not file_key.startswith('datasilo/datasilo/'):
                            # Try with doubled prefix if we have a single one
                            doubled_key = file_key.replace('datasilo/', 'datasilo/datasilo/')
                            possible_keys.append(doubled_key)
                            logger.info(f"Adding path with doubled datasilo prefix: {doubled_key}")
                        
                        # Add common variations
                        if file_key.startswith('media/'):
                            possible_keys.append(file_key[6:])  # Remove 'media/'
                        
                        # If AWS_LOCATION is set, try with that prefix
                        if aws_location and not file_key.startswith(f"{aws_location}/"):
                            possible_keys.append(f"{aws_location}/{file_key}")
                            
                            # Also try with the location but without media/ if it starts with that
                            if file_key.startswith('media/'):
                                possible_keys.append(f"{aws_location}/{file_key[6:]}")
                        
                        # Remove duplicates but preserve order
                        possible_keys = list(dict.fromkeys(possible_keys))
                        logger.info(f"Will try these S3 paths: {possible_keys}")
                        
                        # Try each possible key until one works
                        download_success = False
                        last_error = None
                        
                        for key in possible_keys:
                            try:
                                logger.info(f"Attempting to download with key: {key}")
                                s3_client.download_file(aws_bucket, key, temp_file.name)
                                logger.info(f"Successfully downloaded using key: {key}")
                                
                                # Update the file record with the correct path if it's different from what we have
                                if key != file_key:
                                    logger.info(f"Updating file record with correct path: {key}")
                                    data_file.file.name = key
                                    data_file.save(update_fields=['file'])
                                
                                download_success = True
                                break
                            except Exception as e:
                                logger.warning(f"Failed to download with key {key}: {str(e)}")
                                last_error = e
                        
                        # If all attempts failed, raise the last error
                        if not download_success:
                            logger.error(f"All download attempts failed. Last error: {str(last_error)}")
                            
                            # Try listing the objects in the bucket to debug
                            try:
                                # Check if there's anything in the bucket with a similar path
                                prefix = file_key.split('/')
                                if len(prefix) > 1:
                                    search_prefix = '/'.join(prefix[:-1]) + '/'
                                else:
                                    search_prefix = ''
                                    
                                logger.info(f"Listing objects with prefix: {search_prefix}")
                                response = s3_client.list_objects_v2(
                                    Bucket=aws_bucket,
                                    Prefix=search_prefix,
                                    MaxKeys=10
                                )
                                
                                if response.get('KeyCount', 0) > 0:
                                    keys = [obj['Key'] for obj in response.get('Contents', [])]
                                    logger.info(f"Found {len(keys)} objects with similar prefix: {keys}")
                                    
                                    # Find the closest match by filename
                                    filename = os.path.basename(file_key)
                                    closest_match = None
                                    for key in keys:
                                        if filename in key:
                                            closest_match = key
                                            break
                                    
                                    if closest_match:
                                        logger.info(f"Found closest match: {closest_match}, attempting download")
                                        try:
                                            s3_client.download_file(aws_bucket, closest_match, temp_file.name)
                                            logger.info(f"Successfully downloaded using closest match: {closest_match}")
                                            
                                            # Update the file record with the correct path
                                            logger.info(f"Updating file record with closest match path: {closest_match}")
                                            data_file.file.name = closest_match
                                            data_file.save(update_fields=['file'])
                                            
                                            download_success = True
                                        except Exception as e:
                                            logger.error(f"Failed to download closest match: {str(e)}")
                                else:
                                    logger.warning(f"No objects found with prefix: {search_prefix}")
                            except Exception as list_err:
                                logger.error(f"Error listing objects: {str(list_err)}")
                            
                            if not download_success:
                                raise last_error
                    else:
                        # For local storage, just open and read the file
                        with default_storage.open(data_file.file.name, 'rb') as f:
                            temp_file.write(f.read())
                    
                    temp_file.close()
                    
                    # Verify file was downloaded and has content
                    if os.path.getsize(temp_file.name) == 0:
                        logger.error(f"Downloaded file is empty: {temp_file.name}")
                        DataFile.objects.filter(id=file_id).update(vector_store_status='failed')
                        return {
                            "success": False,
                            "error": "Downloaded file is empty"
                        }
                    
                    logger.info(f"File downloaded successfully to {temp_file.name} ({os.path.getsize(temp_file.name)} bytes)")
                    
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
                if retry_count < max_retries:
                    retry_count += 1
                    retry_delay = 120 * (2 ** retry_count)  # 120s, 240s, 480s
                    logger.info(f"Temporary error detected. Retrying in {retry_delay} seconds... (Attempt {retry_count + 1})")
                    time.sleep(retry_delay)
                    continue  # Try again
                
            # Force garbage collection
            gc.collect()
            
            return {
                "success": False,
                "error": str(e)
            }
            
    # Should not get here, but just in case
    return {
        "success": False,
        "error": "Exceeded maximum number of retry attempts"
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