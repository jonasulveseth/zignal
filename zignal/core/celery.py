import os
from celery import Celery
import ssl

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zignal.config.settings')

# Create Celery application
app = Celery('zignal')

# Configure Redis SSL settings for Celery
redis_url = os.environ.get('REDIS_URL', '')
if redis_url.startswith('rediss://'):
    # Configure SSL settings for Redis connections
    ssl_settings = {
        'ssl_cert_reqs': ssl.CERT_NONE,
        'ssl_check_hostname': False
    }
    
    # Apply SSL settings to Celery
    app.conf.broker_use_ssl = ssl_settings
    app.conf.redis_backend_use_ssl = ssl_settings
    
    # Set these as environment variables to ensure they're used by all workers
    os.environ['CELERY_BROKER_USE_SSL'] = 'True'
    os.environ['CELERY_REDIS_BACKEND_USE_SSL'] = 'True'

# Load config from Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all installed apps
app.autodiscover_tasks()

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}') 