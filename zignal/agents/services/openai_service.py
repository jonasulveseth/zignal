"""
Service for interacting with the OpenAI API
"""
import os
import logging
from typing import List, Dict, Any, Optional, Generator
import time
from openai import OpenAI
from django.conf import settings
from ..models import Agent, Conversation, Message

logger = logging.getLogger(__name__)

class OpenAIService:
    """
    Service for interacting with the OpenAI API
    """
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.default_model = settings.OPENAI_MODEL
        self.default_embeddings_model = settings.OPENAI_EMBEDDINGS_MODEL
    
    def generate_embeddings(self, text: str) -> List[float]:
        """
        Generate embeddings for the given text
        """
        try:
            response = self.client.embeddings.create(
                model=self.default_embeddings_model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating embeddings: {str(e)}")
            raise
    
    def prepare_messages(self, conversation: Conversation) -> List[Dict[str, str]]:
        """
        Prepare the message format required by OpenAI API from a conversation
        """
        messages = []
        
        # Add system prompt if present
        if conversation.agent.system_prompt:
            messages.append({
                "role": "system",
                "content": conversation.agent.system_prompt
            })
        
        # Add all messages from the conversation
        for message in conversation.messages.all():
            messages.append({
                "role": message.role,
                "content": message.content
            })
        
        return messages
    
    def chat_completion(self, 
                        conversation: Conversation, 
                        new_message_content: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a chat completion for the given conversation
        """
        # Check if we should use the Assistants API instead
        if conversation.agent.api_version == 'assistants':
            return self.assistant_completion(conversation, new_message_content)
            
        messages = self.prepare_messages(conversation)
        
        # Add new message if provided
        if new_message_content:
            user_message = Message.objects.create(
                conversation=conversation,
                role='user',
                content=new_message_content
            )
            messages.append({
                "role": "user",
                "content": new_message_content
            })
        
        try:
            agent = conversation.agent
            response = self.client.chat.completions.create(
                model=agent.model,
                messages=messages,
                temperature=agent.temperature,
                max_tokens=agent.max_tokens
            )
            
            # Save assistant response to conversation
            assistant_content = response.choices[0].message.content
            Message.objects.create(
                conversation=conversation,
                role='assistant',
                content=assistant_content
            )
            
            return {
                "response": assistant_content,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }
        except Exception as e:
            logger.error(f"Error in chat completion: {str(e)}")
            # Save error message
            Message.objects.create(
                conversation=conversation,
                role='system',
                content=f"Error: {str(e)}"
            )
            raise
    
    def streaming_chat_completion(self, 
                                conversation: Conversation, 
                                new_message_content: str) -> Generator[str, None, None]:
        """
        Generate a streaming chat completion for the given conversation
        """
        # Check if we should use the Assistants API instead
        if conversation.agent.api_version == 'assistants':
            return self.streaming_assistant_completion(conversation, new_message_content)
            
        messages = self.prepare_messages(conversation)
        
        # Add new message
        user_message = Message.objects.create(
            conversation=conversation,
            role='user',
            content=new_message_content
        )
        messages.append({
            "role": "user",
            "content": new_message_content
        })
        
        try:
            agent = conversation.agent
            response = self.client.chat.completions.create(
                model=agent.model,
                messages=messages,
                temperature=agent.temperature,
                max_tokens=agent.max_tokens,
                stream=True
            )
            
            # Collect the full response while yielding chunks
            full_response = ""
            
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    yield content
            
            # Save the complete response to the database
            Message.objects.create(
                conversation=conversation,
                role='assistant',
                content=full_response
            )
            
        except Exception as e:
            logger.error(f"Error in streaming chat completion: {str(e)}")
            error_message = f"Error: {str(e)}"
            
            # Save error message
            Message.objects.create(
                conversation=conversation,
                role='system',
                content=error_message
            )
            
            yield error_message
            
    # ------------- Assistants API Methods -------------
    
    def create_assistant(self, agent: Agent) -> str:
        """
        Create an OpenAI Assistant from an Agent model
        
        Returns the Assistant ID
        """
        try:
            # Create assistant
            assistant = self.client.beta.assistants.create(
                name=agent.name,
                description=agent.description or f"Zignal {agent.get_agent_type_display()}",
                instructions=agent.system_prompt or "You are a helpful AI assistant.",
                model=agent.model,
                temperature=agent.temperature,
                metadata={
                    "agent_id": str(agent.id),
                    "agent_type": agent.agent_type
                }
            )
            
            # Return the assistant ID
            return assistant.id
            
        except Exception as e:
            logger.error(f"Error creating assistant: {str(e)}")
            raise
    
    def update_assistant(self, agent: Agent) -> str:
        """
        Update an existing OpenAI Assistant from an Agent model
        
        Returns the Assistant ID
        """
        if not agent.assistant_id:
            return self.create_assistant(agent)
            
        try:
            # Update assistant
            assistant = self.client.beta.assistants.update(
                assistant_id=agent.assistant_id,
                name=agent.name,
                description=agent.description or f"Zignal {agent.get_agent_type_display()}",
                instructions=agent.system_prompt or "You are a helpful AI assistant.",
                model=agent.model,
                temperature=agent.temperature,
                metadata={
                    "agent_id": str(agent.id),
                    "agent_type": agent.agent_type
                }
            )
            
            # Return the assistant ID
            return assistant.id
            
        except Exception as e:
            logger.error(f"Error updating assistant: {str(e)}")
            raise
    
    def create_thread(self, conversation: Conversation) -> str:
        """
        Create an OpenAI Thread for a conversation
        
        Returns the Thread ID
        """
        try:
            # Create thread
            thread = self.client.beta.threads.create()
            
            # Save the thread ID to the conversation
            conversation.thread_id = thread.id
            conversation.save()
            
            return thread.id
            
        except Exception as e:
            logger.error(f"Error creating thread: {str(e)}")
            raise
    
    def add_message_to_thread(self, conversation: Conversation, content: str, role: str = 'user') -> None:
        """
        Add a message to an OpenAI Thread
        """
        if not conversation.thread_id:
            self.create_thread(conversation)
            
        try:
            # Add message to thread
            self.client.beta.threads.messages.create(
                thread_id=conversation.thread_id,
                role=role,
                content=content
            )
            
            # Save message to our database as well
            Message.objects.create(
                conversation=conversation,
                role=role,
                content=content
            )
            
        except Exception as e:
            logger.error(f"Error adding message to thread: {str(e)}")
            raise
    
    def run_assistant(self, conversation: Conversation) -> Dict[str, Any]:
        """
        Run the assistant on a thread
        
        Returns the Run object
        """
        if not conversation.thread_id:
            raise ValueError("Conversation has no thread_id")
            
        if not conversation.agent.assistant_id:
            raise ValueError("Agent has no assistant_id")
            
        try:
            # Create a run
            run = self.client.beta.threads.runs.create(
                thread_id=conversation.thread_id,
                assistant_id=conversation.agent.assistant_id
            )
            
            return run
            
        except Exception as e:
            logger.error(f"Error running assistant: {str(e)}")
            raise
    
    def wait_for_run_completion(self, thread_id: str, run_id: str) -> Dict[str, Any]:
        """
        Wait for a run to complete
        
        Returns the Run object when done
        """
        max_wait_time = 120  # Maximum wait time in seconds
        start_time = time.time()
        
        while True:
            # Check if we've exceeded the max wait time
            if time.time() - start_time > max_wait_time:
                raise TimeoutError("Run timed out")
                
            # Check the run status
            run = self.client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run_id
            )
            
            # If completed, return the run
            if run.status == 'completed':
                return run
                
            # If failed, raise an exception
            if run.status in ['failed', 'cancelled', 'expired']:
                raise Exception(f"Run {run_id} {run.status}: {run.last_error}")
                
            # Wait before polling again
            time.sleep(1)
    
    def get_thread_messages(self, thread_id: str) -> List[Dict[str, Any]]:
        """
        Get messages from a thread
        
        Returns a list of messages
        """
        try:
            # Get messages
            messages = self.client.beta.threads.messages.list(
                thread_id=thread_id
            )
            
            return messages.data
            
        except Exception as e:
            logger.error(f"Error getting thread messages: {str(e)}")
            raise
    
    def assistant_completion(self, 
                            conversation: Conversation, 
                            new_message_content: Optional[str] = None) -> Dict[str, Any]:
        """
        Get a completion from an assistant
        """
        try:
            # Ensure the agent has an assistant_id
            agent = conversation.agent
            if not agent.assistant_id:
                agent.assistant_id = self.create_assistant(agent)
                agent.save()
            
            # Ensure the conversation has a thread_id
            if not conversation.thread_id:
                conversation.thread_id = self.create_thread(conversation)
                conversation.save()
            
            # Add the user message to the thread
            if new_message_content:
                self.add_message_to_thread(conversation, new_message_content, 'user')
            
            # Run the assistant
            run = self.run_assistant(conversation)
            
            # Wait for the run to complete
            self.wait_for_run_completion(conversation.thread_id, run.id)
            
            # Get the latest message from the assistant
            messages = self.get_thread_messages(conversation.thread_id)
            
            # Find the latest assistant message
            for message in messages:
                if message.role == 'assistant':
                    # Extract message content
                    if message.content and len(message.content) > 0:
                        assistant_content = message.content[0].text.value
                        
                        # Save to our database
                        Message.objects.create(
                            conversation=conversation,
                            role='assistant',
                            content=assistant_content
                        )
                        
                        return {
                            "response": assistant_content,
                            "usage": {
                                "prompt_tokens": 0,  # Not available in Assistants API
                                "completion_tokens": 0,
                                "total_tokens": 0
                            }
                        }
            
            raise Exception("No assistant message found in thread")
            
        except Exception as e:
            logger.error(f"Error in assistant completion: {str(e)}")
            # Save error message
            Message.objects.create(
                conversation=conversation,
                role='system',
                content=f"Error: {str(e)}"
            )
            raise
    
    def streaming_assistant_completion(self, 
                                      conversation: Conversation, 
                                      new_message_content: str) -> Generator[str, None, None]:
        """
        Stream a completion from an assistant
        
        Note: OpenAI Assistants API doesn't natively support streaming,
        so we simulate it by polling and checking for new messages
        """
        try:
            # Ensure the agent has an assistant_id
            agent = conversation.agent
            if not agent.assistant_id:
                agent.assistant_id = self.create_assistant(agent)
                agent.save()
            
            # Ensure the conversation has a thread_id
            if not conversation.thread_id:
                conversation.thread_id = self.create_thread(conversation)
                conversation.save()
            
            # Add the user message to the thread
            self.add_message_to_thread(conversation, new_message_content, 'user')
            
            # Let the user know we're processing
            yield "Processing your request... "
            
            # Run the assistant
            run = self.run_assistant(conversation)
            
            # Wait for the run to complete
            self.wait_for_run_completion(conversation.thread_id, run.id)
            
            # Get the latest message from the assistant
            messages = self.get_thread_messages(conversation.thread_id)
            
            # Find the latest assistant message
            assistant_content = None
            for message in messages:
                if message.role == 'assistant':
                    # Extract message content
                    if message.content and len(message.content) > 0:
                        assistant_content = message.content[0].text.value
                        break
            
            if assistant_content:
                # Save to our database
                Message.objects.create(
                    conversation=conversation,
                    role='assistant',
                    content=assistant_content
                )
                
                # Yield the content
                yield assistant_content
            else:
                error_message = "No assistant message found in thread"
                Message.objects.create(
                    conversation=conversation,
                    role='system',
                    content=error_message
                )
                yield error_message
                
        except Exception as e:
            error_message = f"Error: {str(e)}"
            logger.error(f"Error in streaming assistant completion: {error_message}")
            
            # Save error message
            Message.objects.create(
                conversation=conversation,
                role='system',
                content=error_message
            )
            
            yield error_message 