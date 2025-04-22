from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

# Import WebSocket routing from apps
from notifications.routing import websocket_urlpatterns as notification_ws_patterns

# Combine all WebSocket URL patterns
websocket_urlpatterns = [
    *notification_ws_patterns,
    # Add patterns from other apps here
]

# Set up the ASGI application with HTTP and WebSocket support
application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        )
    ),
}) 