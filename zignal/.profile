#!/bin/bash

# Set environment variable to disable SSL certificate verification for Python
export PYTHONHTTPSVERIFY=0

# Create a Redis SSL fix file
cat > $HOME/redis_ssl_disable.py << 'EOF'
import ssl
import redis.connection

# Get the original connection class
OrigConnection = redis.connection.Connection

# Create a patched connection class that disables SSL verification
class SSLPatchedConnection(OrigConnection):
    def get_ssl_context(self):
        context = ssl.create_default_context()
        # Important: Must set check_hostname to False BEFORE changing verify_mode
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        return context

# Apply the monkey patch
redis.connection.Connection = SSLPatchedConnection

# Additional patches for newer Redis versions
if hasattr(redis.connection, 'SSLConnection'):
    OrigSSLConnection = redis.connection.SSLConnection
    
    class PatchedSSLConnection(OrigSSLConnection):
        def __init__(self, *args, **kwargs):
            kwargs['ssl_check_hostname'] = False
            kwargs['ssl_cert_reqs'] = None
            super().__init__(*args, **kwargs)
    
    redis.connection.SSLConnection = PatchedSSLConnection

if hasattr(redis.connection, 'RedisSSLContext'):
    OrigRedisSSLContext = redis.connection.RedisSSLContext
    
    class PatchedRedisSSLContext(OrigRedisSSLContext):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.context.check_hostname = False
            self.context.verify_mode = ssl.CERT_NONE
    
    redis.connection.RedisSSLContext = PatchedRedisSSLContext

print("Redis SSL certificate verification disabled!")
EOF

# Run the script
python $HOME/redis_ssl_disable.py

echo "Redis SSL patch applied" 