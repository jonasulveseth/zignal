import json
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import ensure_csrf_cookie
from django.db.models import Q

from .models import Notification
from .services import NotificationService

logger = logging.getLogger(__name__)


@login_required
@require_GET
@ensure_csrf_cookie
def get_notifications(request):
    """
    Get notifications for the current user
    
    Optional query params:
        - unread_only: If 'true', only return unread notifications
        - limit: Number of notifications to return (default: 20)
        - offset: Starting point for pagination (default: 0)
        
    Returns:
        JsonResponse: JSON response with notifications data
    """
    user = request.user
    unread_only = request.GET.get('unread_only', 'false').lower() == 'true'
    limit = int(request.GET.get('limit', 20))
    offset = int(request.GET.get('offset', 0))
    
    # Query notifications
    query = Q(recipient=user)
    if unread_only:
        query &= Q(unread=True)
    
    notifications = Notification.objects.filter(query).order_by('-created_at')[offset:offset+limit]
    total_count = Notification.objects.filter(query).count()
    unread_count = Notification.objects.filter(recipient=user, unread=True).count()
    
    # Format notifications for response
    notifications_data = []
    for notification in notifications:
        notifications_data.append({
            'id': str(notification.id),
            'title': notification.title,
            'message': notification.message,
            'level': notification.level,
            'unread': notification.unread,
            'created_at': notification.created_at.isoformat(),
            'action_url': notification.action_url,
            'action_text': notification.action_text,
        })
    
    return JsonResponse({
        'notifications': notifications_data,
        'total_count': total_count,
        'unread_count': unread_count,
        'has_more': total_count > (offset + limit)
    })


@login_required
@require_POST
def mark_notification_read(request, notification_id):
    """
    Mark a specific notification as read
    
    Args:
        request: HTTP request
        notification_id: ID of the notification to mark as read
        
    Returns:
        JsonResponse: JSON response indicating success
    """
    user = request.user
    notification = get_object_or_404(Notification, id=notification_id, recipient=user)
    
    NotificationService.mark_as_read(notification)
    
    return JsonResponse({
        'success': True,
        'unread_count': Notification.objects.filter(recipient=user, unread=True).count()
    })


@login_required
@require_POST
def mark_all_read(request):
    """
    Mark all notifications for the current user as read
    
    Returns:
        JsonResponse: JSON response indicating success and count of notifications marked as read
    """
    user = request.user
    
    count = NotificationService.mark_all_as_read(user)
    
    return JsonResponse({
        'success': True,
        'count': count,
        'unread_count': 0
    })


@login_required
@require_GET
def get_notification_count(request):
    """
    Get counts of total and unread notifications for the current user
    
    Returns:
        JsonResponse: JSON response with notification counts
    """
    user = request.user
    
    total_count = Notification.objects.filter(recipient=user).count()
    unread_count = Notification.objects.filter(recipient=user, unread=True).count()
    
    return JsonResponse({
        'total_count': total_count,
        'unread_count': unread_count
    }) 