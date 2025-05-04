import uuid
from django.db import models
from django.utils import timezone

class Support(models.Model):
    """
    Model for storing support/contact form submissions
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    name = models.CharField(max_length=100)
    email = models.EmailField()
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = "Support Request"
        verbose_name_plural = "Support Requests"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.title}"
