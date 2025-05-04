import uuid
from django.db import models
from django.conf import settings
from django.utils.text import slugify
from projects.models import Project

def file_upload_path(instance, filename):
    """Generate a unique file path for uploaded files"""
    # Skip file extension as we'll use a completely unique filename
    ext = filename.split('.')[-1].lower()
    unique_id = str(uuid.uuid4())
    
    # Handle the case where company or project might not be set yet
    company_slug = None
    project_slug = None
    
    # Get company slug
    if hasattr(instance, 'company') and instance.company:
        company_slug = instance.company.slug
    elif hasattr(instance, 'data_silo') and instance.data_silo and instance.data_silo.company:
        company_slug = instance.data_silo.company.slug
    
    # Get project slug
    if hasattr(instance, 'project') and instance.project:
        project_slug = instance.project.slug
    elif hasattr(instance, 'data_silo') and instance.data_silo and instance.data_silo.project:
        project_slug = instance.data_silo.project.slug
    
    # Handle case when neither company nor project is available
    if not company_slug and not project_slug:
        # Use a default path with just the unique ID
        return f"datasilo/files/{unique_id}.{ext}"
    
    # Create path based on available information
    if project_slug:
        return f"datasilo/{company_slug}/{project_slug}/{unique_id}.{ext}"
    else:
        return f"datasilo/company/{company_slug}/{unique_id}.{ext}"


class DataSilo(models.Model):
    """
    Model representing a data storage container for a project or company
    """
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    description = models.TextField(blank=True, null=True)
    project = models.ForeignKey(
        Project, 
        on_delete=models.CASCADE,
        related_name='data_silos',
        null=True,
        blank=True
    )
    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.CASCADE,
        related_name='data_silos',
        null=True,
        blank=True
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        related_name='created_silos',
        null=True
    )
    
    class Meta:
        verbose_name = 'Data Silo'
        verbose_name_plural = 'Data Silos'
        ordering = ['-updated_at']
        constraints = [
            models.CheckConstraint(
                check=(models.Q(project__isnull=False) | models.Q(company__isnull=False)),
                name='project_or_company_not_null'
            ),
            models.UniqueConstraint(
                fields=['name', 'project'],
                name='unique_name_per_project'
            ),
            models.UniqueConstraint(
                fields=['name', 'company'],
                name='unique_name_per_company'
            )
        ]
    
    def __str__(self):
        if self.project:
            return f"{self.name} - {self.project.name}"
        return f"{self.name} - {self.company.name}"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class DataFile(models.Model):
    """
    Model representing a file stored in a data silo
    """
    FILE_TYPE_CHOICES = (
        ('document', 'Document (PDF, DOC, DOCX, TXT)'),
        ('spreadsheet', 'Spreadsheet (XLS, XLSX, CSV)'),
        ('json', 'JSON'),
        ('other', 'Other'),
    )
    
    STATUS_CHOICES = (
        ('pending', 'Pending Processing'),
        ('processing', 'Processing'),
        ('processed', 'Processed'),
        ('failed', 'Failed Processing'),
    )
    
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    file = models.FileField(upload_to=file_upload_path)
    file_type = models.CharField(max_length=20, choices=FILE_TYPE_CHOICES, default='document')
    content_type = models.CharField(max_length=255, blank=True, null=True)
    size = models.BigIntegerField(default=0)  # Size in bytes
    data_silo = models.ForeignKey(
        DataSilo, 
        on_delete=models.CASCADE,
        related_name='files'
    )
    project = models.ForeignKey(
        Project, 
        on_delete=models.CASCADE,
        related_name='files',
        null=True,
        blank=True
    )
    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.CASCADE,
        related_name='files',
        null=True,
        blank=True
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    processed_at = models.DateTimeField(null=True, blank=True)
    embedding_available = models.BooleanField(default=False)
    
    # OpenAI Vector Store fields
    vector_store_file_id = models.CharField(max_length=255, blank=True, null=True,
                                          help_text="OpenAI Vector Store File ID")
    vector_store_status = models.CharField(max_length=20, blank=True, null=True, default='pending',
                                         choices=[
                                             ('pending', 'Pending Vector Processing'),
                                             ('processing', 'Processing for Vector Store'),
                                             ('processed', 'Added to Vector Store'),
                                             ('failed', 'Failed to Add to Vector Store'),
                                             ('skipped', 'Skipped (Unsupported Format)')
                                         ])
    vector_store_processed_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        related_name='uploaded_files',
        null=True
    )
    
    class Meta:
        verbose_name = 'Data File'
        verbose_name_plural = 'Data Files'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        # Set project and company from the data silo if not provided
        if self.data_silo and not self.project and self.data_silo.project:
            self.project = self.data_silo.project
        if self.data_silo and not self.company and self.data_silo.company:
            self.company = self.data_silo.company
        super().save(*args, **kwargs)
