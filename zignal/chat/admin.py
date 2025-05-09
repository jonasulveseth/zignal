from django.contrib import admin
from .models import Thread, Message

@admin.register(Thread)
class ThreadAdmin(admin.ModelAdmin):
    list_display = ('title', 'company', 'user', 'created_at', 'updated_at')
    list_filter = ('company', 'user', 'created_at')
    search_fields = ('title', 'company__name', 'user__email')
    readonly_fields = ('openai_thread_id', 'created_at', 'updated_at')

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('thread', 'role', 'content_preview', 'timestamp')
    list_filter = ('role', 'timestamp', 'thread__company')
    search_fields = ('content', 'thread__title', 'thread__company__name')
    readonly_fields = ('openai_message_id', 'timestamp')

    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'
