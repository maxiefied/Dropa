from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("phone", "name", "role", "is_active", "date_joined")
    list_filter = ("role", "is_active")
    search_fields = ("phone", "name")
    ordering = ("-date_joined",)

    fieldsets = (
        (None, {"fields": ("phone", "password")}),
        ("Profile", {"fields": ("name", "role")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("phone", "name", "role", "password1", "password2"),
            },
        ),
    )
