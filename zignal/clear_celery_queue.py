#!/usr/bin/env python
"""
Script to clear Celery tasks from the queue on Heroku
Usage: heroku run python zignal/clear_celery_queue.py
"""
import os
import sys
import logging
import django
import celery
import redis
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('celery_cleaner')

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zignal.zignal.config.settings')
try:
    django.setup()
except Exception as e:
    logger.error(f"Error setting up Django: {e}")
    sys.exit(1)

def clear_celery_queues():
    """Clear all Celery queues"""
    try:
        # Import Celery app
        from zignal.config.celery import app
        
        # Check if we can connect to the broker
        logger.info(f"Checking connection to Celery broker: {app.conf.broker_url}")
        
        # Get the connection to Redis
        with app.connection_or_acquire() as conn:
            logger.info("Successfully connected to broker")
            
            # Check if we're using Redis
            if 'redis' in app.conf.broker_url:
                logger.info("Broker is Redis, attempting direct queue purge")
                
                # Get Redis connection
                redis_client = conn.channel().client
                
                # List all keys matching Celery pattern
                celery_keys = redis_client.keys('celery*')
                logger.info(f"Found {len(celery_keys)} Celery-related Redis keys")
                
                if celery_keys:
                    # Delete all Celery keys
                    redis_client.delete(*celery_keys)
                    logger.info("Deleted all Celery keys")
                    
                    # Additional cleanup for Celery
                    queue_keys = redis_client.keys('_kombu.binding.*')
                    if queue_keys:
                        redis_client.delete(*queue_keys)
                        logger.info(f"Deleted {len(queue_keys)} Kombu binding keys")
                else:
                    logger.info("No Celery keys found to delete")
                
                # Also check for specific task queue
                process_file_queue = redis_client.keys('*process_file_for_vector_store*')
                if process_file_queue:
                    redis_client.delete(*process_file_queue)
                    logger.info(f"Deleted {len(process_file_queue)} process_file_for_vector_store keys")
                
                # Get updated stats
                remaining_keys = redis_client.keys('celery*')
                logger.info(f"Remaining Celery keys: {len(remaining_keys)}")
                
                # Check memory usage before and after
                info_before = redis_client.info('memory')
                logger.info(f"Redis memory usage: {info_before.get('used_memory_human', 'unknown')}")
                
                return True
            else:
                logger.error("Non-Redis broker detected. This script only supports Redis.")
                return False
                
    except Exception as e:
        import traceback
        logger.error(f"Error clearing Celery queues: {e}")
        logger.error(traceback.format_exc())
        return False

def fix_stuck_files():
    """Fix files stuck in processing state"""
    try:
        from datasilo.models import DataFile
        
        # Find files stuck in "processing" state
        stuck_files = DataFile.objects.filter(vector_store_status='processing')
        logger.info(f"Found {stuck_files.count()} files stuck in 'processing' state")
        
        if stuck_files.exists():
            # Reset status to 'pending'
            count = stuck_files.update(vector_store_status='pending')
            logger.info(f"Reset {count} files to 'pending' status")
            
        return True
    except Exception as e:
        import traceback
        logger.error(f"Error fixing stuck files: {e}")
        logger.error(traceback.format_exc())
        return False

def get_memory_usage():
    """Get current memory usage on Heroku"""
    try:
        import os
        import subprocess
        
        # Try to get memory usage via Heroku command
        logger.info("Checking current memory usage")
        
        try:
            import psutil
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            logger.info(f"Current process memory usage: {memory_info.rss / (1024 * 1024):.2f} MB")
        except ImportError:
            logger.info("psutil not available, skipping process memory check")
        
        return True
    except Exception as e:
        logger.error(f"Error getting memory usage: {e}")
        return False

if __name__ == "__main__":
    logger.info("Starting Celery queue cleanup...")
    
    # First check memory usage
    get_memory_usage()
    
    # Clear Celery queues
    success = clear_celery_queues()
    if success:
        logger.info("Successfully cleared Celery queues")
    else:
        logger.error("Failed to clear Celery queues")
    
    # Fix any stuck files
    fix_success = fix_stuck_files()
    if fix_success:
        logger.info("Successfully fixed stuck files")
    else:
        logger.error("Failed to fix stuck files")
    
    # Check memory usage again
    get_memory_usage()
    
    logger.info("Celery queue cleanup completed") 