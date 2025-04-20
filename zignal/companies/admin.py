from django.contrib import admin
from .models import Company, UserCompanyRelation

class UserCompanyRelationInline(admin.TabularInline):
    model = UserCompanyRelation
    extra = 1
    min_num = 1
    autocomplete_fields = ['user']

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'website', 'created_at', 'created_by')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at')
    inlines = [UserCompanyRelationInline]
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'description', 'website', 'logo', 'address')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
    )

@admin.register(UserCompanyRelation)
class UserCompanyRelationAdmin(admin.ModelAdmin):
    list_display = ('user', 'company', 'role', 'joined_at')
    list_filter = ('role', 'company')
    search_fields = ('user__email', 'user__username', 'company__name')
    autocomplete_fields = ['user', 'company']
