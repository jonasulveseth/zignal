#!/usr/bin/env python
"""
Script to debug vector store issues on Heroku
This can be run via: heroku run python zignal/debug_heroku.py
"""
import os
import sys
import logging
import traceback
import django

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('heroku_debug')

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zignal.config.settings')
try:
    django.setup()
except Exception as e:
    logger.error(f"Error setting up Django: {e}")
    sys.exit(1)

def check_celery():
    """Check Celery configuration"""
    logger.info("Checking Celery configuration...")
    
    try:
        # Try importing Celery-related modules
        from celery import Celery
        from zignal.config.celery import app
        
        logger.info(f"Celery: {app}")
        logger.info(f"Broker URL: {app.conf.broker_url}")
        logger.info(f"Result Backend: {app.conf.result_backend}")
        
        # Check if broker URL is SSL-enabled
        if app.conf.broker_url.startswith('rediss://'):
            logger.info("Broker URL is using SSL (rediss://)")
        else:
            logger.warning("Broker URL is NOT using SSL")
            
        # Check SSL settings for Redis connections
        import ssl
        broker_ssl_settings = app.conf.get('broker_use_ssl', {})
        backend_ssl_settings = app.conf.get('redis_backend_use_ssl', {})
        
        logger.info(f"Broker SSL settings: {broker_ssl_settings}")
        logger.info(f"Backend SSL settings: {backend_ssl_settings}")
        
        # Check environment variables related to SSL
        ssl_envs = {
            'CELERY_BROKER_USE_SSL': os.environ.get('CELERY_BROKER_USE_SSL'),
            'CELERY_REDIS_BACKEND_USE_SSL': os.environ.get('CELERY_REDIS_BACKEND_USE_SSL'),
            'REDIS_URL': os.environ.get('REDIS_URL', 'Not set')[:20] + '...',
        }
        logger.info(f"SSL environment variables: {ssl_envs}")
        
    except Exception as e:
        logger.error(f"Error checking Celery configuration: {e}")
        logger.error(traceback.format_exc())

def check_vector_store():
    """Check vector store configuration and recent files"""
    logger.info("Checking vector store configuration...")
    
    try:
        # Import the models
        from datasilo.models import DataFile
        from companies.models import Company
        
        # Check company vector store settings
        companies = Company.objects.all()
        logger.info(f"Found {companies.count()} companies")
        
        for company in companies:
            logger.info(f"Company: {company.name}")
            logger.info(f"  Vector Store ID: {company.openai_vector_store_id}")
            logger.info(f"  Assistant ID: {company.openai_assistant_id}")
            
        # Check recent files and their vector store status
        recent_files = DataFile.objects.order_by('-created_at')[:5]
        logger.info(f"Recent files: {recent_files.count()}")
        
        for file in recent_files:
            logger.info(f"File: {file.name} (ID: {file.id})")
            logger.info(f"  Created at: {file.created_at}")
            logger.info(f"  Vector Store Status: {file.vector_store_status}")
            logger.info(f"  Vector Store File ID: {file.vector_store_file_id}")
            
            # Check company and data_silo relationships
            company = None
            relationship_path = []
            
            if hasattr(file, 'company') and file.company:
                company = file.company
                relationship_path.append("direct company relation")
            elif hasattr(file, 'project') and file.project and file.project.company:
                company = file.project.company
                relationship_path.append("project -> company relation")
            elif hasattr(file, 'data_silo') and file.data_silo:
                if file.data_silo.company:
                    company = file.data_silo.company
                    relationship_path.append("data_silo -> company relation")
                elif file.data_silo.project and file.data_silo.project.company:
                    company = file.data_silo.project.company
                    relationship_path.append("data_silo -> project -> company relation")
                    
            if company:
                logger.info(f"  Associated with company: {company.name} via {' and '.join(relationship_path)}")
            else:
                logger.error(f"  No company association found for file: {file.name}")
    
    except Exception as e:
        logger.error(f"Error checking vector store configuration: {e}")
        logger.error(traceback.format_exc())
        
def check_openai_config():
    """Check OpenAI configuration"""
    logger.info("Checking OpenAI configuration...")
    
    try:
        # Import settings
        from django.conf import settings
        
        # Check if API key is configured
        api_key = getattr(settings, 'OPENAI_API_KEY', None)
        if api_key:
            # Mask the key for security
            masked_key = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "***"
            logger.info(f"OpenAI API key is configured: {masked_key}")
        else:
            logger.error("OpenAI API key is not configured")
            
        # Check model settings
        openai_model = getattr(settings, 'OPENAI_MODEL', None)
        logger.info(f"OpenAI model: {openai_model}")
        
        # Try to create a client
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        # Try a simple API call to validate credentials
        logger.info("Testing OpenAI API connection...")
        models = client.models.list(limit=1)
        logger.info(f"OpenAI API connection successful. Available models (sample): {models.data[0].id if models.data else 'None'}")
        
        # Check vector stores feature
        if hasattr(client, 'vector_stores'):
            logger.info("Vector stores feature is available")
        else:
            logger.error("Vector stores feature is NOT available in this OpenAI client version")
    
    except Exception as e:
        logger.error(f"Error checking OpenAI configuration: {e}")
        logger.error(traceback.format_exc())
        
def test_file_processing():
    """Test vector store processing with a recent file"""
    logger.info("Testing file processing...")
    
    try:
        # Import required modules
        from datasilo.models import DataFile
        from core.tasks import process_file_for_vector_store
        
        # Get a recent file that hasn't been processed
        files = DataFile.objects.filter(vector_store_status__in=['pending', 'failed']).order_by('-created_at')
        
        if not files.exists():
            logger.warning("No unprocessed files found")
            return
            
        file = files.first()
        logger.info(f"Testing with file: {file.name} (ID: {file.id})")
        
        # Try processing the file directly (not via Celery)
        logger.info("Processing file directly (bypassing Celery)...")
        result = process_file_for_vector_store(file.id)
        
        logger.info(f"Processing result: {result}")
        
        # Check final status
        file.refresh_from_db()
        logger.info(f"Final vector store status: {file.vector_store_status}")
        logger.info(f"Final vector store file ID: {file.vector_store_file_id}")
        
    except Exception as e:
        logger.error(f"Error testing file processing: {e}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    logger.info("Starting Heroku debug script...")
    
    try:
        # Run each check in sequence
        check_celery()
        check_vector_store()
        check_openai_config()
        test_file_processing()
        
        logger.info("Debug script completed successfully")
    except Exception as e:
        logger.error(f"Unhandled error in debug script: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1) 