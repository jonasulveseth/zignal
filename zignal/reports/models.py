from django.db import models
from django.conf import settings
from django.utils.text import slugify
from projects.models import Project

class ReportTemplate(models.Model):
    """
    Model representing a report template that can be used to generate reports
    """
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    description = models.TextField(blank=True, null=True)
    template_content = models.TextField(help_text="Template content with placeholders for data")
    
    # Constraints on what projects can use this template
    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.CASCADE,
        related_name='report_templates',
        null=True,
        blank=True,
        help_text="If set, this template is available only for this company"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        related_name='created_report_templates',
        null=True
    )
    
    class Meta:
        verbose_name = 'Report Template'
        verbose_name_plural = 'Report Templates'
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Report(models.Model):
    """
    Model representing a generated report
    """
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('generating', 'Generating'),
        ('generated', 'Generated'),
        ('failed', 'Failed'),
        ('archived', 'Archived'),
    )
    
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    description = models.TextField(blank=True, null=True)
    content = models.TextField(blank=True, null=True, help_text="The generated report content")
    template = models.ForeignKey(
        ReportTemplate,
        on_delete=models.SET_NULL,
        related_name='reports',
        null=True,
        blank=True,
        help_text="The template used to generate this report"
    )
    project = models.ForeignKey(
        Project, 
        on_delete=models.CASCADE,
        related_name='reports',
        null=True,
        blank=True
    )
    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.CASCADE,
        related_name='reports',
        null=True,
        blank=True
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    parameters = models.JSONField(default=dict, blank=True, help_text="Parameters used to generate the report")
    
    # PDF generation
    pdf_file = models.FileField(upload_to='reports/pdfs/', null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    generated_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        related_name='created_reports',
        null=True
    )
    
    class Meta:
        verbose_name = 'Report'
        verbose_name_plural = 'Reports'
        ordering = ['-updated_at']
        constraints = [
            models.CheckConstraint(
                check=(models.Q(project__isnull=False) | models.Q(company__isnull=False)),
                name='report_project_or_company_not_null'
            )
        ]
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)


class ReportSchedule(models.Model):
    """
    Model for scheduling recurring report generation
    """
    FREQUENCY_CHOICES = (
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
    )
    
    name = models.CharField(max_length=255)
    template = models.ForeignKey(
        ReportTemplate,
        on_delete=models.CASCADE,
        related_name='schedules'
    )
    project = models.ForeignKey(
        Project, 
        on_delete=models.CASCADE,
        related_name='report_schedules',
        null=True,
        blank=True
    )
    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.CASCADE,
        related_name='report_schedules',
        null=True,
        blank=True
    )
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    day_of_week = models.IntegerField(null=True, blank=True, help_text="Day of week (0-6, 0 is Monday) for weekly schedules")
    day_of_month = models.IntegerField(null=True, blank=True, help_text="Day of month for monthly schedules")
    parameters = models.JSONField(default=dict, blank=True, help_text="Parameters to use for the report")
    is_active = models.BooleanField(default=True)
    
    last_run = models.DateTimeField(null=True, blank=True)
    next_run = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        related_name='created_report_schedules',
        null=True
    )
    
    class Meta:
        verbose_name = 'Report Schedule'
        verbose_name_plural = 'Report Schedules'
        ordering = ['name']
        constraints = [
            models.CheckConstraint(
                check=(models.Q(project__isnull=False) | models.Q(company__isnull=False)),
                name='schedule_project_or_company_not_null'
            )
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_frequency_display()})"
