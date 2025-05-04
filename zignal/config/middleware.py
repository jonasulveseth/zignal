"""
Custom middlewares for the zignal project.
"""
import logging

logger = logging.getLogger('django')

class WebSocketLoggingMiddleware:
    """
    Middleware to handle logging for WebSocket paths.
    
    This middleware prevents 404 warnings for WebSocket paths from cluttering the logs
    by suppressing or downgrading these warnings to debug level.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Check if this is a request to a WebSocket path
        if request.path.startswith('/ws/'):
            # Log at debug level instead of warning
            logger.debug(f"WebSocket path requested: {request.path}")
            
            # Process the request normally
            response = self.get_response(request)
            
            # Return the response without logging warnings
            return response
        
        # For non-WebSocket paths, just proceed normally
        return self.get_response(request) 