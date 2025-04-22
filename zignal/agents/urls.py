from django.urls import path
from . import views

app_name = 'agents'

urlpatterns = [
    path('api/agents/', views.agent_list, name='agent_list'),
    path('api/agents/<int:agent_id>/', views.agent_detail, name='agent_detail'),
    path('api/conversations/', views.conversation_list, name='conversation_list'),
    path('api/conversations/<int:conversation_id>/', views.conversation_detail, name='conversation_detail'),
    path('api/conversations/<int:conversation_id>/messages/', views.message_list, name='message_list'),
    path('api/conversations/<int:conversation_id>/chat/', views.chat, name='chat'),
    path('api/conversations/<int:conversation_id>/stream/', views.stream_chat, name='stream_chat'),
    
    # Portfolio manager chat endpoints
    path('api/portfolio/conversation/', views.portfolio_conversation, name='portfolio_conversation'),
    path('api/portfolio/conversation/<int:conversation_id>/messages/', views.portfolio_conversation_messages, name='portfolio_conversation_messages'),
    path('api/portfolio/conversation/<int:conversation_id>/chat/', views.portfolio_chat, name='portfolio_chat'),
    path('api/portfolio/conversation/<int:conversation_id>/stream/', views.portfolio_stream_chat, name='portfolio_stream_chat'),
    
    # Meeting management
    path('meetings/', views.meeting_list, name='meeting_list'),
    path('meetings/<int:meeting_id>/', views.meeting_detail, name='meeting_detail'),
    path('meetings/<int:meeting_id>/cancel/', views.cancel_meeting, name='cancel_meeting'),
    
    # Meeting BaaS webhook
    path('webhook/meeting/<int:meeting_id>/', views.meeting_webhook, name='meeting_webhook'),
] 