
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):

    ordering = ["email"]

    list_display = [
        "email",
        "first_name",
        "last_name",
        "role",
        "instructor_status",
        "is_active",
    ]

    list_filter = [
        "role",
        "instructor_status",
        "is_active",
    ]

    search_fields = [
        "email",
        "first_name",
        "last_name",
    ]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Personal Information",
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "profile_image",
                    "bio",
                )
            },
        ),
        (
            "LMS Permissions",
            {
                "fields": (
                    "role",
                    "instructor_status",
                )
            },
        ),
        (
            "Django Permissions",
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
        (
            "Important Dates",
            {
                "fields": (
                    "last_login",
                    "date_joined",
                )
            },
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "password1",
                    "password2",
                    "role",
                    "instructor_status",
                    "is_staff",
                    "is_superuser",
                ),
            },
        ),
    )

    filter_horizontal = (
        "groups",
        "user_permissions",
    )


from .models import InstructorApplication
@admin.register(InstructorApplication)
class InstructorApplicationAdmin(admin.ModelAdmin):

    list_display = [
        "user",
        "expertise",
        "status",
        "created_at",
        "reviewed_by",
    ]

    list_filter = [
        "status",
        "created_at",
    ]

    search_fields = [
        "user__email",
        "expertise",
    ]

    readonly_fields = [
        "created_at",
        "updated_at",
        "reviewed_at",
    ]