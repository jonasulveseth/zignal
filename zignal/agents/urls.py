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
] 