from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('', views.chat_view, name='chat'),
    path('new/', views.new_chat, name='new_chat'),
    path('force-new-thread/', views.force_new_thread, name='force_new_thread'),
    path('api/threads/', views.thread_list, name='thread_list'),
    path('api/threads/create/', views.create_thread, name='create_thread'),
    path('api/threads/<int:thread_id>/messages/', views.message_list, name='message_list'),
    path('api/threads/<int:thread_id>/send/', views.send_message, name='send_message'),
] 