# Redis SSL fix
import os

# Modify these Redis settings to SSL connect without cert verification
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379')

# Update Redis connection settings with SSL params
if REDIS_URL.startswith('rediss://'):
    # For SSL connections
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': REDIS_URL,
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                'CONNECTION_POOL_KWARGS': {
                    'ssl_cert_reqs': None,  # Disables certificate verification
                },
            }
        }
    }

    # Channel layers with SSL options
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                'hosts': [{'address': REDIS_URL, 'ssl_cert_reqs': None}],
            },
        },
    }

    # Celery settings with SSL options
    CELERY_BROKER_URL = REDIS_URL
    CELERY_RESULT_BACKEND = REDIS_URL
    CELERY_REDIS_BACKEND_USE_SSL = {
        'ssl_cert_reqs': None,
    }
    CELERY_BROKER_USE_SSL = {
        'ssl_cert_reqs': None, 
    } 