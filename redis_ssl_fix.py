"""
Redis SSL Fix script

This file overrides the Redis connection class to disable SSL certificate verification.
"""

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