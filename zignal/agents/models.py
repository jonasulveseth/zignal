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
    
    # TODO: Add relations to Project model when created
    # project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, related_name='agents')
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
