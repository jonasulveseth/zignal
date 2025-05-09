from django.db import models
from django.conf import settings
from companies.models import Company

class Thread(models.Model):
    """
    A thread represents a conversation with a company's AI assistant
    """
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='chat_threads')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chat_threads')
    openai_thread_id = models.CharField(max_length=255, blank=True, null=True,
                                      help_text="OpenAI Thread ID")
    title = models.CharField(max_length=200, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Thread {self.id} - {self.company.name}"
    
    class Meta:
        ordering = ['-updated_at']

class Message(models.Model):
    """
    A message in a thread
    """
    ROLE_CHOICES = (
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System'),
    )
    
    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    openai_message_id = models.CharField(max_length=255, blank=True, null=True,
                                       help_text="OpenAI Message ID")
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."
    
    class Meta:
        ordering = ['timestamp']
