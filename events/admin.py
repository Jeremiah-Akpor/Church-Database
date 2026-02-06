from datetime import date, datetime, timedelta
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote

from django.contrib import admin
from django.conf import settings
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import path, reverse
from django.utils.text import get_valid_filename
from django.utils.html import format_html
from django.db import models
from unfold.contrib.forms.widgets import WysiwygWidget
from unfold.admin import ModelAdmin
from unfold.admin import StackedInline
from unfold.widgets import UnfoldAdminImageFieldWidget, UnfoldAdminTextInputWidget

from .forms import EventForm
from .models import (
    Event,
    EventAttendance,
    EventOccurrence,
    EventRegistration,
)


IMAGE_PREVIEW_OVERRIDES = {
    models.ImageField: {"widget": UnfoldAdminImageFieldWidget},
}
DATE_TIME_OVERRIDES = {
    models.DateField: {"widget": UnfoldAdminTextInputWidget(attrs={"type": "date"})},
    models.TimeField: {"widget": UnfoldAdminTextInputWidget(attrs={"type": "time"})},
    models.DateTimeField: {
        "widget": UnfoldAdminTextInputWidget(attrs={"type": "datetime-local"})
    },
    models.TextField: {"widget": WysiwygWidget},
}
EVENT_ADMIN_OVERRIDES = {**IMAGE_PREVIEW_OVERRIDES, **DATE_TIME_OVERRIDES}


class _ReportLabHTMLRenderer(HTMLParser):
    """Render editor HTML into ReportLab-safe paragraph markup."""

    INLINE_TAGS = {"b": "b", "strong": "b", "i": "i", "em": "i", "u": "u"}
    HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
    BLOCK_TAGS = {"p", "div", "section", "article"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.list_stack: list[dict[str, int | str]] = []
        self.in_heading = False

    def _append_break(self, force: bool = False) -> None:
        if not self.out:
            return
        if force or not self.out[-1].endswith("<br/>"):
            self.out.append("<br/>")

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag == "br":
            self._append_break()
            return
        if tag == "ol":
            self.list_stack.append({"type": "ol", "index": 0})
            self._append_break(force=True)
            return
        if tag == "ul":
            self.list_stack.append({"type": "ul", "index": 0})
            self._append_break(force=True)
            return
        if tag == "li":
            self._append_break(force=True)
            if self.list_stack and self.list_stack[-1]["type"] == "ol":
                self.list_stack[-1]["index"] = int(self.list_stack[-1]["index"]) + 1
                self.out.append(f"{self.list_stack[-1]['index']}. ")
            else:
                self.out.append("• ")
            return
        if tag in self.HEADING_TAGS:
            self._append_break(force=True)
            self.out.append("<b>")
            self.in_heading = True
            return
        mapped = self.INLINE_TAGS.get(tag)
        if mapped:
            self.out.append(f"<{mapped}>")

    def handle_endtag(self, tag):
        tag = tag.lower()
        mapped = self.INLINE_TAGS.get(tag)
        if mapped:
            self.out.append(f"</{mapped}>")
            return
        if tag in self.HEADING_TAGS:
            if self.in_heading:
                self.out.append("</b>")
                self.in_heading = False
            self._append_break(force=True)
            self._append_break(force=True)
            return
        if tag in {"ol", "ul"}:
            if self.list_stack:
                self.list_stack.pop()
            self._append_break(force=True)
            return
        if tag == "li":
            self._append_break(force=True)
            return
        if tag in self.BLOCK_TAGS:
            self._append_break(force=True)
            self._append_break()

    def handle_data(self, data):
        if data:
            self.out.append(escape(data))

    def handle_entityref(self, name):
        self.out.append(f"&{name};")

    def handle_charref(self, name):
        self.out.append(f"&#{name};")

    def rendered(self) -> str:
        rendered = "".join(self.out).strip()
        while "<br/><br/><br/><br/>" in rendered:
            rendered = rendered.replace("<br/><br/><br/><br/>", "<br/><br/>")
        return rendered


def _to_reportlab_paragraph_html(value: str) -> str:
    if not value:
        return ""
    parser = _ReportLabHTMLRenderer()
    parser.feed(str(value))
    return parser.rendered()


class EventOccurrenceInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        event = self.instance
        is_recurring = bool(event.is_recurring)
        start_date = event.start_date
        recurrence_until = event.recurrence_until

        has_occurrence_input = False

        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue
            if form.cleaned_data.get("DELETE"):
                continue

            occurrence_date = form.cleaned_data.get("occurrence_date")
            if not occurrence_date:
                continue

            has_occurrence_input = True

            if not is_recurring:
                raise ValidationError(
                    "Occurrences can only be edited when 'is recurring' is enabled."
                )

            if start_date and occurrence_date < start_date:
                raise ValidationError(
                    "Occurrence date cannot be earlier than event start date."
                )
            if recurrence_until and occurrence_date > recurrence_until:
                raise ValidationError(
                    "Occurrence date cannot be later than recurrence end date."
                )

        if is_recurring and has_occurrence_input and not recurrence_until:
            raise ValidationError(
                "Set a recurrence end date before adding occurrences."
            )


class EventAttendanceInline(StackedInline):
    """Inline for event attendances."""

    model = EventAttendance
    formfield_overrides = DATE_TIME_OVERRIDES
    extra = 1
    autocomplete_fields = ["member"]


class EventRegistrationInline(StackedInline):
    """Inline for event registrations."""

    model = EventRegistration
    formfield_overrides = DATE_TIME_OVERRIDES
    extra = 1
    autocomplete_fields = ["member"]


class EventOccurrenceInline(StackedInline):
    """Inline for generated recurrence dates."""

    model = EventOccurrence
    formset = EventOccurrenceInlineFormSet
    formfield_overrides = DATE_TIME_OVERRIDES
    extra = 1
    show_change_link = True
    autocomplete_fields = ["leader"]
    verbose_name_plural = "Recurrence Occurrences"
    fields = [
        "occurrence_date",
        "start_time",
        "end_time",
        "leader",
        "is_cancelled",
        "notes",
    ]

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)

        if obj and obj.start_date:
            date_widget_attrs = (
                formset.form.base_fields["occurrence_date"].widget.attrs
            )
            date_widget_attrs["min"] = obj.start_date.isoformat()
            if obj.recurrence_until:
                date_widget_attrs["max"] = obj.recurrence_until.isoformat()

        return formset


@admin.register(Event)
class EventAdmin(ModelAdmin):
    """Admin configuration for Event model."""
    form = EventForm
    formfield_overrides = EVENT_ADMIN_OVERRIDES
    inlines = [EventOccurrenceInline, EventAttendanceInline, EventRegistrationInline]
    actions = ["generate_next_three_months_occurrences"]

    list_display = [
        "title",
        "event_type",
        "start_date",
        "start_time",
        "is_recurring",
        "occurrence_count",
        "schedule_pdf_link",
        "location",
        "expected_attendees",
        "actual_attendees",
        "is_public",
    ]
    list_filter = [
        "event_type",
        "is_public",
        "requires_registration",
        "is_recurring",
        "start_date",
    ]
    search_fields = ["title", "description", "location", "address"]
    readonly_fields = [
        "actual_attendees",
        "schedule_pdf_link",
        "created_at",
        "updated_at",
    ]
    autocomplete_fields = ["organizer", "speakers"]
    date_hierarchy = "start_date"

    class Media:
        js = ("events/admin/event_occurrence_toggle.js",)

    fieldsets = (
        ("Event Information", {
            "fields": (
                "title",
                "description",
                "event_outline",
                "event_type",
                "banner_image",
            ),
        }),
        ("Date and Time", {
            "fields": (
                ("start_date", "end_date"),
                ("start_time", "end_time"),
            ),
        }),
        ("Location", {
            "fields": ("location", "address", "is_online", "online_link"),
        }),
        ("Organization", {
            "fields": (
                "organizer",
                "speakers",
                "expected_attendees",
                "actual_attendees",
            ),
        }),
        ("Registration", {
            "fields": (
                "requires_registration",
                "registration_deadline",
            ),
        }),
        
        ("Media", {
            "fields": ("attachments",),
            "classes": ("collapse",),
        }),
        ("Settings", {
            "fields": ("is_public",),
        }),
        ("Metadata", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
        ("Recurrence", {
            "fields": (
                "is_recurring",
                "recurrence_pattern",
                "recurrence_weekday",
                "recurrence_until",
                "schedule_pdf_link",
            ),
        }),
    )

    def actual_attendees(self, obj):
        return obj.actual_attendees
    actual_attendees.short_description = "Actual Attendees"

    def occurrence_count(self, obj):
        return obj.occurrences.count()

    occurrence_count.short_description = "Occurrences"

    def schedule_pdf_link(self, obj):
        if not obj or not obj.pk:
            return "Save this event first to enable PDF generation."
        url = reverse("admin:events_event_schedule_pdf", args=[obj.pk])
        default_month = obj.start_date.strftime("%Y-%m")
        button_classes = (
            "font-medium flex group items-center gap-2 px-3 py-2 relative "
            "rounded-default justify-center whitespace-nowrap cursor-pointer "
            "border border-base-200 bg-primary-600 border-transparent text-white "
            "w-fit"
        )
        return format_html(
            '<a class="{}" href="{}?month={}" target="_blank" rel="noopener noreferrer">Generate Schedule PDF</a>',
            button_classes,
            url,
            default_month,
        )

    schedule_pdf_link.short_description = "Schedule PDF"

    @admin.action(description="Generate occurrences for next 3 months")
    def generate_next_three_months_occurrences(self, request, queryset):
        start = date.today().replace(day=1)
        month = start.month + 3
        year = start.year + ((month - 1) // 12)
        month = ((month - 1) % 12) + 1
        end_date = date(year, month, 1) - timedelta(days=1)

        total_created = 0
        for event in queryset.filter(is_recurring=True):
            total_created += event.generate_occurrences(
                range_start=start,
                range_end=end_date,
            )
        self.message_user(request, f"Created {total_created} occurrences.")

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:event_id>/schedule-pdf/",
                self.admin_site.admin_view(self.schedule_pdf_view),
                name="events_event_schedule_pdf",
            ),
        ]
        return custom_urls + urls

    def schedule_pdf_view(self, request, event_id):
        event = get_object_or_404(Event, pk=event_id)

        month_raw = request.GET.get("month")
        if month_raw:
            try:
                month_start = datetime.strptime(month_raw, "%Y-%m").date().replace(day=1)
            except ValueError:
                month_start = event.start_date.replace(day=1)
        else:
            month_start = event.start_date.replace(day=1)

        if month_start.month == 12:
            next_month = month_start.replace(year=month_start.year + 1, month=1, day=1)
        else:
            next_month = month_start.replace(month=month_start.month + 1, day=1)
        month_end_date = next_month - timedelta(days=1)

        if event.is_recurring:
            event.generate_occurrences(
                range_start=month_start,
                range_end=month_end_date,
            )

        occurrences_qs = (
            event.occurrences.filter(
                occurrence_date__gte=month_start,
                occurrence_date__lte=month_end_date,
            )
            .select_related("leader")
            .order_by("occurrence_date")
        )
        occurrences = list(occurrences_qs)
        if (
            event.recurrence_pattern in {"weekly", "biweekly"}
            and event.recurrence_weekday is not None
        ):
            occurrences = [
                occurrence
                for occurrence in occurrences
                if occurrence.occurrence_date.weekday() == event.recurrence_weekday
            ]

        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
            from reportlab.platypus import (
                Image,
                PageBreak,
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

        response = HttpResponse(content_type="application/pdf")
        safe_base = get_valid_filename(f"{event.title}_{month_start:%Y_%m}")
        fallback_name = "event_schedule"
        safe_base = safe_base or fallback_name
        ascii_filename = "".join(
            ch for ch in safe_base if ch.isascii() and (ch.isalnum() or ch in "._-")
        ) or fallback_name
        utf8_filename = quote(f"{safe_base}.pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="{ascii_filename}.pdf"; '
            f"filename*=UTF-8''{utf8_filename}"
        )

        doc = SimpleDocTemplate(
            response,
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36,
        )
        styles = getSampleStyleSheet()
        table_cell_style = ParagraphStyle(
            "EventScheduleCell",
            parent=styles["Normal"],
            fontSize=9,
            leading=11,
            wordWrap="CJK",
        )
        table_head_style = ParagraphStyle(
            "EventScheduleHead",
            parent=styles["Normal"],
            fontSize=10,
            leading=12,
        )
        story = []

        def append_logo(target_story):
            if event.banner_image and getattr(event.banner_image, "path", None):
                try:
                    logo = Image(event.banner_image.path, width=130, height=130)
                    target_story.append(logo)
                    target_story.append(Spacer(1, 12))
                    return
                except Exception:
                    pass

            static_logo = (
                Path(settings.BASE_DIR) / "staticfiles" / "customfiles" / "logo.png"
            )
            if static_logo.exists():
                try:
                    logo = Image(str(static_logo), width=130, height=130)
                    target_story.append(logo)
                    target_story.append(Spacer(1, 12))
                except Exception:
                    pass

        append_logo(story)

        story.append(Paragraph(event.title, styles["Title"]))
        story.append(Spacer(1, 12))
        story.append(Paragraph(month_start.strftime("%B %Y"), styles["Heading2"]))
        story.append(Spacer(1, 12))

        organizer_name = event.organizer.full_name if event.organizer else "N/A"
        event_end_date = event.end_date.strftime("%Y-%m-%d") if event.end_date else "-"
        event_end_time = event.end_time.strftime("%H:%M") if event.end_time else "-"
        recurrence_label = (
            event.get_recurrence_pattern_display() if event.is_recurring and event.recurrence_pattern else "Not recurring"
        )
        recurrence_day_label = (
            event.get_recurrence_weekday_display()
            if event.recurrence_weekday is not None
            else "-"
        )
        recurrence_until_label = (
            event.recurrence_until.strftime("%Y-%m-%d") if event.recurrence_until else "-"
        )
        registration_label = "Yes" if event.requires_registration else "No"
        online_label = "Yes" if event.is_online else "No"

        summary_rows = [
            [Paragraph("Event type", table_head_style), Paragraph(event.get_event_type_display(), table_cell_style)],
            [Paragraph("Organizer", table_head_style), Paragraph(organizer_name, table_cell_style)],
            [Paragraph("Location", table_head_style), Paragraph(event.location, table_cell_style)],
            [Paragraph("Online event", table_head_style), Paragraph(online_label, table_cell_style)],
            [Paragraph("Date range", table_head_style), Paragraph(f"{event.start_date:%Y-%m-%d} to {event_end_date}", table_cell_style)],
            [Paragraph("Time range", table_head_style), Paragraph(f"{event.start_time:%H:%M} to {event_end_time}", table_cell_style)],
            [Paragraph("Recurrence", table_head_style), Paragraph(recurrence_label, table_cell_style)],
            [Paragraph("Recurrence day", table_head_style), Paragraph(recurrence_day_label, table_cell_style)],
            [Paragraph("Recurrence until", table_head_style), Paragraph(recurrence_until_label, table_cell_style)],
            [Paragraph("Requires registration", table_head_style), Paragraph(registration_label, table_cell_style)],
        ]
        summary_table = Table(summary_rows, colWidths=[120, 380])
        summary_table.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(summary_table)
        story.append(Spacer(1, 14))

        rows = [[
            Paragraph("Date", table_head_style),
            Paragraph("Day", table_head_style),
            Paragraph("Start Time", table_head_style),
            Paragraph("End Time", table_head_style),
            Paragraph("Leaders", table_head_style),
            Paragraph("Notes", table_head_style),
        ]]
        for occurrence in occurrences:
            leaders = occurrence.leader.full_name if occurrence.leader else ""
            notes = _to_reportlab_paragraph_html(occurrence.notes or "")
            start_time = occurrence.start_time.strftime("%H:%M") if occurrence.start_time else ""
            end_time = occurrence.end_time.strftime("%H:%M") if occurrence.end_time else ""
            rows.append(
                [
                    Paragraph(occurrence.occurrence_date.strftime("%Y-%m-%d"), table_cell_style),
                    Paragraph(occurrence.day_name, table_cell_style),
                    Paragraph(start_time, table_cell_style),
                    Paragraph(end_time, table_cell_style),
                    Paragraph(leaders, table_cell_style),
                    Paragraph(notes, table_cell_style),
                ]
            )

        if len(rows) == 1:
            story.append(Paragraph("No event occurrences generated for this month.", styles["Normal"]))
        else:
            table = Table(
                rows,
                repeatRows=1,
                colWidths=[60, 50, 50, 50, 90, 220],
            )
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )
            story.append(table)

        outline_html = _to_reportlab_paragraph_html(event.event_outline or "")
        outline_has_content = bool(outline_html.replace("<br/>", "").strip())
        if outline_has_content:
            story.append(PageBreak())
            append_logo(story)
            story.append(Paragraph("Event Outline", styles["Title"]))
            story.append(Spacer(1, 8))
            story.append(Paragraph(event.title, styles["Heading2"]))
            story.append(Spacer(1, 4))
            story.append(
                Paragraph(
                    f"Date: {event.start_date:%Y-%m-%d}",
                    styles["Normal"],
                )
            )
            story.append(Spacer(1, 12))
            story.append(Paragraph(outline_html, table_cell_style))

        doc.build(story)
        return response

@admin.register(EventOccurrence)
class EventOccurrenceAdmin(ModelAdmin):
    formfield_overrides = DATE_TIME_OVERRIDES
    list_display = [
        "event",
        "occurrence_date",
        "day_name",
        "leaders_display",
        "is_cancelled",
    ]
    list_filter = ["occurrence_date", "is_cancelled", "event"]
    search_fields = [
        "event__title",
        "notes",
        "leader__first_name",
        "leader__last_name",
    ]
    autocomplete_fields = ["event", "leader"]


@admin.register(EventAttendance)
class EventAttendanceAdmin(ModelAdmin):
    """Admin configuration for EventAttendance model."""
    formfield_overrides = DATE_TIME_OVERRIDES

    list_display = [
        "event",
        "get_attendee_name",
        "is_present",
        "check_in_time",
    ]
    list_filter = ["is_present", "check_in_time", "event"]
    search_fields = [
        "event__title",
        "member__first_name",
        "member__last_name",
        "visitor_name",
        "visitor_email",
    ]
    autocomplete_fields = ["event", "member", "registered_by"]
    readonly_fields = ["check_in_time"]

    def get_attendee_name(self, obj):
        if obj.member:
            return obj.member.full_name
        return obj.visitor_name or "Anonymous"
    get_attendee_name.short_description = "Attendee"


@admin.register(EventRegistration)
class EventRegistrationAdmin(ModelAdmin):
    """Admin configuration for EventRegistration model."""
    formfield_overrides = DATE_TIME_OVERRIDES

    list_display = [
        "event",
        "get_registrant_name",
        "number_of_guests",
        "status",
        "registered_at",
    ]
    list_filter = ["status", "registered_at", "event"]
    search_fields = [
        "event__title",
        "member__first_name",
        "member__last_name",
        "guest_name",
        "guest_email",
    ]
    autocomplete_fields = ["event", "member"]
    readonly_fields = ["registered_at"]

    def get_registrant_name(self, obj):
        if obj.member:
            return obj.member.full_name
        return obj.guest_name or "Anonymous"
    get_registrant_name.short_description = "Registrant"
