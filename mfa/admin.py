from django.contrib import admin

from unfold.admin import ModelAdmin

from .models import UserMFA


@admin.register(UserMFA)
class UserMFAAdmin(ModelAdmin):
    list_display = [
        "user",
        "is_enrolled",
        "require_password_change",
        "enrolled_at",
        "last_verified_at",
    ]
    list_filter = [
        "is_enrolled",
        "require_password_change",
        "enrolled_at",
        "last_verified_at",
    ]
    search_fields = ["user__username", "user__email"]
    readonly_fields = ["created_at", "updated_at", "last_verified_at"]
    fields = [
        "user",
        "is_enrolled",
        "require_password_change",
        "enrolled_at",
        "last_verified_at",
        "created_at",
        "updated_at",
    ]
    actions = ["force_reenroll_next_login"]

    @admin.action(description="Force MFA re-enrollment on next login")
    def force_reenroll_next_login(self, request, queryset):
        updated = queryset.update(
            is_enrolled=False,
            secret="",
            enrolled_at=None,
            last_verified_at=None,
        )
        self.message_user(
            request,
            f"{updated} user MFA profile(s) will be prompted to enroll again at next login.",
        )
