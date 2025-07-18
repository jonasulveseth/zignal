"""
Service for handling OpenAI integrations for companies
"""
import logging
import os
import json
from django.conf import settings
from openai import OpenAI
from agents.services.openai_service import OpenAIService

logger = logging.getLogger(__name__)

class CompanyOpenAIService:
    """
    Service for handling OpenAI integrations for companies
    """
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.openai_service = OpenAIService()
    
    def setup_company_ai(self, company):
        """
        Set up OpenAI resources for a new company
        - Creates a vector store (if supported by API version)
        - Creates an assistant with file search capabilities
        - Uses OpenAI's native file handling system
        
        Args:
            company: Company model instance
            
        Returns:
            dict: Information about created resources
        """
        try:
            logger.info(f"Setting up OpenAI resources for company: {company.name} (ID: {company.id})")
            
            # Check if API key is valid and not a placeholder
            if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY.startswith("your_") or len(settings.OPENAI_API_KEY) < 20:
                logger.error(f"Invalid OpenAI API key format: {settings.OPENAI_API_KEY[:10]}...")
                return {
                    "success": False,
                    "error": "Invalid API key format. Please configure a valid OpenAI API key."
                }
            
            # Create a vector store for the company if supported
            vector_store_id = None
            try:
                # Check if vector_stores is available directly on the client
                has_vector_stores = hasattr(self.client, 'vector_stores')
                if has_vector_stores:
                    # Create a vector store
                    vector_store = self.client.vector_stores.create(
                        name=f"{company.name} Vector Store"
                    )
                    vector_store_id = vector_store.id
                    logger.info(f"Created vector store for company {company.name}: {vector_store_id}")
                else:
                    logger.warning("Vector stores not supported in this OpenAI API version. Falling back to basic assistant.")
                    vector_store_id = f"assistant_files_{company.id}"
            except Exception as e:
                logger.error(f"Error creating vector store: {str(e)}")
                vector_store_id = f"assistant_files_{company.id}"
            
            # Create an assistant with file search capabilities if vector store was created
            try:
                assistant_args = {
                    "name": f"{company.name} Assistant",
                    "description": f"AI assistant for {company.name}",
                    "instructions": f"You are an AI assistant for {company.name}. Your role is to help with company-related tasks and queries.",
                    "model": settings.OPENAI_MODEL,
                    "metadata": {
                        "company_id": str(company.id),
                        "company_name": company.name
                    }
                }
                
                # Add file search capability if we have a valid vector store ID
                if vector_store_id and not vector_store_id.startswith("assistant_files_"):
                    assistant_args["tools"] = [{"type": "file_search"}]
                    assistant_args["tool_resources"] = {
                        "file_search": {
                            "vector_store_ids": [vector_store_id]
                        }
                    }
                    assistant_args["instructions"] += " You can search through documents that have been uploaded."
                
                # Create the assistant
                assistant = self.client.beta.assistants.create(**assistant_args)
                logger.info(f"Created assistant for company {company.name}: {assistant.id}")
                
                logger.info(f"Successfully created OpenAI resources for company: {company.name}")
                
                return {
                    "success": True,
                    "assistant_id": assistant.id,
                    "vector_store_id": vector_store_id
                }
            except Exception as e:
                logger.error(f"Error creating assistant: {str(e)}")
                return {
                    "success": False,
                    "error": f"Error code: {getattr(e, 'status_code', 'unknown')} - {str(e)}"
                }
            
        except Exception as e:
            logger.error(f"Error setting up OpenAI resources for company {company.name}: {str(e)}")
            return {
                "success": False,
                "error": f"Error code: {getattr(e, 'status_code', 'unknown')} - {str(e)}"
            }
    
    def add_file_to_vector_store(self, company, file_path, file_name=None):
        """
        Add a file to the company's vector store for retrieval
        
        Args:
            company: Company model instance
            file_path: Path to the file to add
            file_name: Optional name for the file (defaults to filename from path)
            
        Returns:
            dict: Information about the operation
        """
        if not company.openai_assistant_id:
            return {
                "success": False,
                "error": "Company does not have an OpenAI assistant configured"
            }
        
        try:
            # If no file_name provided, use the basename from the path
            if not file_name:
                file_name = os.path.basename(file_path)
                
            # Upload the file to OpenAI
            with open(file_path, "rb") as file:
                file_upload = self.client.files.create(
                    file=file,
                    purpose="assistants"
                )
            logger.info(f"Uploaded file {file_name} to OpenAI with ID: {file_upload.id}")
            
            # Check if we have a proper vector store ID (not a placeholder) and vector stores are supported
            if (company.openai_vector_store_id and 
                not company.openai_vector_store_id.startswith("assistant_files_") and 
                hasattr(self.client, 'vector_stores')):
                try:
                    # Create a file batch with the uploaded file
                    file_batch = self.client.vector_stores.file_batches.create(
                        vector_store_id=company.openai_vector_store_id,
                        file_ids=[file_upload.id]
                    )
                    logger.info(f"Added file to vector store batch: {file_batch.id}")
                    
                    return {
                        "success": True,
                        "file_id": file_upload.id,
                        "file_batch_id": file_batch.id
                    }
                except Exception as e:
                    logger.error(f"Error adding file to vector store: {str(e)}")
                    # Continue to try attaching directly to assistant as fallback
            
            # If vector store wasn't available or attachment failed, try to create a thread and attach the file
            try:
                # Create a thread to attach the file to
                thread = self.client.beta.threads.create()
                
                # Add a message with the file attachment
                message = self.client.beta.threads.messages.create(
                    thread_id=thread.id,
                    role="user",
                    content="This document contains important information.",
                    attachments=[
                        {"file_id": file_upload.id, "tools": [{"type": "file_search"}]}
                    ]
                )
                logger.info(f"Created thread with file attachment: {thread.id}")
                
                return {
                    "success": True,
                    "file_id": file_upload.id,
                    "thread_id": thread.id,
                    "message_id": message.id
                }
            except Exception as e:
                logger.error(f"Error creating thread with file attachment: {str(e)}")
                return {
                    "success": False,
                    "error": str(e)
                }
            
        except Exception as e:
            logger.error(f"Error uploading file for company {company.name}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def add_text_to_vector_store(self, company, text, file_name="company_data.txt"):
        """
        Add text content to the company's vector store by creating a temporary file
        
        Args:
            company: Company model instance
            text: Text content to add
            file_name: Name for the temporary file
            
        Returns:
            dict: Information about the operation
        """
        if not company.openai_assistant_id:
            return {
                "success": False,
                "error": "Company does not have an OpenAI assistant configured"
            }
        
        try:
            # Create a temporary file
            temp_file_path = os.path.join("/tmp", file_name)
            with open(temp_file_path, "w") as file:
                file.write(text)
                
            # Add the file to the vector store
            result = self.add_file_to_vector_store(company, temp_file_path, file_name)
            
            # Clean up the temporary file
            os.remove(temp_file_path)
            
            return result
            
        except Exception as e:
            logger.error(f"Error adding text for company {company.name}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def add_s3_file_to_vector_store(self, company, s3_bucket, s3_key, file_name=None, metadata=None):
        """
        Add a file directly from S3 to the company's vector store without downloading it first
        
        Args:
            company: Company model instance
            s3_bucket: S3 bucket name
            s3_key: S3 object key
            file_name: Optional name for the file (defaults to the last part of S3 key)
            metadata: Optional metadata to include with the file
            
        Returns:
            dict: Information about the operation
        """
        if not company.openai_assistant_id:
            return {
                "success": False,
                "error": "Company does not have an OpenAI assistant configured"
            }
        
        logger.info(f"Adding S3 file to vector store - bucket: {s3_bucket}, key: {s3_key}")
        
        try:
            # Handle S3 path issues by trying multiple path variations
            # This handles the case of double 'media/' prefixes or missing 'media/' prefix
            import boto3
            import tempfile
            from django.conf import settings
            from botocore.exceptions import ClientError
            
            # If no file_name provided, use the basename from the key
            if not file_name:
                file_name = os.path.basename(s3_key)
            
            # Create S3 client
            s3 = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME
            )
            
            # Try different path variations to make sure we find the file
            keys_to_try = [s3_key]
            
            # Add check for double datasilo prefix
            if 'datasilo/' in s3_key:
                # Check for double datasilo prefix
                if 'datasilo/datasilo/' in s3_key:
                    # Already has double prefix, add a version without it
                    fixed_key = s3_key.replace('datasilo/datasilo/', 'datasilo/')
                    keys_to_try.append(fixed_key)
                    logger.info(f"Added path with fixed datasilo prefix: {fixed_key}")
                else:
                    # Has single prefix, try with double prefix
                    doubled_key = s3_key.replace('datasilo/', 'datasilo/datasilo/')
                    keys_to_try.append(doubled_key)
                    logger.info(f"Added path with doubled datasilo prefix: {doubled_key}")
            
            # If the key doesn't start with media/, try with it
            if not s3_key.startswith('media/'):
                keys_to_try.append(f"media/{s3_key}")
            
            # If the key starts with media/, try without it
            if s3_key.startswith('media/'):
                keys_to_try.append(s3_key[6:])  # Remove 'media/' prefix
            
            # Also try media/media/ prefix (double media)
            if not s3_key.startswith('media/media/') and not s3_key.startswith('media/'):
                keys_to_try.append(f"media/media/{s3_key}")
                
            # Try datasilo prefix combinations with media
            if 'datasilo/' in s3_key and not s3_key.startswith('media/'):
                keys_to_try.append(f"media/datasilo/datasilo/{s3_key.split('datasilo/')[1]}")
                keys_to_try.append(f"media/datasilo/{s3_key.split('datasilo/')[1]}")
            
            # Remove duplicates but preserve order
            keys_to_try = list(dict.fromkeys(keys_to_try))
            
            # Try to find the correct key in S3
            working_key = None
            for test_key in keys_to_try:
                try:
                    # Check if the object exists
                    s3.head_object(Bucket=s3_bucket, Key=test_key)
                    working_key = test_key
                    logger.info(f"Found existing S3 object with key: {test_key}")
                    break
                except ClientError:
                    logger.info(f"S3 object not found with key: {test_key}")
                    continue
            
            if not working_key:
                logger.error(f"Could not find S3 object with any of these keys: {keys_to_try}")
                return {
                    "success": False,
                    "error": f"S3 file not found: {s3_key}"
                }
            
            # Now we have the correct S3 key, continue with OpenAI integration
            # Use the working_key instead of original s3_key
            logger.info(f"Using S3 key: {working_key} (original: {s3_key})")
            
            # We need to use an intermediate step with a temporary file
            # because OpenAI's API doesn't support direct S3 upload yet
            temp_file = tempfile.NamedTemporaryFile(delete=False)
            try:
                # Download the file to a temporary location using the working key
                logger.info(f"Downloading from S3 to temp file: {temp_file.name}")
                s3.download_file(s3_bucket, working_key, temp_file.name)
                
                # Close the file to ensure it's fully written
                temp_file.close()
                
                # Add metadata to include with file
                file_metadata = metadata or {}
                if not file_metadata:
                    file_metadata = {
                        "source": "s3",
                        "bucket": s3_bucket,
                        "key": working_key,
                        "original_key": s3_key,
                    }
                
                # Now upload the file to OpenAI
                result = self.add_file_to_vector_store(company, temp_file.name, file_name)
                
                # Add metadata to the result
                if result.get("success") and result.get("file_id"):
                    # Try to update the file metadata - this is a beta feature
                    if hasattr(self.client, 'files') and hasattr(self.client.files, 'update'):
                        try:
                            self.client.files.update(
                                file_id=result.get("file_id"),
                                metadata=file_metadata
                            )
                            logger.info(f"Updated file metadata for file ID: {result.get('file_id')}")
                        except Exception as e:
                            logger.warning(f"Could not update file metadata (likely not supported): {str(e)}")
                
                return result
                
            finally:
                # Clean up temp file
                try:
                    import os
                    os.unlink(temp_file.name)
                    logger.info(f"Deleted temporary file: {temp_file.name}")
                except Exception as e:
                    logger.warning(f"Error deleting temporary file: {str(e)}")
            
        except Exception as e:
            logger.error(f"Error adding S3 file to vector store: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            } 