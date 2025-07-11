import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zignal.config.settings')

from celery import Celery

# Set the default Django settings module for the 'celery' program
app = Celery('zignal')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

# Production safety: If REDIS_URL uses rediss://, make sure Celery URLs do too
redis_url = os.environ.get('REDIS_URL', '')
if redis_url.startswith('rediss://'):
    # Fix any Redis URLs that might be using the wrong scheme
    if os.environ.get('CELERY_BROKER_URL', '').startswith('redis://'):
        os.environ['CELERY_BROKER_URL'] = os.environ['CELERY_BROKER_URL'].replace('redis://', 'rediss://', 1)
        print("Fixed CELERY_BROKER_URL to use rediss://")
        
    if os.environ.get('CELERY_RESULT_BACKEND', '').startswith('redis://'):
        os.environ['CELERY_RESULT_BACKEND'] = os.environ['CELERY_RESULT_BACKEND'].replace('redis://', 'rediss://', 1)
        print("Fixed CELERY_RESULT_BACKEND to use rediss://") 