from django import forms
from .models import DataSilo, DataFile


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
        fields = ['name', 'description', 'file', 'file_type']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        self.data_silo = kwargs.pop('data_silo', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Apply Tailwind CSS classes to all form fields
        for field_name, field in self.fields.items():
            if field_name == 'file':
                field.widget.attrs['class'] = 'hidden'  # We'll use a custom file input UI
            else:
                field.widget.attrs['class'] = 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500'
    
    def save(self, commit=True):
        """Save the form and associate with the data silo"""
        instance = super().save(commit=False)
        
        if self.data_silo:
            instance.data_silo = self.data_silo
            
            # Set project and company from the data silo
            if self.data_silo.project:
                instance.project = self.data_silo.project
            if self.data_silo.company:
                instance.company = self.data_silo.company
        
        if self.user:
            instance.uploaded_by = self.user
        
        if commit:
            instance.save()
        
        return instance 