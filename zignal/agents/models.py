from django.db import models
from django.conf import settings

class Agent(models.Model):
    """
    An AI agent associated with a project
    """
    AGENT_TYPES = (
        ('chat', 'Chat Agent'),
        ('report', 'Report Agent'),
        ('meeting', 'Meeting Agent'),
        ('email', 'Email Agent'),
    )
    
    API_VERSIONS = (
        ('chat_completion', 'Chat Completion API'),
        ('assistants', 'Assistants API'),
    )
    
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    agent_type = models.CharField(max_length=20, choices=AGENT_TYPES, default='chat')
    model = models.CharField(max_length=50, default=settings.OPENAI_MODEL)
    temperature = models.FloatField(default=0.7)
    max_tokens = models.IntegerField(default=1000)
    system_prompt = models.TextField(blank=True, null=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # OpenAI Assistants API fields
    api_version = models.CharField(max_length=20, choices=API_VERSIONS, default='chat_completion')
    assistant_id = models.CharField(max_length=255, blank=True, null=True, 
                                  help_text="OpenAI Assistant ID (only used with Assistants API)")
    
    project = models.ForeignKey(
        'projects.Project', 
        on_delete=models.CASCADE, 
        related_name='agents',
        null=True,
        blank=True
    )
    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.CASCADE,
        related_name='agents',
        null=True,
        blank=True
    )
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, 
                                 related_name='created_agents', null=True)
    
    def __str__(self):
        return f"{self.name} ({self.get_agent_type_display()})"
    
    class Meta:
        ordering = ['-created_at']


class Conversation(models.Model):
    """
    A conversation with an AI agent
    """
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='conversations')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='conversations')
    title = models.CharField(max_length=200, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # OpenAI Assistants API fields
    thread_id = models.CharField(max_length=255, blank=True, null=True,
                               help_text="OpenAI Thread ID (only used with Assistants API)")
    
    def __str__(self):
        return f"Conversation {self.id} with {self.agent.name}"
    
    class Meta:
        ordering = ['-updated_at']


class Message(models.Model):
    """
    A message in a conversation
    """
    ROLE_CHOICES = (
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System'),
    )
    
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."
    
    class Meta:
        ordering = ['timestamp']


class MeetingTranscript(models.Model):
    """
    A transcript from a meeting via Meeting BaaS
    """
    MEETING_PLATFORM_CHOICES = (
        ('zoom', 'Zoom'),
        ('teams', 'Microsoft Teams'),
        ('google_meet', 'Google Meet'),
    )
    
    STATUS_CHOICES = (
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    )
    
    meeting_id = models.CharField(max_length=255, unique=True)
    external_meeting_id = models.CharField(max_length=255, blank=True, null=True)
    meeting_title = models.CharField(max_length=255)
    platform = models.CharField(max_length=20, choices=MEETING_PLATFORM_CHOICES)
    meeting_url = models.URLField(max_length=1000)
    scheduled_time = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    
    transcript_raw = models.TextField(blank=True, null=True)
    transcript_summary = models.TextField(blank=True, null=True)
    
    transcript_file = models.FileField(upload_to='meeting_transcripts/', blank=True, null=True)
    recording_url = models.URLField(max_length=1000, blank=True, null=True)
    
    duration_minutes = models.IntegerField(blank=True, null=True)
    
    # Allow connecting to project or company
    project = models.ForeignKey(
        'projects.Project', 
        on_delete=models.SET_NULL,
        related_name='meeting_transcripts',
        null=True,
        blank=True
    )
    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.SET_NULL,
        related_name='meeting_transcripts',
        null=True,
        blank=True
    )
    
    # User who scheduled the meeting
    scheduled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='scheduled_meetings',
        null=True
    )
    
    # Fields for Meeting BaaS integration
    meetingbaas_bot_id = models.CharField(max_length=255, blank=True, null=True)
    meetingbaas_webhook_id = models.CharField(max_length=255, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Create conversation for this meeting
    conversation = models.OneToOneField(
        Conversation,
        on_delete=models.SET_NULL,
        related_name='meeting_transcript',
        null=True,
        blank=True
    )
    
    class Meta:
        ordering = ['-scheduled_time']
        verbose_name = "Meeting Transcript"
        verbose_name_plural = "Meeting Transcripts"
    
    def __str__(self):
        return f"{self.meeting_title} ({self.get_platform_display()}) - {self.get_status_display()}"
