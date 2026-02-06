from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.admin import StackedInline

from .models import Department, Member, Family, FamilyMember


class FamilyMemberInline(StackedInline):
    """Inline for family members."""

    model = FamilyMember
    extra = 1
    fields = ["member", "relationship", "is_primary_contact"]


class MemberInline(StackedInline):
    """Inline for members in departments."""

    model = Member.departments.through
    extra = 1


@admin.register(Department)
class DepartmentAdmin(ModelAdmin):
    """Admin configuration for Department model."""

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
    readonly_fields = ["age", "full_name", "created_at", "updated_at"]
    filter_horizontal = ["departments"]

    fieldsets = (
        ("Personal Information", {
            "fields": (
                "user",
                ("first_name", "last_name"),
                "middle_name",
                "full_name",
                "photo",
            ),
        }),
        ("Contact Information", {
            "fields": ("email", "phone_number", "address", "city", "state", "country"),
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

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("departments")


@admin.register(Family)
class FamilyAdmin(ModelAdmin):
    """Admin configuration for Family model."""

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

    list_display = ["family", "member", "relationship", "is_primary_contact"]
    list_filter = ["relationship", "is_primary_contact", "created_at"]
    search_fields = ["family__family_name", "member__first_name", "member__last_name"]
    autocomplete_fields = ["family", "member"]
