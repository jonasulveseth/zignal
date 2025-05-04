"""
ASGI routing configuration for zignal project.
This is a simplified version that doesn't use WebSockets.
"""

from django.core.asgi import get_asgi_application

# Regular ASGI application for HTTP
application = get_asgi_application() 