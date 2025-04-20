from django.contrib import admin
from .models import DataSilo, DataFile

class DataFileInline(admin.TabularInline):
    model = DataFile
    extra = 0
    fields = ('name', 'file_type', 'status', 'size', 'uploaded_by', 'created_at')
    readonly_fields = ('status', 'size', 'uploaded_by', 'created_at')
    can_delete = False
    show_change_link = True
    max_num = 10

@admin.register(DataSilo)
class DataSiloAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_owner', 'file_count', 'created_at', 'updated_at')
    search_fields = ('name', 'description', 'project__name', 'company__name')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at')
    autocomplete_fields = ['project', 'company', 'created_by']
    inlines = [DataFileInline]
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'description')
        }),
        ('Ownership', {
            'fields': ('project', 'company')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
    )
    
    def get_owner(self, obj):
        if obj.project:
            return f"Project: {obj.project.name}"
        return f"Company: {obj.company.name}"
    get_owner.short_description = 'Owner'
    
    def file_count(self, obj):
        return obj.files.count()
    file_count.short_description = 'Files'

@admin.register(DataFile)
class DataFileAdmin(admin.ModelAdmin):
    list_display = ('name', 'file_type', 'data_silo', 'status', 'size_display', 'uploaded_by', 'created_at')
    list_filter = ('file_type', 'status', 'data_silo', 'project', 'company')
    search_fields = ('name', 'description', 'data_silo__name')
    readonly_fields = ('content_type', 'size', 'created_at', 'updated_at', 'processed_at', 'embedding_available')
    autocomplete_fields = ['data_silo', 'project', 'company', 'uploaded_by']
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'file', 'file_type')
        }),
        ('Storage', {
            'fields': ('data_silo', 'project', 'company')
        }),
        ('Processing', {
            'fields': ('status', 'processed_at', 'embedding_available')
        }),
        ('File Details', {
            'fields': ('content_type', 'size')
        }),
        ('Metadata', {
            'fields': ('uploaded_by', 'created_at', 'updated_at')
        }),
    )
    
    def size_display(self, obj):
        """Display file size in human-readable format"""
        size = obj.size
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        else:
            return f"{size / (1024 * 1024 * 1024):.1f} GB"
    size_display.short_description = 'Size'
