#!/usr/bin/env python
"""
Script to check if Django is correctly loading environment variables
"""
import os
import sys
import django

# Add the project directory to the path so Django can find the settings
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zignal.config.settings')
django.setup()

from django.conf import settings
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_env_vars():
    """Check important environment variables in Django settings"""
    print("\n=== Django Environment Variables Check ===\n")
    
    # Check if dotenv is loaded
    from dotenv import find_dotenv, load_dotenv
    dotenv_path = find_dotenv()
    print(f"Found .env file at: {dotenv_path or 'Not found'}")
    
    # Force reload the .env file
    if dotenv_path:
        print(f"Reloading .env file from: {dotenv_path}")
        load_dotenv(dotenv_path, override=True)
    
    # Check OpenAI settings
    print("\n--- OpenAI Settings ---")
    openai_key = settings.OPENAI_API_KEY
    openai_model = settings.OPENAI_MODEL
    
    print(f"OPENAI_API_KEY set: {bool(openai_key)}")
    if openai_key:
        print(f"OPENAI_API_KEY value: {openai_key[:5]}{'*'*30}")
        print(f"OPENAI_API_KEY looks valid: {not openai_key.startswith('your_') and len(openai_key) > 20}")
    else:
        print("OPENAI_API_KEY is not set")
    
    print(f"OPENAI_MODEL: {openai_model}")
    
    # Check environment variables directly
    print("\n--- Environment Variables ---")
    env_openai_key = os.environ.get('OPENAI_API_KEY', '')
    print(f"os.environ['OPENAI_API_KEY'] set: {bool(env_openai_key)}")
    if env_openai_key:
        print(f"os.environ['OPENAI_API_KEY'] value: {env_openai_key[:5]}{'*'*30}")
    
    # Check other important settings
    print("\n--- Other Important Settings ---")
    print(f"DEBUG: {settings.DEBUG}")
    print(f"ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}")
    print(f"Database ENGINE: {settings.DATABASES['default']['ENGINE']}")
    print(f"Database NAME: {settings.DATABASES['default']['NAME']}")
    
    # Compare the environment variables with settings
    print("\n--- Environment vs Settings Comparison ---")
    if env_openai_key != openai_key:
        print("WARNING: Environment OPENAI_API_KEY doesn't match Django settings!")
        print(f"Environment: {env_openai_key[:5] if env_openai_key else 'Not set'}")
        print(f"Settings: {openai_key[:5] if openai_key else 'Not set'}")
    else:
        print("Environment OPENAI_API_KEY matches Django settings")
    
    print("\n=== Check Complete ===\n")
    
    # Suggest fix if needed
    if not openai_key or openai_key.startswith('your_') or len(openai_key) < 20:
        print("Problem detected: Invalid or missing OpenAI API key in Django settings.")
        print("Possible solutions:")
        print("1. Make sure your .env file has a valid OPENAI_API_KEY value.")
        print("2. Restart your Django server to apply changes to the .env file.")
        print("3. Run the fix_openai_key.py script to update your OpenAI API key.")
        return False
    
    return True

if __name__ == "__main__":
    if check_env_vars():
        print("Environment check completed successfully.")
    else:
        print("Environment check found issues that need to be addressed.")
        sys.exit(1) 