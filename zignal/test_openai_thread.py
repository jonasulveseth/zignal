#!/usr/bin/env python
"""
Test script to verify OpenAI thread creation
"""
import os
import sys
import django
import time
import logging

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from openai import OpenAI
from django.conf import settings

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_openai_thread_creation():
    """Test creating an OpenAI thread directly"""
    try:
        logger.info("Starting OpenAI thread creation test")
        logger.info(f"Using API key ending with: {settings.OPENAI_API_KEY[-4:]}")
        
        # Create OpenAI client with v2 header
        client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            default_headers={"OpenAI-Beta": "assistants=v2"}
        )
        logger.info("Created OpenAI client with assistants=v2 header")
        
        # Create thread directly
        start_time = time.time()
        thread = client.beta.threads.create()
        duration = time.time() - start_time
        
        thread_id = thread.id
        logger.info(f"Successfully created thread in {duration:.2f}s with ID: {thread_id}")
        
        # Verify thread exists by retrieving it
        retrieved_thread = client.beta.threads.retrieve(thread_id=thread_id)
        logger.info(f"Successfully retrieved thread: {retrieved_thread.id}")
        
        return {"success": True, "thread_id": thread_id}
    
    except Exception as e:
        logger.exception(f"Error creating OpenAI thread: {str(e)}")
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    print("\nTesting OpenAI thread creation...")
    result = test_openai_thread_creation()
    
    if result["success"]:
        print(f"\n✅ SUCCESS: Created thread with ID: {result['thread_id']}")
    else:
        print(f"\n❌ ERROR: {result['error']}") 