from django import forms
from django.utils.translation import gettext_lazy as _
from django.db.models import Q
from .models import Report, ReportTemplate, ReportSchedule


class ReportTemplateForm(forms.ModelForm):
    """Form for creating and editing report templates"""
    
    class Meta:
        model = ReportTemplate
        fields = ['name', 'description', 'template_content', 'company']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'template_content': forms.Textarea(attrs={'rows': 15, 'class': 'font-mono'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Apply Tailwind CSS classes to form fields
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.Textarea):
                field.widget.attrs['class'] = 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500'
            else:
                field.widget.attrs['class'] = 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500'
        
        # Filter company choices if user is provided
        if self.user:
            from companies.models import Company
            user_companies = Company.objects.filter(user_relations__user=self.user)
            self.fields['company'].queryset = user_companies
            
        # Help text for template content
        self.fields['template_content'].help_text = _(
            "Use placeholders like {{project.name}} or {{parameters.start_date}} that will be replaced when generating the report."
        )


class ReportForm(forms.ModelForm):
    """Form for creating and editing reports"""
    
    generate_now = forms.BooleanField(
        required=False,
        initial=False,
        label=_("Generate report immediately after creation"),
        widget=forms.CheckboxInput(attrs={'class': 'h-4 w-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500'})
    )
    
    class Meta:
        model = Report
        fields = ['title', 'description', 'template', 'project', 'company', 'parameters']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'parameters': forms.Textarea(attrs={'rows': 5, 'class': 'font-mono'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Apply Tailwind CSS classes to form fields
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.Textarea):
                field.widget.attrs['class'] = 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500'
            elif isinstance(field.widget, forms.CheckboxInput):
                continue  # Skip checkbox as we've already styled it
            else:
                field.widget.attrs['class'] = 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500'
        
        # Filter project and company choices if user is provided
        if self.user:
            from projects.models import Project
            from companies.models import Company
            
            user_projects = Project.objects.filter(user_relations__user=self.user)
            user_companies = Company.objects.filter(user_relations__user=self.user)
            
            self.fields['project'].queryset = user_projects
            self.fields['company'].queryset = user_companies
            
            # Filter templates based on user's companies
            self.fields['template'].queryset = ReportTemplate.objects.filter(
                Q(company__in=user_companies) | Q(company__isnull=True)
            ).distinct()
        
        # Help text for parameters
        self.fields['parameters'].help_text = _(
            "Enter parameters as JSON that will be used to generate the report. E.g., {\"start_date\": \"2023-01-01\", \"end_date\": \"2023-12-31\"}"
        )
        
        # Generate now field should only appear on creation, not on edit
        if self.instance and self.instance.pk:
            self.fields.pop('generate_now', None)
    
    def clean(self):
        """Ensure either project or company is provided, but not both"""
        cleaned_data = super().clean()
        project = cleaned_data.get('project')
        company = cleaned_data.get('company')
        
        if not project and not company:
            raise forms.ValidationError(_("Either project or company must be selected"))
        
        if project and company:
            raise forms.ValidationError(_("Only one of project or company can be selected"))
        
        return cleaned_data


class ReportScheduleForm(forms.ModelForm):
    """Form for creating and editing report schedules"""
    
    class Meta:
        model = ReportSchedule
        fields = ['name', 'template', 'project', 'company', 'frequency', 'day_of_week', 'day_of_month', 'parameters', 'is_active']
        widgets = {
            'parameters': forms.Textarea(attrs={'rows': 5, 'class': 'font-mono'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Apply Tailwind CSS classes to form fields
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.Textarea):
                field.widget.attrs['class'] = 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500'
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'h-4 w-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500'
            else:
                field.widget.attrs['class'] = 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500'
        
        # Filter project and company choices if user is provided
        if self.user:
            from projects.models import Project
            from companies.models import Company
            
            user_projects = Project.objects.filter(user_relations__user=self.user)
            user_companies = Company.objects.filter(user_relations__user=self.user)
            
            self.fields['project'].queryset = user_projects
            self.fields['company'].queryset = user_companies
            
            # Filter templates based on user's companies
            self.fields['template'].queryset = ReportTemplate.objects.filter(
                Q(company__in=user_companies) | Q(company__isnull=True)
            ).distinct()
        
        # Help text
        self.fields['day_of_week'].help_text = _("Required for weekly schedules (0=Monday, 6=Sunday)")
        self.fields['day_of_month'].help_text = _("Required for monthly and quarterly schedules (1-31)")
        self.fields['parameters'].help_text = _(
            "Enter parameters as JSON that will be used to generate the reports. E.g., {\"end_days\": 30}"
        )
    
    def clean(self):
        """Ensure either project or company is provided, but not both, and validate frequency fields"""
        cleaned_data = super().clean()
        project = cleaned_data.get('project')
        company = cleaned_data.get('company')
        frequency = cleaned_data.get('frequency')
        day_of_week = cleaned_data.get('day_of_week')
        day_of_month = cleaned_data.get('day_of_month')
        
        if not project and not company:
            raise forms.ValidationError(_("Either project or company must be selected"))
        
        if project and company:
            raise forms.ValidationError(_("Only one of project or company can be selected"))
        
        # Validate day_of_week for weekly frequency
        if frequency == 'weekly' and (day_of_week is None or day_of_week < 0 or day_of_week > 6):
            self.add_error('day_of_week', _("For weekly schedules, day of week must be between 0 and 6"))
        
        # Validate day_of_month for monthly and quarterly frequency
        if frequency in ['monthly', 'quarterly'] and (day_of_month is None or day_of_month < 1 or day_of_month > 31):
            self.add_error('day_of_month', _("For monthly and quarterly schedules, day of month must be between 1 and 31"))
        
        return cleaned_data 