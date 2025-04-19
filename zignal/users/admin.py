from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User


class UserAdmin(BaseUserAdmin):
    """
    Custom UserAdmin for our custom User model.
    """
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name", "email", "bio", "phone_number", "profile_picture")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("User type"), {"fields": ("user_type",)}),
        (_("Important dates"), {"fields": ("last_login", "date_joined", "created_at", "updated_at")}),
    )
    readonly_fields = ["created_at", "updated_at"]
    list_display = ["username", "email", "first_name", "last_name", "user_type", "is_staff"]
    list_filter = ["is_staff", "is_superuser", "is_active", "user_type", "groups"]
    search_fields = ["username", "first_name", "last_name", "email"]


admin.site.register(User, UserAdmin)
