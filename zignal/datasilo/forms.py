from django import forms
from .models import DataSilo, DataFile
import os


class DataSiloForm(forms.ModelForm):
    """Form for creating and updating DataSilo objects"""
    
    class Meta:
        model = DataSilo
        fields = ['name', 'description', 'project', 'company']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Apply Tailwind CSS classes to all form fields
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500'
        
        # If user is provided, filter projects and companies based on permissions
        if self.user:
            from projects.models import Project
            from companies.models import Company
            
            user_projects = Project.objects.filter(members=self.user)
            user_companies = Company.objects.filter(members=self.user)
            
            self.fields['project'].queryset = user_projects
            self.fields['company'].queryset = user_companies
    
    def clean(self):
        """Ensure either project or company is provided, but not both"""
        cleaned_data = super().clean()
        project = cleaned_data.get('project')
        company = cleaned_data.get('company')
        
        if not project and not company:
            raise forms.ValidationError("Either project or company must be selected")
        
        if project and company:
            raise forms.ValidationError("Only one of project or company can be selected")
        
        return cleaned_data


class DataFileForm(forms.ModelForm):
    """Form for uploading files to a DataSilo"""
    
    class Meta:
        model = DataFile
        fields = ['description', 'file', 'file_type']  # Remove name from visible fields
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        self.data_silo = kwargs.pop('data_silo', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Hide name field - we'll set it automatically from the file
        if 'name' in self.fields:
            del self.fields['name']
        
        # Apply Tailwind CSS classes to all form fields
        for field_name, field in self.fields.items():
            if field_name == 'file':
                field.widget.attrs['class'] = 'hidden'  # We'll use a custom file input UI
            else:
                field.widget.attrs['class'] = 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500'
    
    def save(self, commit=True):
        """Save the form and create file relationship with the data silo"""
        try:
            # Configure Redis SSL if needed
            import os
            import redis
            import ssl
            from redis.connection import ConnectionPool
            
            # Check if we're using Redis with SSL
            redis_url = os.environ.get('REDIS_URL', '')
            if redis_url.startswith('rediss://'):
                # Configure SSL settings
                ssl_settings = {
                    'ssl_cert_reqs': ssl.CERT_NONE,
                    'ssl_check_hostname': False
                }
                
                # Apply settings to any existing connection pools
                pools = getattr(ConnectionPool, '_connection_pool_cache', {})
                for url, pool in pools.items():
                    if url.startswith('rediss://'):
                        pool.connection_kwargs.update(ssl_settings)
                        
        except Exception as e:
            print(f"Redis SSL configuration in form save: {str(e)}")
            
        # Get or create the model instance
        instance = super().save(False)
        
        # Ensure data_silo is assigned - this is the critical part
        if self.data_silo:
            instance.data_silo = self.data_silo
            
        # Set user if provided and not already set - use uploaded_by, not created_by
        if self.user and not instance.uploaded_by:
            instance.uploaded_by = self.user
            
        # Auto-generate name from file if name is empty
        if not instance.name and instance.file:
            # Extract filename without extension
            import os
            filename = os.path.basename(instance.file.name)
            instance.name = os.path.splitext(filename)[0]
            
        # Make sure data_silo is set before saving - validation
        if not instance.data_silo:
            raise ValueError("DataFile has no data_silo")
            
        # Save the instance if commit is True
        if commit:
            instance.save()
            
        return instance 