from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.admin import StackedInline

from .models import Event, EventAttendance, EventRegistration

class EventAttendanceInline(StackedInline):
    """Inline for event attendances."""

    model = EventAttendance
    extra = 1
    autocomplete_fields = ["member"]


class EventRegistrationInline(StackedInline):
    """Inline for event registrations."""

    model = EventRegistration
    extra = 1
    autocomplete_fields = ["member"]


@admin.register(Event)
class EventAdmin(ModelAdmin):
    """Admin configuration for Event model."""

    list_display = [
        "title",
        "event_type",
        "start_date",
        "start_time",
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
    readonly_fields = ["actual_attendees", "created_at", "updated_at"]
    filter_horizontal = ["speakers"]
    date_hierarchy = "start_date"

    fieldsets = (
        ("Event Information", {
            "fields": ("title", "description", "event_type", "banner_image"),
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
        ("Recurrence", {
            "fields": ("is_recurring", "recurrence_pattern"),
            "classes": ("collapse",),
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
    )

    def actual_attendees(self, obj):
        return obj.actual_attendees
    actual_attendees.short_description = "Actual Attendees"


@admin.register(EventAttendance)
class EventAttendanceAdmin(ModelAdmin):
    """Admin configuration for EventAttendance model."""

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
