from django import forms
from django.utils.text import slugify
from django.core.validators import RegexValidator
from .models import Company
import uuid

class CompanyForm(forms.ModelForm):
    """
    Form for creating and editing companies
    """
    
    class Meta:
        model = Company
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'shadow-sm focus:ring-blue-500 focus:border-blue-500 block w-full sm:text-sm border-gray-300 rounded-md', 'placeholder': 'Company name'}),
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'shadow-sm focus:ring-blue-500 focus:border-blue-500 block w-full sm:text-sm border-gray-300 rounded-md', 'placeholder': 'Brief description of your company'}),
        }
    
    def clean_name(self):
        """
        Validate that the company name is unique
        """
        name = self.cleaned_data.get('name')
        # Check if a company with this name already exists
        if Company.objects.filter(name=name).exists():
            raise forms.ValidationError("A company with this name already exists.")
        return name
    
    def save(self, commit=True):
        """
        Override save to automatically generate a slug
        """
        instance = super().save(commit=False)
        # Generate a slug from the name
        base_slug = slugify(instance.name)
        
        # Make sure the slug is unique
        if Company.objects.filter(slug=base_slug).exists():
            # If the slug already exists, add a unique identifier
            base_slug = f"{base_slug}-{uuid.uuid4().hex[:6]}"
        
        instance.slug = base_slug
        
        if commit:
            instance.save()
        
        return instance


class CompanyEmailForm(forms.ModelForm):
    """
    Form for setting up company email address for mail receiver
    """
    company_email = forms.CharField(
        max_length=255,
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Z0-9_-]+$',
                message='Email prefix can only contain letters, numbers, underscores, and hyphens',
            ),
        ],
        widget=forms.TextInput(
            attrs={
                'class': 'shadow-sm focus:ring-blue-500 focus:border-blue-500 block w-full sm:text-sm border-gray-300 rounded-md',
                'placeholder': 'Enter email prefix (e.g., company-name)',
            }
        ),
        help_text="This will be your unique email prefix for receiving emails. Only letters, numbers, underscores, and hyphens are allowed.",
    )
    
    class Meta:
        model = Company
        fields = ['company_email']
    
    def clean_company_email(self):
        email_prefix = self.cleaned_data.get('company_email')
        
        # Check if this email is already taken
        if Company.objects.filter(company_email=email_prefix).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This email address is already taken. Please choose another one.")
        
        return email_prefix.lower() 