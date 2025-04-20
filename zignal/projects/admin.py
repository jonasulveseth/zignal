from django.contrib import admin
from .models import Project, UserProjectRelation

class UserProjectRelationInline(admin.TabularInline):
    model = UserProjectRelation
    extra = 1
    autocomplete_fields = ['user']

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'status', 'start_date', 'end_date', 'created_at')
    list_filter = ('status', 'company')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at')
    autocomplete_fields = ['company', 'created_by']
    inlines = [UserProjectRelationInline]
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'description', 'company', 'status')
        }),
        ('Timeline', {
            'fields': ('start_date', 'end_date')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
    )

@admin.register(UserProjectRelation)
class UserProjectRelationAdmin(admin.ModelAdmin):
    list_display = ('user', 'project', 'role', 'joined_at')
    list_filter = ('role', 'project__company', 'project')
    search_fields = ('user__email', 'user__username', 'project__name')
    autocomplete_fields = ['user', 'project']
