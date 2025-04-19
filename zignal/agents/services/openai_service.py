"""
Service for interacting with the OpenAI API
"""
import os
import logging
from typing import List, Dict, Any, Optional, Generator
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