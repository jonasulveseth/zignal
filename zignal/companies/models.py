from django.db import models
from django.conf import settings
from django.utils.text import slugify

class Company(models.Model):
    """
    Model representing a company in the system
    """
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    description = models.TextField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    logo = models.ImageField(upload_to='company_logos/', blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    company_email = models.CharField(max_length=255, blank=True, null=True, unique=True, 
                                   help_text="Unique email prefix for receiving emails (e.g., 'acme' will become acme@yourservice.com)")
    
    # OpenAI integration fields
    openai_assistant_id = models.CharField(max_length=255, blank=True, null=True,
                                         help_text="OpenAI Assistant ID for this company")
    openai_vector_store_id = models.CharField(max_length=255, blank=True, null=True,
                                            help_text="OpenAI Vector Store ID for this company")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        related_name='created_companies',
        null=True
    )
    
    # Managers through UserCompanyRelation
    
    class Meta:
        verbose_name = 'Company'
        verbose_name_plural = 'Companies'
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def get_full_email_address(self):
        """
        Get the full email address for receiving emails
        """
        if self.company_email:
            from django.conf import settings
            domain = getattr(settings, 'EMAIL_DOMAIN', 'zignal.com')
            return f"{self.company_email}@{domain}"
        return None


class UserCompanyRelation(models.Model):
    """
    Model representing the relationship between users and companies
    """
    ROLE_CHOICES = (
        ('owner', 'Owner'),
        ('admin', 'Admin'),
        ('member', 'Member'),
        ('viewer', 'Viewer'),
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='company_relations'
    )
    company = models.ForeignKey(
        Company, 
        on_delete=models.CASCADE,
        related_name='user_relations'
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    joined_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'company')
        verbose_name = 'Company Member'
        verbose_name_plural = 'Company Members'
    
    def __str__(self):
        return f"{self.user.email} - {self.company.name} ({self.role})"
