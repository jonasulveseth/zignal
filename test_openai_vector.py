"""
Test script to check if the OpenAI vector_stores API is working properly
"""
import os
import logging
from openai import OpenAI

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the OpenAI client
api_key = os.environ.get("OPENAI_API_KEY") or input("Enter your OpenAI API key: ")
client = OpenAI(api_key=api_key)

try:
    # Try to get all vector stores
    logger.info("Trying to access the vector_stores API...")
    try:
        # Try method 1: Get all vector stores
        vector_stores = client.beta.vector_stores.list()
        logger.info(f"Success! Found {len(vector_stores.data)} vector stores")
    except Exception as e:
        logger.error(f"Error accessing vector_stores.list(): {str(e)}")
        
    # Try method 2: Create a vector store
    try:
        logger.info("Trying to create a vector store...")
        vector_store = client.beta.vector_stores.create(
            name="Test Vector Store"
        )
        logger.info(f"Successfully created vector store with ID: {vector_store.id}")
    except Exception as e:
        logger.error(f"Error creating vector store: {str(e)}")
        
    # Print client details
    logger.info(f"OpenAI client version: {client.__module__}")
    logger.info(f"API key (first 5 chars): {api_key[:5]}...")
    
    # Get OpenAI module version
    import openai
    logger.info(f"OpenAI module version: {openai.__version__}")
    
except Exception as e:
    logger.error(f"Unexpected error: {str(e)}")

# Check if Beta has vector_stores attribute
try:
    has_vector_stores = hasattr(client.beta, 'vector_stores')
    logger.info(f"client.beta has vector_stores attribute: {has_vector_stores}")
    
    # Print all attributes of client.beta
    logger.info(f"All attributes of client.beta: {dir(client.beta)}")
except Exception as e:
    logger.error(f"Error checking client.beta attributes: {str(e)}") 