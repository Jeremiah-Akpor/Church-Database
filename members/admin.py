from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group, User
from django.db import models
from django.utils.html import format_html
from unfold.contrib.forms.widgets import WysiwygWidget
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm
from unfold.admin import ModelAdmin
from unfold.admin import StackedInline
from unfold.widgets import UnfoldAdminTextInputWidget

from mfa.models import UserMFA
from .forms import MemberForm
from .models import Department, Member, Family, FamilyMember


admin.site.unregister(User)
admin.site.unregister(Group)

DATE_TIME_OVERRIDES = {
    models.DateField: {"widget": UnfoldAdminTextInputWidget(attrs={"type": "date"})},
    models.TimeField: {"widget": UnfoldAdminTextInputWidget(attrs={"type": "time"})},
    models.DateTimeField: {
        "widget": UnfoldAdminTextInputWidget(attrs={"type": "datetime-local"})
    },
    models.TextField: {"widget": WysiwygWidget},
}


class UserMFAInline(StackedInline):
    model = UserMFA
    can_delete = False
    extra = 0
    max_num = 1
    verbose_name_plural = "Multi-Factor Authentication"
    fields = ["is_enrolled", "enrolled_at", "last_verified_at"]
    readonly_fields = ["enrolled_at", "last_verified_at"]


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    inlines = [UserMFAInline]

    def get_inlines(self, request, obj):
        # Only show MFA inline after the user exists.
        if obj is None:
            return []
        return super().get_inlines(request, obj)


@admin.register(Group)
class GroupAdmin(ModelAdmin, BaseGroupAdmin):
    pass


class FamilyMemberInline(StackedInline):
    """Inline for family members."""

    model = FamilyMember
    formfield_overrides = DATE_TIME_OVERRIDES
    extra = 1
    fields = ["member", "relationship", "is_primary_contact"]


class MemberInline(StackedInline):
    """Inline for members in departments."""

    model = Member.departments.through
    formfield_overrides = DATE_TIME_OVERRIDES
    extra = 1


@admin.register(Department)
class DepartmentAdmin(ModelAdmin):
    """Admin configuration for Department model."""
    formfield_overrides = DATE_TIME_OVERRIDES

    list_display = ["name", "leader", "member_count", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["name", "description"]
    readonly_fields = ["created_at", "updated_at"]
    fieldsets = (
        ("Department Information", {
            "fields": ("name", "description", "leader"),
        }),
        ("Metadata", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    def member_count(self, obj):
        return obj.members.count()
    member_count.short_description = "Members"


@admin.register(Member)
class MemberAdmin(ModelAdmin):
    """Admin configuration for Member model."""
    form = MemberForm
    formfield_overrides = DATE_TIME_OVERRIDES

    list_display = [
        "full_name",
        "email",
        "phone_number",
        "membership_status",
        "is_leader",
        "created_at",
    ]
    list_filter = [
        "membership_status",
        "gender",
        "marital_status",
        "is_leader",
        "departments",
        "created_at",
    ]
    search_fields = [
        "first_name",
        "last_name",
        "email",
        "phone_number",
        "address",
    ]
    readonly_fields = ["age", "full_name", "created_at", "updated_at"] # photo_preview is not readonly because it depends on the photo field which can be edited
    autocomplete_fields = ["departments"]

    fieldsets = (
        ("Personal Information", {
            "fields": (
                "user",
                ("first_name", "last_name"),
                "middle_name",
                "full_name",
                "photo",
                # "photo_preview",
            ),
        }),
        ("Contact Information", {
            "fields": (
                ("email", "phone_number"),
                "address",
                ("city", "state"),
                "country",
            ),
        }),
        ("Personal Details", {
            "fields": (
                "date_of_birth",
                "age",
                "gender",
                "marital_status",
                "occupation",
                "employer",
            ),
        }),
        ("Church Information", {
            "fields": (
                "membership_status",
                "membership_date",
                "baptism_date",
                "baptism_type",
                "departments",
                "is_leader",
                "leadership_position",
            ),
        }),
        ("Emergency Contact", {
            "fields": (
                "emergency_contact_name",
                "emergency_contact_phone",
                "emergency_contact_relationship",
            ),
            "classes": ("collapse",),
        }),
        ("Notes", {
            "fields": ("notes",),
            "classes": ("collapse",),
        }),
        ("Metadata", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    def get_fieldsets(self, request, obj=None):
        """Show user selector only to superusers."""
        fieldsets = super().get_fieldsets(request, obj)
        if request.user.is_superuser:
            return fieldsets

        updated = []
        for title, opts in fieldsets:
            opts = dict(opts)
            fields = []
            for field in opts.get("fields", ()):
                if isinstance(field, tuple):
                    nested = tuple(item for item in field if item != "user")
                    if nested:
                        fields.append(nested)
                elif field != "user":
                    fields.append(field)
            opts["fields"] = tuple(fields)
            updated.append((title, opts))
        return tuple(updated)

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("departments")

    def photo_preview(self, obj):
        if obj and obj.photo:
            return format_html(
                '<img src="{}" alt="Photo preview" style="max-height: 180px; border-radius: 8px;" />',
                obj.photo.url,
            )
        return "No photo uploaded"

    photo_preview.short_description = "Photo Preview"


@admin.register(Family)
class FamilyAdmin(ModelAdmin):
    """Admin configuration for Family model."""
    formfield_overrides = DATE_TIME_OVERRIDES

    list_display = [
        "family_name",
        "family_head",
        "family_type",
        "member_count",
        "anniversary_date",
    ]
    list_filter = ["family_type", "anniversary_date", "created_at"]
    search_fields = ["family_name", "address", "home_phone"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [FamilyMemberInline]

    fieldsets = (
        ("Family Information", {
            "fields": (
                "family_name",
                "family_head",
                "family_type",
                "anniversary_date",
            ),
        }),
        ("Contact Information", {
            "fields": ("address", "home_phone"),
        }),
        ("Metadata", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    def member_count(self, obj):
        return obj.members.count()
    member_count.short_description = "Members"


@admin.register(FamilyMember)
class FamilyMemberAdmin(ModelAdmin):
    """Admin configuration for FamilyMember model."""
    formfield_overrides = DATE_TIME_OVERRIDES

    list_display = ["family", "member", "relationship", "is_primary_contact"]
    list_filter = ["relationship", "is_primary_contact", "created_at"]
    search_fields = ["family__family_name", "member__first_name", "member__last_name"]
    autocomplete_fields = ["family", "member"]
