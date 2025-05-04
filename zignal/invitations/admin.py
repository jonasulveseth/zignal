from django.contrib import admin
from .models import Invitation, EarlySignup

@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ('email', 'invitation_type', 'get_target', 'role', 'status', 'created_at', 'expires_at')
    list_filter = ('invitation_type', 'status', 'company', 'project')
    search_fields = ('email', 'company__name', 'project__name')
    readonly_fields = ('id', 'created_at', 'expires_at', 'accepted_at')
    
    fieldsets = (
        (None, {
            'fields': ('id', 'email', 'invitation_type', 'company', 'project', 'role', 'message')
        }),
        ('Status', {
            'fields': ('status', 'created_at', 'expires_at', 'accepted_at')
        }),
        ('Users', {
            'fields': ('invited_by', 'accepted_by')
        }),
    )
    
    def get_target(self, obj):
        if obj.invitation_type == 'company':
            return obj.company.name
        return obj.project.name
    get_target.short_description = 'Target'
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.invited_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(EarlySignup)
class EarlySignupAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'company', 'created_at', 'contacted')
    list_filter = ('created_at', 'contacted')
    search_fields = ('first_name', 'last_name', 'email', 'company')
    readonly_fields = ('id', 'created_at')
    
    fieldsets = (
        (None, {
            'fields': ('id', 'first_name', 'last_name', 'email', 'company')
        }),
        ('Status', {
            'fields': ('created_at', 'contacted')
        }),
    )
