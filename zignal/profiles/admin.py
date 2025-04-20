from django.contrib import admin
from .models import Profile

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'position', 'phone_number', 'created_at', 'updated_at')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'position')
    list_filter = ('email_notifications', 'dark_mode', 'created_at')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'bio', 'position', 'phone_number', 'profile_image')
        }),
        ('Social Media', {
            'fields': ('linkedin_url', 'twitter_url', 'github_url', 'website_url')
        }),
        ('Preferences', {
            'fields': ('email_notifications', 'dark_mode')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at')
        }),
    )
