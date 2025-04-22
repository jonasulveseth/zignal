from django.contrib import admin
from .models import Agent, Conversation, Message, MeetingTranscript

@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = ('name', 'agent_type', 'model', 'active', 'created_at')
    list_filter = ('agent_type', 'active', 'model')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'agent_type', 'active')
        }),
        ('Model Configuration', {
            'fields': ('model', 'temperature', 'max_tokens', 'system_prompt')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
    )


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    fields = ('role', 'content_preview', 'timestamp')
    readonly_fields = ('role', 'content_preview', 'timestamp')
    can_delete = False
    max_num = 20
    
    def content_preview(self, obj):
        return obj.content[:100] + "..." if len(obj.content) > 100 else obj.content
    content_preview.short_description = 'Content'


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('title_display', 'agent', 'user', 'created_at', 'updated_at')
    list_filter = ('agent', 'user')
    search_fields = ('title', 'agent__name', 'user__username')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [MessageInline]
    
    def title_display(self, obj):
        return obj.title or f"Conversation {obj.id}"
    title_display.short_description = 'Title'


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('get_conversation', 'role', 'content_preview', 'timestamp')
    list_filter = ('role', 'conversation__agent')
    search_fields = ('content', 'conversation__title')
    readonly_fields = ('timestamp',)
    
    def get_conversation(self, obj):
        return f"Conversation {obj.conversation.id}"
    get_conversation.short_description = 'Conversation'
    
    def content_preview(self, obj):
        return obj.content[:100] + "..." if len(obj.content) > 100 else obj.content
    content_preview.short_description = 'Content'


@admin.register(MeetingTranscript)
class MeetingTranscriptAdmin(admin.ModelAdmin):
    list_display = ('meeting_title', 'platform', 'scheduled_time', 'status', 'scheduled_by')
    list_filter = ('platform', 'status', 'scheduled_time')
    search_fields = ('meeting_title', 'transcript_raw', 'scheduled_by__username')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Meeting Information', {
            'fields': ('meeting_id', 'external_meeting_id', 'meeting_title', 'platform', 'meeting_url', 
                      'scheduled_time', 'status', 'duration_minutes')
        }),
        ('Transcript', {
            'fields': ('transcript_raw', 'transcript_summary', 'transcript_file', 'recording_url')
        }),
        ('Relations', {
            'fields': ('project', 'company', 'scheduled_by', 'conversation')
        }),
        ('Meeting BaaS', {
            'fields': ('meetingbaas_bot_id', 'meetingbaas_webhook_id')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at')
        }),
    )
