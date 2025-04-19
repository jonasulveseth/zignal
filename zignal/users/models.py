from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """
    Custom User model extending Django's AbstractUser.
    
    This allows for adding additional fields and methods to the User model
    while maintaining compatibility with Django's authentication system.
    """
    # Additional fields
    bio = models.TextField(_("Bio"), blank=True)
    phone_number = models.CharField(_("Phone number"), max_length=20, blank=True)
    profile_picture = models.ImageField(_("Profile picture"), upload_to='profile_pictures/', blank=True, null=True)
    
    # User type field with choices for different user roles
    USER_TYPE_CHOICES = (
        ('admin', _('Admin')),
        ('portfolio_manager', _('Portfolio Manager')),
        ('company_user', _('Company User')),
    )
    user_type = models.CharField(
        _("User type"), 
        max_length=20, 
        choices=USER_TYPE_CHOICES,
        default='company_user'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")
    
    def __str__(self):
        return self.username
    
    @property
    def full_name(self):
        """
        Returns the person's full name.
        """
        return f"{self.first_name} {self.last_name}".strip() or self.username
