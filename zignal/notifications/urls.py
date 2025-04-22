from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('api/notifications/', views.get_notifications, name='get_notifications'),
    path('api/notifications/count/', views.get_notification_count, name='get_notification_count'),
    path('api/notifications/mark-all-read/', views.mark_all_read, name='mark_all_read'),
    path('api/notifications/<uuid:notification_id>/mark-read/', views.mark_notification_read, name='mark_notification_read'),
] 