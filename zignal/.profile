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
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        return context

# Apply the monkey patch
redis.connection.Connection = SSLPatchedConnection

print("Redis SSL certificate verification disabled!")
EOF

# Run the script
python $HOME/redis_ssl_disable.py

echo "Redis SSL patch applied" 