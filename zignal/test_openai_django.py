#!/usr/bin/env python
"""
Test script for OpenAI client with Django settings
"""
import os
import sys
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zignal.config.settings')
django.setup()

from django.conf import settings
from openai import OpenAI
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Main test function"""
    # Check the API key
    logger.info(f"API key available: {bool(settings.OPENAI_API_KEY)}")
    logger.info(f"API key first 5 chars: {settings.OPENAI_API_KEY[:5] if settings.OPENAI_API_KEY else 'N/A'}")
    
    # Get OpenAI module version
    import openai
    logger.info(f"OpenAI module version: {openai.__version__}")
    
    # Initialize the client
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    
    # Check if beta namespace is available
    logger.info(f"Client has beta namespace: {hasattr(client, 'beta')}")
    if hasattr(client, 'beta'):
        logger.info(f"Beta attributes: {dir(client.beta)}")
        logger.info(f"Beta has vector_stores: {hasattr(client.beta, 'vector_stores')}")
    
    # Try to create a vector store
    try:
        logger.info("Attempting to create a vector store...")
        vector_store = client.beta.vector_stores.create(
            name="Test Vector Store"
        )
        logger.info(f"Successfully created vector store with ID: {vector_store.id}")
        
        # Try to create an assistant with the vector store
        logger.info("Attempting to create an assistant with vector store...")
        assistant = client.beta.assistants.create(
            name="Test Assistant",
            description="Test assistant with vector store",
            instructions="You are a test assistant.",
            model=settings.OPENAI_MODEL,
            tools=[{"type": "file_search"}],
            tool_resources={
                "file_search": {
                    "vector_store_ids": [vector_store.id]
                }
            }
        )
        logger.info(f"Successfully created assistant with ID: {assistant.id}")
        logger.info(f"Assistant details: {assistant}")
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    main() 