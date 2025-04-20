from django.db import models
from django.conf import settings
from django.utils.text import slugify
from companies.models import Company

class Project(models.Model):
    """
    Model representing a project in the system
    """
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('completed', 'Completed'),
        ('archived', 'Archived'),
    )
    
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    description = models.TextField(blank=True, null=True)
    company = models.ForeignKey(
        Company, 
        on_delete=models.CASCADE,
        related_name='projects'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        related_name='created_projects',
        null=True
    )
    
    # Project managers through UserProjectRelation
    
    class Meta:
        verbose_name = 'Project'
        verbose_name_plural = 'Projects'
        ordering = ['-updated_at']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class UserProjectRelation(models.Model):
    """
    Model representing the relationship between users and projects
    """
    ROLE_CHOICES = (
        ('manager', 'Manager'),
        ('member', 'Member'),
        ('viewer', 'Viewer'),
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='project_relations'
    )
    project = models.ForeignKey(
        Project, 
        on_delete=models.CASCADE,
        related_name='user_relations'
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    joined_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'project')
        verbose_name = 'Project Member'
        verbose_name_plural = 'Project Members'
    
    def __str__(self):
        return f"{self.user.email} - {self.project.name} ({self.role})"
