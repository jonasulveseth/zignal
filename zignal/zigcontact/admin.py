from django.contrib import admin
from .models import Support

@admin.register(Support)
class SupportAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'title', 'created_at', 'is_resolved')
    list_filter = ('created_at', 'is_resolved')
    search_fields = ('name', 'email', 'title', 'message')
    readonly_fields = ('id', 'created_at')
    
    fieldsets = (
        (None, {
            'fields': ('id', 'title', 'name', 'email')
        }),
        ('Message', {
            'fields': ('message',)
        }),
        ('Status', {
            'fields': ('created_at', 'is_resolved')
        }),
    )
