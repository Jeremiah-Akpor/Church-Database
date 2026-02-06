from datetime import date, timedelta
from pathlib import Path

from django.contrib import admin
from django.contrib.admin import helpers
from django.conf import settings
from django.db import models
from django.http import HttpResponse
from unfold.contrib.forms.widgets import WysiwygWidget
from unfold.admin import ModelAdmin
from unfold.admin import StackedInline
from unfold.widgets import UnfoldAdminTextInputWidget

from .models import DonationCategory, Donation, Pledge, PledgePayment

DATE_TIME_OVERRIDES = {
    models.DateField: {"widget": UnfoldAdminTextInputWidget(attrs={"type": "date"})},
    models.TimeField: {"widget": UnfoldAdminTextInputWidget(attrs={"type": "time"})},
    models.DateTimeField: {
        "widget": UnfoldAdminTextInputWidget(attrs={"type": "datetime-local"})
    },
    models.TextField: {"widget": WysiwygWidget},
}


class PledgePaymentInline(StackedInline):
    """Inline for pledge payments."""

    model = PledgePayment
    formfield_overrides = DATE_TIME_OVERRIDES
    extra = 1
    autocomplete_fields = ["donation"]


@admin.register(DonationCategory)
class DonationCategoryAdmin(ModelAdmin):
    """Admin configuration for DonationCategory model."""
    formfield_overrides = DATE_TIME_OVERRIDES

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
    formfield_overrides = DATE_TIME_OVERRIDES
    actions_on_top = True
    actions_on_bottom = True
    actions_selection_counter = False
    actions = [
        "generate_pdf_selected_rows",
        "generate_pdf_this_month",
        "generate_pdf_last_1_month",
        "generate_pdf_last_1_month_including_this_month",
        "generate_pdf_last_3_months",
        "generate_pdf_last_3_months_including_this_month",
        "generate_pdf_last_6_months",
        "generate_pdf_last_6_months_including_this_month",
        "generate_pdf_last_9_months",
        "generate_pdf_last_9_months_including_this_month",
        "generate_pdf_current_year",
    ]
    actions_without_selection = {
        "generate_pdf_this_month",
        "generate_pdf_last_1_month",
        "generate_pdf_last_1_month_including_this_month",
        "generate_pdf_last_3_months",
        "generate_pdf_last_3_months_including_this_month",
        "generate_pdf_last_6_months",
        "generate_pdf_last_6_months_including_this_month",
        "generate_pdf_last_9_months",
        "generate_pdf_last_9_months_including_this_month",
        "generate_pdf_current_year",
    }

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

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if db_field.name == "donation_date" and formfield and formfield.widget:
            formfield.widget.attrs["max"] = date.today().isoformat()
        return formfield

    def get_donor_name(self, obj):
        if obj.member:
            return obj.member.full_name
        if obj.anonymous_donor_name:
            return f"{obj.anonymous_donor_name} (Anonymous)"
        return "Anonymous"
    get_donor_name.short_description = "Donor"

    def _build_donation_pdf_response(
        self,
        queryset,
        period_code: str,
        period_display: str,
        period_range_display: str,
        category_label: str,
    ):
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
            from reportlab.platypus import (
                Paragraph,
                SimpleDocTemplate,
                Spacer,
                Table,
                TableStyle,
            )
        except ImportError:
            return HttpResponse(
                "reportlab is required for PDF generation. Install with: pipenv install reportlab",
                status=500,
            )

        queryset = queryset.order_by("donation_date", "created_at")
        total = queryset.total_amount()

        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="donations_{period_code}.pdf"'
        )

        doc = SimpleDocTemplate(response, pagesize=A4)
        styles = getSampleStyleSheet()
        table_cell_style = ParagraphStyle(
            "DonationTableCell",
            parent=styles["Normal"],
            fontSize=9,
            leading=11,
            wordWrap="CJK",
        )
        table_head_style = ParagraphStyle(
            "DonationTableHead",
            parent=styles["Normal"],
            fontSize=10,
            leading=12,
        )
        story = []

        logo_path = Path(settings.BASE_DIR) / "staticfiles" / "customfiles" / "logo.png"
        if logo_path.exists():
            try:
                from reportlab.platypus import Image

                story.append(Image(str(logo_path), width=110, height=110))
                story.append(Spacer(1, 8))
            except Exception:
                pass

        story.append(Paragraph("Donation Entries Report", styles["Title"]))
        story.append(Spacer(1, 10))
        story.append(Paragraph(f"Type: {category_label}", styles["Normal"]))
        story.append(Paragraph(f"Period: {period_display}", styles["Normal"]))
        story.append(Paragraph(f"Date range: {period_range_display}", styles["Normal"]))
        story.append(Paragraph(f"Entries: {queryset.count()}", styles["Normal"]))
        story.append(Paragraph(f"Total: {total}", styles["Normal"]))
        story.append(Spacer(1, 12))

        rows = [[
            Paragraph("Date", table_head_style),
            Paragraph("Donor", table_head_style),
            Paragraph("Amount", table_head_style),
            Paragraph("Method", table_head_style),
            Paragraph("Receipt", table_head_style),
        ]]

        for donation in queryset:
            if donation.member:
                donor = donation.member.full_name
            elif donation.anonymous_donor_name:
                donor = donation.anonymous_donor_name
            else:
                donor = "Anonymous"

            rows.append(
                [
                    Paragraph(donation.donation_date.strftime("%Y-%m-%d"), table_cell_style),
                    Paragraph(donor, table_cell_style),
                    Paragraph(f"{donation.amount} {donation.currency}", table_cell_style),
                    Paragraph(donation.get_payment_method_display(), table_cell_style),
                    Paragraph(donation.receipt_number, table_cell_style),
                ]
            )

        if len(rows) == 1:
            rows.append([
                Paragraph("-", table_cell_style),
                Paragraph("No entries found", table_cell_style),
                Paragraph("-", table_cell_style),
                Paragraph("-", table_cell_style),
                Paragraph("-", table_cell_style),
            ])

        table = Table(rows, repeatRows=1, colWidths=[70, 150, 85, 110, 125])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (2, 1), (2, -1), "RIGHT"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(table)
        doc.build(story)
        return response

    def _apply_category_filter_from_request(self, request, queryset):
        category_value = request.GET.get("category__id__exact")
        if not category_value:
            return queryset, "All donations"

        try:
            category_id = int(category_value)
        except (TypeError, ValueError):
            return queryset, "All donations"

        category = DonationCategory.objects.filter(id=category_id).first()
        label = category.name if category else "All donations"
        return queryset.filter(category_id=category_id), label

    def response_action(self, request, queryset):
        action = request.POST.get("action")
        selected = request.POST.getlist(helpers.ACTION_CHECKBOX_NAME)

        if action in self.actions_without_selection and not selected:
            func = self.get_actions(request).get(action, (None, None, None))[0]
            if func is None:
                return super().response_action(request, queryset)
            response = func(self, request, queryset.none())
            if response:
                return response
            return None

        return super().response_action(request, queryset)

    def _month_start(self, input_date: date) -> date:
        return input_date.replace(day=1)

    def _shift_month(self, input_date: date, months: int) -> date:
        month_index = input_date.year * 12 + (input_date.month - 1) + months
        year, month_zero = divmod(month_index, 12)
        return date(year, month_zero + 1, 1)

    def _calendar_previous_months_range(self, months: int) -> tuple[date, date]:
        current_month_start = self._month_start(date.today())
        start = self._shift_month(current_month_start, -months)
        end = current_month_start - timedelta(days=1)
        return start, end

    def _calendar_previous_months_with_current_range(
        self,
        months: int,
    ) -> tuple[date, date]:
        current_month_start = self._month_start(date.today())
        start = self._shift_month(current_month_start, -months)
        end = date.today()
        return start, end

    def _format_date_range(self, start: date, end: date) -> str:
        return f"{start.strftime('%B %d, %Y')} to {end.strftime('%B %d, %Y')}"

    @admin.action(description="Generate PDF (selected rows)")
    def generate_pdf_selected_rows(self, request, queryset):
        filtered_queryset, category_label = self._apply_category_filter_from_request(
            request,
            queryset,
        )
        if filtered_queryset.exists():
            start = filtered_queryset.order_by("donation_date").first().donation_date
            end = filtered_queryset.order_by("-donation_date").first().donation_date
            range_display = self._format_date_range(start, end)
        else:
            range_display = "No date range (no entries)"
        return self._build_donation_pdf_response(
            filtered_queryset,
            period_code="selected_rows",
            period_display="Selected rows",
            period_range_display=range_display,
            category_label=category_label,
        )

    @admin.action(description="Generate PDF (this month)")
    def generate_pdf_this_month(self, request, queryset):
        today = date.today()
        start = self._month_start(today)
        end = today
        base_queryset = self.model.objects.filter(
            donation_date__gte=start,
            donation_date__lte=end,
        )
        filtered_queryset, category_label = self._apply_category_filter_from_request(
            request,
            base_queryset,
        )
        return self._build_donation_pdf_response(
            filtered_queryset,
            period_code=f"this_month_{today.year}_{today.month:02d}",
            period_display="This month",
            period_range_display=self._format_date_range(start, end),
            category_label=category_label,
        )

    @admin.action(description="Generate PDF (last 1 month)")
    def generate_pdf_last_1_month(self, request, queryset):
        start, end = self._calendar_previous_months_range(1)
        base_queryset = self.model.objects.filter(
            donation_date__gte=start,
            donation_date__lte=end,
        )
        filtered_queryset, category_label = self._apply_category_filter_from_request(
            request,
            base_queryset,
        )
        return self._build_donation_pdf_response(
            filtered_queryset,
            period_code="last_1_month",
            period_display="Last 1 month",
            period_range_display=self._format_date_range(start, end),
            category_label=category_label,
        )

    @admin.action(description="Generate PDF (last 1 month, incl. this month)")
    def generate_pdf_last_1_month_including_this_month(self, request, queryset):
        start, end = self._calendar_previous_months_with_current_range(1)
        base_queryset = self.model.objects.filter(
            donation_date__gte=start,
            donation_date__lte=end,
        )
        filtered_queryset, category_label = self._apply_category_filter_from_request(
            request,
            base_queryset,
        )
        return self._build_donation_pdf_response(
            filtered_queryset,
            period_code="last_1_month_including_this_month",
            period_display="Last 1 month (including this month)",
            period_range_display=self._format_date_range(start, end),
            category_label=category_label,
        )

    @admin.action(description="Generate PDF (last 3 months)")
    def generate_pdf_last_3_months(self, request, queryset):
        start, end = self._calendar_previous_months_range(3)
        base_queryset = self.model.objects.filter(
            donation_date__gte=start,
            donation_date__lte=end,
        )
        filtered_queryset, category_label = self._apply_category_filter_from_request(
            request,
            base_queryset,
        )
        return self._build_donation_pdf_response(
            filtered_queryset,
            period_code="last_3_months",
            period_display="Last 3 months",
            period_range_display=self._format_date_range(start, end),
            category_label=category_label,
        )

    @admin.action(description="Generate PDF (last 3 months, incl. this month)")
    def generate_pdf_last_3_months_including_this_month(self, request, queryset):
        start, end = self._calendar_previous_months_with_current_range(3)
        base_queryset = self.model.objects.filter(
            donation_date__gte=start,
            donation_date__lte=end,
        )
        filtered_queryset, category_label = self._apply_category_filter_from_request(
            request,
            base_queryset,
        )
        return self._build_donation_pdf_response(
            filtered_queryset,
            period_code="last_3_months_including_this_month",
            period_display="Last 3 months (including this month)",
            period_range_display=self._format_date_range(start, end),
            category_label=category_label,
        )

    @admin.action(description="Generate PDF (last 6 months)")
    def generate_pdf_last_6_months(self, request, queryset):
        start, end = self._calendar_previous_months_range(6)
        base_queryset = self.model.objects.filter(
            donation_date__gte=start,
            donation_date__lte=end,
        )
        filtered_queryset, category_label = self._apply_category_filter_from_request(
            request,
            base_queryset,
        )
        return self._build_donation_pdf_response(
            filtered_queryset,
            period_code="last_6_months",
            period_display="Last 6 months",
            period_range_display=self._format_date_range(start, end),
            category_label=category_label,
        )

    @admin.action(description="Generate PDF (last 6 months, incl. this month)")
    def generate_pdf_last_6_months_including_this_month(self, request, queryset):
        start, end = self._calendar_previous_months_with_current_range(6)
        base_queryset = self.model.objects.filter(
            donation_date__gte=start,
            donation_date__lte=end,
        )
        filtered_queryset, category_label = self._apply_category_filter_from_request(
            request,
            base_queryset,
        )
        return self._build_donation_pdf_response(
            filtered_queryset,
            period_code="last_6_months_including_this_month",
            period_display="Last 6 months (including this month)",
            period_range_display=self._format_date_range(start, end),
            category_label=category_label,
        )

    @admin.action(description="Generate PDF (last 9 months)")
    def generate_pdf_last_9_months(self, request, queryset):
        start, end = self._calendar_previous_months_range(9)
        base_queryset = self.model.objects.filter(
            donation_date__gte=start,
            donation_date__lte=end,
        )
        filtered_queryset, category_label = self._apply_category_filter_from_request(
            request,
            base_queryset,
        )
        return self._build_donation_pdf_response(
            filtered_queryset,
            period_code="last_9_months",
            period_display="Last 9 months",
            period_range_display=self._format_date_range(start, end),
            category_label=category_label,
        )

    @admin.action(description="Generate PDF (last 9 months, incl. this month)")
    def generate_pdf_last_9_months_including_this_month(self, request, queryset):
        start, end = self._calendar_previous_months_with_current_range(9)
        base_queryset = self.model.objects.filter(
            donation_date__gte=start,
            donation_date__lte=end,
        )
        filtered_queryset, category_label = self._apply_category_filter_from_request(
            request,
            base_queryset,
        )
        return self._build_donation_pdf_response(
            filtered_queryset,
            period_code="last_9_months_including_this_month",
            period_display="Last 9 months (including this month)",
            period_range_display=self._format_date_range(start, end),
            category_label=category_label,
        )

    @admin.action(description="Generate PDF (current year)")
    def generate_pdf_current_year(self, request, queryset):
        current_year = date.today().year
        start = date(current_year, 1, 1)
        end = date.today()
        base_queryset = self.model.objects.filter(
            donation_date__gte=start,
            donation_date__lte=end,
        )
        filtered_queryset, category_label = self._apply_category_filter_from_request(
            request,
            base_queryset,
        )
        return self._build_donation_pdf_response(
            filtered_queryset,
            period_code=f"year_{current_year}",
            period_display=f"Year {current_year}",
            period_range_display=self._format_date_range(start, end),
            category_label=category_label,
        )


@admin.register(Pledge)
class PledgeAdmin(ModelAdmin):
    """Admin configuration for Pledge model."""
    formfield_overrides = DATE_TIME_OVERRIDES

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
    formfield_overrides = DATE_TIME_OVERRIDES

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
