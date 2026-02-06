from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.admin import StackedInline

from .models import DonationCategory, Donation, Pledge, PledgePayment


class PledgePaymentInline(StackedInline):
    """Inline for pledge payments."""

    model = PledgePayment
    extra = 1
    autocomplete_fields = ["donation"]


@admin.register(DonationCategory)
class DonationCategoryAdmin(ModelAdmin):
    """Admin configuration for DonationCategory model."""

    list_display = [
        "name",
        "is_tax_deductible",
        "target_amount",
        "total_donations",
        "is_active",
    ]
    list_filter = ["is_tax_deductible", "is_active", "created_at"]
    search_fields = ["name", "description"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        ("Category Information", {
            "fields": ("name", "description", "is_tax_deductible", "target_amount"),
        }),
        ("Status", {
            "fields": ("is_active",),
        }),
        ("Metadata", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    def total_donations(self, obj):
        from django.db.models import Sum
        total = obj.donations.filter().aggregate(Sum("amount"))["amount__sum"]
        return total or 0
    total_donations.short_description = "Total Donations"


@admin.register(Donation)
class DonationAdmin(ModelAdmin):
    """Admin configuration for Donation model."""

    list_display = [
        "receipt_number",
        "get_donor_name",
        "category",
        "amount",
        "currency",
        "payment_method",
        "donation_date",
        "frequency",
    ]
    list_filter = [
        "category",
        "payment_method",
        "frequency",
        "is_anonymous",
        "receipt_sent",
        "donation_date",
    ]
    search_fields = [
        "receipt_number",
        "transaction_reference",
        "check_number",
        "member__first_name",
        "member__last_name",
        "anonymous_donor_name",
    ]
    date_hierarchy = "donation_date"
    readonly_fields = [
        "receipt_number",
        "tax_year",
        "created_at",
        "updated_at",
    ]
    autocomplete_fields = ["member", "event", "recorded_by"]

    fieldsets = (
        ("Receipt Information", {
            "fields": ("receipt_number",),
        }),
        ("Donor Information", {
            "fields": (
                "member",
                "anonymous_donor_name",
                "is_anonymous",
            ),
        }),
        ("Donation Details", {
            "fields": (
                "category",
                ("amount", "currency"),
                "payment_method",
                "frequency",
            ),
        }),
        ("Date and Event", {
            "fields": ("donation_date", "event"),
        }),
        ("Payment Details", {
            "fields": (
                "transaction_reference",
                "check_number",
                "bank_name",
                "payment_notes",
            ),
            "classes": ("collapse",),
        }),
        ("Tax Information", {
            "fields": (
                "is_tax_receipt_required",
                "tax_year",
            ),
            "classes": ("collapse",),
        }),
        ("Acknowledgment", {
            "fields": (
                "receipt_sent",
                "receipt_sent_date",
                "thank_you_sent",
            ),
        }),
        ("Notes", {
            "fields": ("notes", "recorded_by"),
            "classes": ("collapse",),
        }),
        ("Metadata", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    def get_donor_name(self, obj):
        if obj.member:
            return obj.member.full_name
        if obj.anonymous_donor_name:
            return f"{obj.anonymous_donor_name} (Anonymous)"
        return "Anonymous"
    get_donor_name.short_description = "Donor"


@admin.register(Pledge)
class PledgeAdmin(ModelAdmin):
    """Admin configuration for Pledge model."""

    list_display = [
        "member",
        "category",
        "amount",
        "currency",
        "frequency",
        "total_paid",
        "balance",
        "percentage_paid",
        "status",
        "pledge_date",
    ]
    list_filter = [
        "status",
        "frequency",
        "category",
        "pledge_date",
    ]
    search_fields = [
        "member__first_name",
        "member__last_name",
        "purpose",
    ]
    readonly_fields = [
        "balance",
        "percentage_paid",
        "created_at",
        "updated_at",
    ]
    autocomplete_fields = ["member", "category"]
    inlines = [PledgePaymentInline]
    date_hierarchy = "pledge_date"

    fieldsets = (
        ("Pledge Information", {
            "fields": (
                "member",
                "category",
                ("amount", "currency"),
                "frequency",
            ),
        }),
        ("Dates", {
            "fields": (
                "pledge_date",
                "start_date",
                "end_date",
            ),
        }),
        ("Status", {
            "fields": (
                "status",
                "total_paid",
                "last_payment_date",
            ),
        }),
        ("Progress", {
            "fields": (
                "balance",
                "percentage_paid",
            ),
        }),
        ("Notes", {
            "fields": ("purpose", "notes"),
            "classes": ("collapse",),
        }),
        ("Metadata", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )


@admin.register(PledgePayment)
class PledgePaymentAdmin(ModelAdmin):
    """Admin configuration for PledgePayment model."""

    list_display = [
        "pledge",
        "get_member_name",
        "amount",
        "payment_date",
    ]
    list_filter = ["payment_date", "created_at"]
    search_fields = [
        "pledge__member__first_name",
        "pledge__member__last_name",
        "notes",
    ]
    autocomplete_fields = ["pledge", "donation"]
    readonly_fields = ["created_at"]
    date_hierarchy = "payment_date"

    def get_member_name(self, obj):
        return obj.pledge.member.full_name if obj.pledge.member else "Unknown"
    get_member_name.short_description = "Member"
