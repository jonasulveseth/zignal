from django.contrib import admin
from .models import ReportTemplate, Report, ReportSchedule

@admin.register(ReportTemplate)
class ReportTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'created_by', 'created_at')
    list_filter = ('company',)
    search_fields = ('name', 'description', 'template_content')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at')
    autocomplete_fields = ['company', 'created_by']
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'description', 'template_content')
        }),
        ('Availability', {
            'fields': ('company',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
    )

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'template', 'get_owner', 'created_at', 'generated_at')
    list_filter = ('status', 'template', 'company', 'project')
    search_fields = ('title', 'description', 'content')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('created_at', 'updated_at', 'generated_at')
    autocomplete_fields = ['template', 'project', 'company', 'created_by']
    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'description', 'content')
        }),
        ('Report Details', {
            'fields': ('template', 'project', 'company', 'status', 'parameters', 'pdf_file')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at', 'generated_at')
        }),
    )
    
    def get_owner(self, obj):
        if obj.project:
            return f"Project: {obj.project.name}"
        return f"Company: {obj.company.name}"
    get_owner.short_description = 'Owner'

@admin.register(ReportSchedule)
class ReportScheduleAdmin(admin.ModelAdmin):
    list_display = ('name', 'template', 'frequency', 'is_active', 'last_run', 'next_run')
    list_filter = ('frequency', 'is_active', 'template', 'company', 'project')
    search_fields = ('name',)
    readonly_fields = ('created_at', 'updated_at', 'last_run', 'next_run')
    autocomplete_fields = ['template', 'project', 'company', 'created_by']
    fieldsets = (
        (None, {
            'fields': ('name', 'template', 'is_active')
        }),
        ('Scope', {
            'fields': ('project', 'company')
        }),
        ('Schedule', {
            'fields': ('frequency', 'day_of_week', 'day_of_month', 'parameters')
        }),
        ('Run Information', {
            'fields': ('last_run', 'next_run')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
    )
