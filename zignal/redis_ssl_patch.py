"""
Redis SSL Monkey Patch

This file provides comprehensive patches for all Redis-related libraries to support SSL connections
without certificate verification and handle URL scheme conversions between redis:// and rediss://.
"""
import ssl
import os
import redis.connection

# ======== URL conversions ========
# First, ensure all Redis URLs use the correct scheme based on environment

def convert_redis_urls():
    """Convert all Redis URLs to use the same scheme (redis:// or rediss://) based on the main REDIS_URL"""
    main_redis_url = os.environ.get('REDIS_URL', '')
    
    # Determine if we should use SSL based on main Redis URL
    use_ssl = main_redis_url.startswith('rediss://')
    
    # Dictionary of environment variables to check and potentially convert
    redis_env_vars = [
        'REDIS_URL',
        'CELERY_BROKER_URL',
        'CELERY_RESULT_BACKEND'
    ]
    
    # Convert all Redis URLs to the correct scheme
    for var in redis_env_vars:
        if var in os.environ and os.environ[var]:
            current_url = os.environ[var]
            
            # Convert URL scheme if needed
            if use_ssl and current_url.startswith('redis://'):
                # Convert to rediss://
                os.environ[var] = current_url.replace('redis://', 'rediss://', 1)
                print(f"Converted {var} from redis:// to rediss://")
            elif not use_ssl and current_url.startswith('rediss://'):
                # Convert to redis://
                os.environ[var] = current_url.replace('rediss://', 'redis://', 1)
                print(f"Converted {var} from rediss:// to redis://")

# Run URL conversions first
try:
    convert_redis_urls()
except Exception as e:
    print(f"Failed to convert Redis URLs: {e}")

# ======== Redis Connection Patching ========
try:
    # Save the original connection class
    orig_connection = redis.connection.Connection

    # Override the SSL context creation to disable certificate verification
    class PatchedConnection(orig_connection):
        def get_ssl_context(self):
            ctx = ssl.create_default_context()
            # Important: Must set check_hostname to False BEFORE changing verify_mode
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            return ctx

    # Apply the patch
    redis.connection.Connection = PatchedConnection
    
    # Also patch the SSL connection parameters
    if hasattr(redis.connection, 'SSLConnection'):
        orig_ssl_connection = redis.connection.SSLConnection
        
        class PatchedSSLConnection(orig_ssl_connection):
            def __init__(self, *args, **kwargs):
                kwargs['ssl_cert_reqs'] = None
                super().__init__(*args, **kwargs)
                
        redis.connection.SSLConnection = PatchedSSLConnection
        
    # Additional patch for newer Redis versions that use a different method
    if hasattr(redis.connection, 'RedisSSLContext'):
        orig_redis_ssl_context = redis.connection.RedisSSLContext
        
        class PatchedRedisSSLContext(orig_redis_ssl_context):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                # Important: Must disable hostname checking before setting verify_mode
                self.context.check_hostname = False
                self.context.verify_mode = ssl.CERT_NONE
                
        redis.connection.RedisSSLContext = PatchedRedisSSLContext
    
    print("Redis SSL connection patching complete!")
        
except Exception as e:
    print(f"Failed to apply Redis SSL patch: {e}")
    # Continue without the patch

# ======== Celery Patching ========
try:
    from celery.backends.redis import RedisBackend
    
    # Save original methods
    original_params_from_url = RedisBackend._params_from_url
    
    # Define patched method
    def patched_params_from_url(self, url, defaults):
        # Force URL to use rediss:// scheme if SSL params are provided
        if (url.startswith('redis://') and 
            ((hasattr(self, 'redis_backend_use_ssl') and self.redis_backend_use_ssl) or 
             (hasattr(self, 'broker_use_ssl') and self.broker_use_ssl))):
            url = url.replace('redis://', 'rediss://', 1)
            print(f"Converted Celery Redis URL from redis:// to rediss://")
            
        return original_params_from_url(self, url, defaults)
    
    # Apply the patch
    RedisBackend._params_from_url = patched_params_from_url
    
    print("Celery Redis backend patching complete!")
    
except Exception as e:
    print(f"Failed to patch Celery Redis backend: {e}")

# ======== Channels Redis Patching ========
try:
    import importlib
    
    # Try to patch channels_redis (only if installed)
    if importlib.util.find_spec('channels_redis') is not None:
        import channels_redis.core
        
        # Get the original channel layer
        orig_channel_layer = channels_redis.core.RedisChannelLayer
        
        # Create patched channel layer
        class PatchedRedisChannelLayer(orig_channel_layer):
            def __init__(self, *args, **kwargs):
                # Ensure all connection configs have SSL settings
                if 'hosts' in kwargs.get('config', {}):
                    for i, host_config in enumerate(kwargs['config']['hosts']):
                        if isinstance(host_config, dict) and 'address' in host_config:
                            # Add SSL settings if using rediss://
                            if isinstance(host_config['address'], str) and host_config['address'].startswith('rediss://'):
                                host_config['ssl_cert_reqs'] = None
                                host_config['ssl_check_hostname'] = False
                            # Force rediss:// if main Redis URL uses SSL
                            elif (isinstance(host_config['address'], str) and 
                                 host_config['address'].startswith('redis://') and
                                 os.environ.get('REDIS_URL', '').startswith('rediss://')):
                                host_config['address'] = host_config['address'].replace('redis://', 'rediss://', 1)
                                host_config['ssl_cert_reqs'] = None
                                host_config['ssl_check_hostname'] = False
                                print(f"Converted Channels Redis URL from redis:// to rediss://")
                                
                super().__init__(*args, **kwargs)
        
        # Apply the patch
        channels_redis.core.RedisChannelLayer = PatchedRedisChannelLayer
        
        print("Channels Redis patching complete!")
        
except Exception as e:
    print(f"Failed to patch Channels Redis: {e}") 