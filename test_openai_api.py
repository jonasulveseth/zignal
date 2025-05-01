"""
Test script to check the structure of the OpenAI API client
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

# Get OpenAI module version
import openai
logger.info(f"OpenAI module version: {openai.__version__}")

# Print all attributes of client.beta
logger.info("Attributes of client.beta:")
for attr in dir(client.beta):
    if not attr.startswith('_'):
        logger.info(f"  - {attr}")

# Print all attributes of client.beta.assistants
logger.info("\nAttributes of client.beta.assistants:")
for attr in dir(client.beta.assistants):
    if not attr.startswith('_'):
        logger.info(f"  - {attr}")

# Try to create a simple assistant
try:
    logger.info("\nTrying to create an assistant...")
    assistant = client.beta.assistants.create(
        name="Test Assistant",
        instructions="You are a test assistant",
        model="gpt-3.5-turbo",
    )
    logger.info(f"Successfully created assistant with ID: {assistant.id}")
    
    # Check available methods to add files
    logger.info("\nChecking how to add files to assistants...")
    
    # Method 1: Check if there's a 'files' attribute
    has_files_attr = hasattr(client.beta.assistants, 'files')
    logger.info(f"client.beta.assistants has 'files' attribute: {has_files_attr}")
    
    # Method 2: Check if there's an 'attach_file' method or similar
    assistant_dir = dir(client.beta.assistants)
    file_related_methods = [m for m in assistant_dir if 'file' in m.lower()]
    logger.info(f"File-related methods in client.beta.assistants: {file_related_methods}")
    
    # Method 3: Check if we can create a file first and then attach it
    logger.info("\nTrying to create a file...")
    with open("/tmp/test.txt", "w") as f:
        f.write("This is a test file.")
    
    with open("/tmp/test.txt", "rb") as f:
        file = client.files.create(
            file=f,
            purpose="assistants"
        )
    logger.info(f"Created file with ID: {file.id}")
    
    # List all methods of client.files
    logger.info("\nMethods of client.files:")
    for attr in dir(client.files):
        if not attr.startswith('_'):
            logger.info(f"  - {attr}")
    
    # Explore the OpenAI documentation for the right way to attach files to assistants
    logger.info("\nPlease check the OpenAI documentation for the right way to attach files to assistants.")
    logger.info("The API structure may have changed. Visit: https://platform.openai.com/docs/assistants-api for more information.")
    
except Exception as e:
    logger.error(f"Error: {str(e)}") 