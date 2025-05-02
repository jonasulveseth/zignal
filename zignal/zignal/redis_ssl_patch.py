"""
Redis SSL Monkey Patch

This file patches the Redis connection class to disable SSL certificate verification.
"""
import ssl
import redis.connection

# Save the original connection class
orig_connection = redis.connection.Connection

# Override the SSL context creation to disable certificate verification
class PatchedConnection(orig_connection):
    def get_ssl_context(self):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx

# Apply the patch
redis.connection.Connection = PatchedConnection 