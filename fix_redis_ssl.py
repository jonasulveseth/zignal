#!/usr/bin/env python
"""
Wrapper script to start Django with Redis SSL fix

This script applies the Redis SSL certificate bypass fix before starting Django,
allowing it to connect to Redis instances with self-signed certificates.
"""

import os
import sys

# Apply Redis SSL fix
try:
    import ssl
    import redis.connection
    
    # Save the original connection class
    OriginalConnection = redis.connection.Connection
    
    # Override the SSL context creation method to disable certificate verification
    class SSLConnection(OriginalConnection):
        def get_ssl_context(self):
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            return context
    
    # Replace the original Connection with our patched version
    redis.connection.Connection = SSLConnection
    print("Redis SSL certificate verification disabled")
except Exception as e:
    print(f"Failed to apply Redis SSL fix: {e}")

# Execute Django management command
os.chdir('zignal')
from django.core.management import execute_from_command_line
if __name__ == "__main__":
    execute_from_command_line(sys.argv) 