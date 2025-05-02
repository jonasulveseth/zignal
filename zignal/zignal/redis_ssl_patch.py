"""
Redis SSL Monkey Patch

This file patches the Redis connection class to disable SSL certificate verification.
"""
import ssl
import redis.connection

# For Redis >= 4.0.0
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
        
    print("Redis SSL patch applied successfully!")
        
except Exception as e:
    print(f"Failed to apply Redis SSL patch: {e}")
    # Continue without the patch 