import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.urls import reverse
from django.core.mail import send_mail
from django.template.loader import render_to_string

class Invitation(models.Model):
    """
    Invitation model for inviting users to companies and projects
    """
    INVITATION_TYPE_CHOICES = (
        ('company', 'Company Invitation'),
        ('project', 'Project Invitation'),
    )
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
        ('expired', 'Expired'),
    )
    
    ROLE_CHOICES_COMPANY = (
        ('owner', 'Owner'),
        ('admin', 'Admin'),
        ('member', 'Member'),
        ('viewer', 'Viewer'),
    )
    
    ROLE_CHOICES_PROJECT = (
        ('manager', 'Manager'),
        ('member', 'Member'),
        ('viewer', 'Viewer'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField()
    invitation_type = models.CharField(max_length=10, choices=INVITATION_TYPE_CHOICES)
    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.CASCADE,
        related_name='invitations',
        null=True,
        blank=True
    )
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='invitations',
        null=True,
        blank=True
    )
    role = models.CharField(max_length=20)
    message = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    
    # Who sent the invitation
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_invitations'
    )
    
    # Who accepted the invitation (if any)
    accepted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='accepted_invitations',
        null=True,
        blank=True
    )
    
    def __str__(self):
        if self.invitation_type == 'company':
            return f"Company Invitation to {self.email} for {self.company.name}"
        return f"Project Invitation to {self.email} for {self.project.name}"
    
    def save(self, *args, **kwargs):
        # Set expiration date if not set
        if not self.expires_at:
            # Default expiration is 7 days
            self.expires_at = timezone.now() + timezone.timedelta(days=7)
        
        # Validate company/project is provided based on invitation type
        if self.invitation_type == 'company' and not self.company:
            raise ValueError("Company is required for company invitations")
        if self.invitation_type == 'project' and not self.project:
            raise ValueError("Project is required for project invitations")
        
        # Validate role based on invitation type
        valid_roles = dict(self.ROLE_CHOICES_COMPANY if self.invitation_type == 'company' 
                         else self.ROLE_CHOICES_PROJECT).keys()
        if self.role not in valid_roles:
            raise ValueError(f"Invalid role for {self.invitation_type} invitation")
            
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('invitation_detail', kwargs={'uuid': self.id})
    
    def get_accept_url(self):
        return reverse('invitation_accept', kwargs={'uuid': self.id})
    
    def get_decline_url(self):
        return reverse('invitation_decline', kwargs={'uuid': self.id})
    
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    def mark_as_expired(self):
        self.status = 'expired'
        self.save(update_fields=['status'])
    
    def accept(self, user):
        if self.status != 'pending':
            return False
        
        if self.is_expired():
            self.mark_as_expired()
            return False
        
        self.status = 'accepted'
        self.accepted_at = timezone.now()
        self.accepted_by = user
        
        # Create the relationship based on invitation type
        if self.invitation_type == 'company':
            from companies.models import UserCompanyRelation
            UserCompanyRelation.objects.create(
                user=user,
                company=self.company,
                role=self.role
            )
        else:  # project invitation
            from projects.models import UserProjectRelation
            UserProjectRelation.objects.create(
                user=user,
                project=self.project,
                role=self.role
            )
        
        self.save(update_fields=['status', 'accepted_at', 'accepted_by'])
        return True
    
    def decline(self):
        if self.status != 'pending':
            return False
        
        self.status = 'declined'
        self.save(update_fields=['status'])
        return True
    
    def send_invitation_email(self, request=None):
        """Send invitation email to the invited user"""
        context = {
            'invitation': self,
            'accept_url': request.build_absolute_uri(self.get_accept_url()) if request else self.get_accept_url(),
            'decline_url': request.build_absolute_uri(self.get_decline_url()) if request else self.get_decline_url(),
        }
        
        if self.invitation_type == 'company':
            subject = f"Invitation to join {self.company.name}"
            context['company'] = self.company
        else:
            subject = f"Invitation to join project {self.project.name}"
            context['project'] = self.project
            context['company'] = self.project.company
        
        html_message = render_to_string('invitations/invitation_email.html', context)
        plain_message = render_to_string('invitations/invitation_email_plain.txt', context)
        
        from_email = settings.DEFAULT_FROM_EMAIL
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=from_email,
            recipient_list=[self.email],
            html_message=html_message,
            fail_silently=False,
        )

class EarlySignup(models.Model):
    """
    Model for capturing early signup invites from the landing page
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    company = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    contacted = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = "Early Signup"
        verbose_name_plural = "Early Signups"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.email}"
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"
