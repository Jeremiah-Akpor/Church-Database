from django.contrib import admin
from django.db import models
from unfold.contrib.forms.widgets import WysiwygWidget
from unfold.admin import ModelAdmin
from unfold.admin import StackedInline
from unfold.widgets import UnfoldAdminTextInputWidget

from .models import SermonSeries, Sermon, SermonNote, BibleStudyMaterial

DATE_TIME_OVERRIDES = {
    models.DateField: {"widget": UnfoldAdminTextInputWidget(attrs={"type": "date"})},
    models.TimeField: {"widget": UnfoldAdminTextInputWidget(attrs={"type": "time"})},
    models.DateTimeField: {
        "widget": UnfoldAdminTextInputWidget(attrs={"type": "datetime-local"})
    },
    models.TextField: {"widget": WysiwygWidget},
}


class SermonInline(StackedInline):
    """Inline for sermons in a series."""

    model = Sermon
    formfield_overrides = DATE_TIME_OVERRIDES
    extra = 1
    fields = [
        "title",
        "sermon_date",
        "speaker",
        "primary_scripture_book",
        "is_published",
    ]
    autocomplete_fields = ["speaker"]


class SermonNoteInline(StackedInline):
    """Inline for sermon notes."""

    model = SermonNote
    formfield_overrides = DATE_TIME_OVERRIDES
    extra = 1


@admin.register(SermonSeries)
class SermonSeriesAdmin(ModelAdmin):
    """Admin configuration for SermonSeries model."""
    formfield_overrides = DATE_TIME_OVERRIDES

    list_display = [
        "title",
        "start_date",
        "end_date",
        "sermon_count",
        "is_active",
    ]
    list_filter = ["is_active", "start_date"]
    search_fields = ["title", "description"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [SermonInline]

    fieldsets = (
        ("Series Information", {
            "fields": ("title", "description", "cover_image"),
        }),
        ("Dates", {
            "fields": (("start_date", "end_date"),),
        }),
        ("Status", {
            "fields": ("is_active",),
        }),
        ("Metadata", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    def sermon_count(self, obj):
        return obj.sermons.count()
    sermon_count.short_description = "Sermons"


@admin.register(Sermon)
class SermonAdmin(ModelAdmin):
    """Admin configuration for Sermon model."""
    formfield_overrides = DATE_TIME_OVERRIDES

    list_display = [
        "title",
        "speaker_name",
        "series",
        "primary_scripture_book",
        "sermon_date",
        "duration_minutes",
        "view_count",
        "is_featured",
        "is_published",
    ]
    list_filter = [
        "is_published",
        "is_featured",
        "primary_scripture_book",
        "sermon_date",
        "series",
    ]
    search_fields = [
        "title",
        "subtitle",
        "summary",
        "full_text",
        "guest_speaker_name",
        "member__first_name",
        "member__last_name",
    ]
    readonly_fields = [
        "primary_scripture_reference",
        "view_count",
        "download_count",
        "created_at",
        "updated_at",
    ]
    autocomplete_fields = ["speaker", "event", "series", "recorded_by"]
    date_hierarchy = "sermon_date"
    inlines = [SermonNoteInline]

    fieldsets = (
        ("Basic Information", {
            "fields": (
                "title",
                "subtitle",
                "series",
            ),
        }),
        ("Speaker", {
            "fields": (
                "speaker",
                "guest_speaker_name",
                "guest_speaker_bio",
            ),
        }),
        ("Scripture", {
            "fields": (
                ("primary_scripture_book", "primary_scripture_chapter"),
                ("primary_scripture_verse_start", "primary_scripture_verse_end"),
                "primary_scripture_reference",
                "additional_scriptures",
            ),
        }),
        ("Content", {
            "fields": (
                "summary",
                "full_text",
                "key_points",
            ),
            "classes": ("collapse",),
        }),
        ("Event Information", {
            "fields": (
                "event",
                "sermon_date",
            ),
        }),
        ("Audio", {
            "fields": (
                "audio_file",
                "audio_url",
                "duration_minutes",
            ),
            "classes": ("collapse",),
        }),
        ("Video", {
            "fields": (
                "video_file",
                "video_url",
                "video_embed_code",
            ),
            "classes": ("collapse",),
        }),
        ("Media", {
            "fields": (
                "presentation_file",
                "thumbnail_image",
                "file_size_mb",
            ),
            "classes": ("collapse",),
        }),
        ("Categorization", {
            "fields": (
                "topics",
                "tags",
            ),
            "classes": ("collapse",),
        }),
        ("Statistics", {
            "fields": (
                "view_count",
                "download_count",
            ),
        }),
        ("Status", {
            "fields": (
                "is_featured",
                "is_published",
            ),
        }),
        ("Recording", {
            "fields": (
                "recorded_by",
                "recording_notes",
            ),
            "classes": ("collapse",),
        }),
        ("Metadata", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    def speaker_name(self, obj):
        return obj.speaker_name
    speaker_name.short_description = "Speaker"


@admin.register(SermonNote)
class SermonNoteAdmin(ModelAdmin):
    """Admin configuration for SermonNote model."""
    formfield_overrides = DATE_TIME_OVERRIDES

    list_display = [
        "title",
        "sermon",
        "note_type",
        "is_downloadable",
        "download_count",
        "created_at",
    ]
    list_filter = ["note_type", "is_downloadable", "created_at"]
    search_fields = ["title", "content", "sermon__title"]
    autocomplete_fields = ["sermon"]
    readonly_fields = ["download_count", "created_at", "updated_at"]


@admin.register(BibleStudyMaterial)
class BibleStudyMaterialAdmin(ModelAdmin):
    """Admin configuration for BibleStudyMaterial model."""
    formfield_overrides = DATE_TIME_OVERRIDES

    list_display = [
        "title",
        "material_type",
        "author",
        "number_of_lessons",
        "is_active",
        "is_featured",
    ]
    list_filter = [
        "material_type",
        "is_active",
        "is_featured",
        "created_at",
    ]
    search_fields = ["title", "description", "author", "scripture_focus"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        ("Material Information", {
            "fields": (
                "title",
                "description",
                "material_type",
                "author",
            ),
        }),
        ("Content", {
            "fields": (
                "scripture_focus",
                "number_of_lessons",
                "duration_weeks",
            ),
        }),
        ("Files", {
            "fields": (
                "cover_image",
                "file",
                "external_link",
            ),
        }),
        ("Status", {
            "fields": (
                "is_active",
                "is_featured",
            ),
        }),
        ("Metadata", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )
