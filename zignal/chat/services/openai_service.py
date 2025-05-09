"""
Service for handling OpenAI Assistant API interactions for chat
"""
import logging
import json
import time
from typing import Generator, Dict, Any
from django.conf import settings
import openai
from openai import OpenAI
from ..models import Thread, Message

logger = logging.getLogger(__name__)

class ChatOpenAIService:
    """
    Service for handling OpenAI Assistant API interactions for chat
    """
    
    def __init__(self):
        # Log OpenAI SDK version for debugging
        logger.info(f"Using OpenAI SDK version: {openai.__version__}")
        
        # Initialize client with or without beta version header based on SDK version
        try:
            self.client = OpenAI(
                api_key=settings.OPENAI_API_KEY,
                # Use Assistants API v2 if supported by this SDK version
                default_headers={"OpenAI-Beta": "assistants=v2"}
            )
            logger.info("Initialized OpenAI client with assistants=v2 header")
        except Exception as e:
            logger.warning(f"Error initializing with v2 header: {str(e)}. Falling back to standard client.")
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
    
    def create_thread(self, company) -> Dict[str, Any]:
        """
        Create a new thread for a company's assistant
        
        Args:
            company: Company model instance
            
        Returns:
            dict: Information about the created thread
        """
        try:
            if not company.openai_assistant_id:
                logger.error(f"Company {company.name} does not have OpenAI assistant ID configured")
                return {
                    "success": False,
                    "error": "Company does not have an OpenAI assistant configured"
                }
            
            logger.info(f"Attempting to create thread for company {company.name} with assistant ID: {company.openai_assistant_id}")
            
            # Create a thread directly without retry logic first
            try:
                thread = self.client.beta.threads.create()
                thread_id = thread.id
                logger.info(f"Successfully created thread with ID: {thread_id}")
                
                # Try retrieving the thread to confirm it exists
                self.client.beta.threads.retrieve(thread_id=thread_id)
                logger.info(f"Verified thread exists with ID: {thread_id}")
                
                return {
                    "success": True,
                    "thread_id": thread_id
                }
            except Exception as e:
                logger.error(f"Failed to create or verify thread: {str(e)}")
                return {
                    "success": False,
                    "error": f"Failed to create OpenAI thread: {str(e)}"
                }
                
        except Exception as e:
            logger.exception(f"Unexpected error creating thread for company {company.name}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def add_message(self, thread: Thread, content: str) -> Dict[str, Any]:
        """
        Add a message to a thread
        
        Args:
            thread: Thread model instance
            content: Message content
            
        Returns:
            dict: Information about the added message
        """
        try:
            if not thread.openai_thread_id:
                logger.error(f"Thread {thread.id} does not have an OpenAI thread ID")
                return {
                    "success": False,
                    "error": "Thread does not have an OpenAI thread ID"
                }
            
            logger.info(f"Adding message to thread {thread.openai_thread_id}")
            
            # Add message to OpenAI thread
            message = self.client.beta.threads.messages.create(
                thread_id=thread.openai_thread_id,
                role="user",
                content=content
            )
            
            # Get the message ID from the response
            message_id = getattr(message, 'id', 'unknown')
            logger.info(f"Added message to thread {thread.id}: {message_id}")
            
            # Save message to database
            db_message = Message.objects.create(
                thread=thread,
                role='user',
                content=content,
                openai_message_id=message_id
            )
            
            return {
                "success": True,
                "message_id": message_id,
                "db_message_id": db_message.id
            }
        except Exception as e:
            logger.exception(f"Error adding message to thread {thread.id}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def run_assistant(self, thread: Thread) -> Generator[str, None, None]:
        """
        Run the assistant on a thread and stream the response
        
        Args:
            thread: Thread model instance
            
        Yields:
            str: Response content chunks
        """
        try:
            if not thread.openai_thread_id:
                logger.error(f"Thread {thread.id} missing OpenAI thread ID")
                yield json.dumps({
                    "error": "Thread does not have required OpenAI ID"
                })
                return
                
            if not thread.company.openai_assistant_id:
                logger.error(f"Company {thread.company.id} missing OpenAI assistant ID")
                yield json.dumps({
                    "error": "Company does not have required OpenAI assistant ID"
                })
                return
            
            logger.info(f"Running assistant {thread.company.openai_assistant_id} on thread {thread.openai_thread_id}")
            
            # Create a run
            try:
                run = self.client.beta.threads.runs.create(
                    thread_id=thread.openai_thread_id,
                    assistant_id=thread.company.openai_assistant_id
                )
                logger.info(f"Created run with ID: {run.id}")
            except Exception as e:
                logger.exception(f"Error creating run: {str(e)}")
                yield json.dumps({
                    "error": f"Failed to create run: {str(e)}"
                })
                return
            
            # Wait for the run to complete with timeout
            start_time = time.time()
            max_wait_time = 60  # Maximum wait time in seconds
            
            while True:
                # Check for timeout
                if time.time() - start_time > max_wait_time:
                    logger.warning(f"Run timed out after {max_wait_time} seconds")
                    yield json.dumps({
                        "error": "Assistant run timed out"
                    })
                    return
                
                try:
                    run = self.client.beta.threads.runs.retrieve(
                        thread_id=thread.openai_thread_id,
                        run_id=run.id
                    )
                    logger.info(f"Run status: {run.status}")
                except Exception as e:
                    logger.exception(f"Error retrieving run status: {str(e)}")
                    yield json.dumps({
                        "error": f"Error retrieving run status: {str(e)}"
                    })
                    return
                
                if run.status == 'completed':
                    logger.info("Run completed successfully")
                    break
                elif run.status in ['failed', 'cancelled', 'expired']:
                    error_message = getattr(run, 'last_error', {'message': 'Unknown error'})
                    if hasattr(error_message, 'message'):
                        error_text = error_message.message
                    else:
                        error_text = str(error_message)
                    
                    logger.error(f"Run {run.status}: {error_text}")
                    yield json.dumps({
                        "error": f"Run {run.status}: {error_text}"
                    })
                    return
                elif run.status == 'requires_action':
                    logger.warning("Run requires action (function calling not supported)")
                    yield json.dumps({
                        "error": "Assistant requires action that is not supported"
                    })
                    return
                
                # Yield status update
                yield json.dumps({
                    "status": run.status
                })
                
                # Brief delay to avoid rate limiting
                time.sleep(1)
            
            # Get the messages
            try:
                messages = self.client.beta.threads.messages.list(
                    thread_id=thread.openai_thread_id,
                    order='desc',
                    limit=1
                )
                logger.info(f"Retrieved {len(messages.data) if hasattr(messages, 'data') else 0} messages")
            except Exception as e:
                logger.exception(f"Error retrieving messages: {str(e)}")
                yield json.dumps({
                    "error": f"Error retrieving messages: {str(e)}"
                })
                return
            
            if hasattr(messages, 'data') and messages.data:
                message = messages.data[0]
                message_content = ""
                
                # Log the message structure for debugging
                logger.debug(f"Message structure: {dir(message)}")
                
                # Parse message content handling different API versions
                try:
                    if hasattr(message, 'content') and message.content:
                        # V2 format
                        for content_part in message.content:
                            if content_part.type == 'text':
                                message_content = content_part.text.value
                                break
                    elif hasattr(message, 'text') and message.text:
                        # Alternative format
                        message_content = message.text
                    elif hasattr(message, 'content') and isinstance(message.content, str):
                        # Direct string format
                        message_content = message.content
                        
                    logger.info(f"Extracted message content: {message_content[:50]}...")
                except Exception as e:
                    logger.exception(f"Error extracting message content: {str(e)}")
                    # Try alternative extraction methods
                    try:
                        # Desperate attempt to get content using __dict__
                        message_dict = message.__dict__
                        logger.debug(f"Message dict: {message_dict}")
                        if 'content' in message_dict and isinstance(message_dict['content'], list) and len(message_dict['content']) > 0:
                            content_item = message_dict['content'][0]
                            if hasattr(content_item, 'text') and hasattr(content_item.text, 'value'):
                                message_content = content_item.text.value
                    except Exception as alt_e:
                        logger.exception(f"Alternative content extraction failed: {str(alt_e)}")
                
                if not message_content:
                    logger.error("Could not extract message content")
                    yield json.dumps({
                        "error": "Could not extract message content from assistant response"
                    })
                    return
                
                # Save assistant message to database
                try:
                    Message.objects.create(
                        thread=thread,
                        role='assistant',
                        content=message_content,
                        openai_message_id=getattr(message, 'id', 'unknown')
                    )
                    logger.info("Saved assistant message to database")
                except Exception as e:
                    logger.exception(f"Error saving message to database: {str(e)}")
                
                # Stream the content
                yield json.dumps({
                    "content": message_content
                })
            else:
                logger.error("No messages found in response")
                yield json.dumps({
                    "error": "No response from assistant"
                })
                
        except Exception as e:
            logger.exception(f"Error running assistant on thread {thread.id}: {str(e)}")
            yield json.dumps({
                "error": str(e)
            }) 