from django.db import models
from members.models import Member


class SermonSeries(models.Model):
    """Series of related sermons."""

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    cover_image = models.ImageField(
        upload_to="sermons/series_covers/", blank=True, null=True
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_date"]
        verbose_name = "Sermon Series"
        verbose_name_plural = "Sermon Series"

    def __str__(self):
        return self.title


class Sermon(models.Model):
    """Individual sermon/message records."""

    SCRIPTURE_BOOK_CHOICES = [
        ("genesis", "Genesis"),
        ("exodus", "Exodus"),
        ("leviticus", "Leviticus"),
        ("numbers", "Numbers"),
        ("deuteronomy", "Deuteronomy"),
        ("joshua", "Joshua"),
        ("judges", "Judges"),
        ("ruth", "Ruth"),
        ("1_samuel", "1 Samuel"),
        ("2_samuel", "2 Samuel"),
        ("1_kings", "1 Kings"),
        ("2_kings", "2 Kings"),
        ("1_chronicles", "1 Chronicles"),
        ("2_chronicles", "2 Chronicles"),
        ("ezra", "Ezra"),
        ("nehemiah", "Nehemiah"),
        ("esther", "Esther"),
        ("job", "Job"),
        ("psalms", "Psalms"),
        ("proverbs", "Proverbs"),
        ("ecclesiastes", "Ecclesiastes"),
        ("song_of_solomon", "Song of Solomon"),
        ("isaiah", "Isaiah"),
        ("jeremiah", "Jeremiah"),
        ("lamentations", "Lamentations"),
        ("ezekiel", "Ezekiel"),
        ("daniel", "Daniel"),
        ("hosea", "Hosea"),
        ("joel", "Joel"),
        ("amos", "Amos"),
        ("obadiah", "Obadiah"),
        ("jonah", "Jonah"),
        ("micah", "Micah"),
        ("nahum", "Nahum"),
        ("habakkuk", "Habakkuk"),
        ("zephaniah", "Zephaniah"),
        ("haggai", "Haggai"),
        ("zechariah", "Zechariah"),
        ("malachi", "Malachi"),
        ("matthew", "Matthew"),
        ("mark", "Mark"),
        ("luke", "Luke"),
        ("john", "John"),
        ("acts", "Acts"),
        ("romans", "Romans"),
        ("1_corinthians", "1 Corinthians"),
        ("2_corinthians", "2 Corinthians"),
        ("galatians", "Galatians"),
        ("ephesians", "Ephesians"),
        ("philippians", "Philippians"),
        ("colossians", "Colossians"),
        ("1_thessalonians", "1 Thessalonians"),
        ("2_thessalonians", "2 Thessalonians"),
        ("1_timothy", "1 Timothy"),
        ("2_timothy", "2 Timothy"),
        ("titus", "Titus"),
        ("philemon", "Philemon"),
        ("hebrews", "Hebrews"),
        ("james", "James"),
        ("1_peter", "1 Peter"),
        ("2_peter", "2 Peter"),
        ("1_john", "1 John"),
        ("2_john", "2 John"),
        ("3_john", "3 John"),
        ("jude", "Jude"),
        ("revelation", "Revelation"),
    ]

    title = models.CharField(max_length=300)
    subtitle = models.CharField(max_length=300, blank=True)
    series = models.ForeignKey(
        SermonSeries,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sermons",
    )

    # Speaker Information
    speaker = models.ForeignKey(
        Member,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sermons_preached",
    )
    guest_speaker_name = models.CharField(max_length=200, blank=True)
    guest_speaker_bio = models.TextField(blank=True)

    # Scripture References
    primary_scripture_book = models.CharField(
        max_length=30, choices=SCRIPTURE_BOOK_CHOICES, blank=True
    )
    primary_scripture_chapter = models.PositiveIntegerField(null=True, blank=True)
    primary_scripture_verse_start = models.PositiveIntegerField(null=True, blank=True)
    primary_scripture_verse_end = models.PositiveIntegerField(null=True, blank=True)
    additional_scriptures = models.TextField(
        blank=True, help_text="Additional scripture references"
    )

    # Content
    summary = models.TextField(blank=True)
    full_text = models.TextField(blank=True, help_text="Full sermon manuscript")
    key_points = models.TextField(blank=True, help_text="Main points of the sermon")
    notes = models.TextField(blank=True)

    # Event/Delivery Information
    event = models.ForeignKey(
        "events.Event",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sermons",
    )
    sermon_date = models.DateField()

    # Media
    audio_file = models.FileField(
        upload_to="sermons/audio/", blank=True, null=True
    )
    audio_url = models.URLField(blank=True)
    video_file = models.FileField(
        upload_to="sermons/video/", blank=True, null=True
    )
    video_url = models.URLField(blank=True)
    video_embed_code = models.TextField(
        blank=True, help_text="YouTube/Vimeo embed code"
    )
    presentation_file = models.FileField(
        upload_to="sermons/presentations/", blank=True, null=True
    )
    thumbnail_image = models.ImageField(
        upload_to="sermons/thumbnails/", blank=True, null=True
    )

    # Metadata
    duration_minutes = models.PositiveIntegerField(null=True, blank=True)
    file_size_mb = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )
    is_featured = models.BooleanField(default=False)
    is_published = models.BooleanField(default=True)
    view_count = models.PositiveIntegerField(default=0)
    download_count = models.PositiveIntegerField(default=0)

    # Tags and Topics
    topics = models.CharField(
        max_length=500,
        blank=True,
        help_text="Comma-separated list of topics",
    )
    tags = models.CharField(
        max_length=500,
        blank=True,
        help_text="Comma-separated list of tags",
    )

    # Recording Details
    recorded_by = models.ForeignKey(
        Member,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recorded_sermons",
    )
    recording_notes = models.TextField(blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-sermon_date", "-created_at"]
        verbose_name = "Sermon"
        verbose_name_plural = "Sermons"

    def __str__(self):
        return f"{self.title} - {self.sermon_date}"

    @property
    def primary_scripture_reference(self):
        if self.primary_scripture_book:
            book = self.get_primary_scripture_book_display()
            ref = f"{book} {self.primary_scripture_chapter}"
            if self.primary_scripture_verse_start:
                ref += f":{self.primary_scripture_verse_start}"
                if self.primary_scripture_verse_end:
                    ref += f"-{self.primary_scripture_verse_end}"
            return ref
        return ""

    @property
    def speaker_name(self):
        if self.speaker:
            return self.speaker.full_name
        return self.guest_speaker_name


class SermonNote(models.Model):
    """Additional notes/resources for sermons."""

    NOTE_TYPE_CHOICES = [
        ("study_guide", "Study Guide"),
        ("discussion_questions", "Discussion Questions"),
        ("handout", "Handout"),
        ("transcript", "Transcript"),
        ("slides", "Slides"),
        ("other", "Other"),
    ]

    sermon = models.ForeignKey(
        Sermon, on_delete=models.CASCADE, related_name="additional_notes"
    )
    title = models.CharField(max_length=200)
    note_type = models.CharField(
        max_length=30, choices=NOTE_TYPE_CHOICES, default="other"
    )
    content = models.TextField(blank=True)
    file = models.FileField(upload_to="sermons/notes/", blank=True, null=True)
    is_downloadable = models.BooleanField(default=True)
    download_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["note_type", "title"]
        verbose_name = "Sermon Note"
        verbose_name_plural = "Sermon Notes"

    def __str__(self):
        return f"{self.sermon.title} - {self.title}"


class BibleStudyMaterial(models.Model):
    """Bible study materials and resources."""

    MATERIAL_TYPE_CHOICES = [
        ("curriculum", "Curriculum"),
        ("workbook", "Workbook"),
        ("leader_guide", "Leader Guide"),
        ("video_series", "Video Series"),
        ("devotional", "Devotional"),
        ("other", "Other"),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    material_type = models.CharField(
        max_length=30, choices=MATERIAL_TYPE_CHOICES, default="other"
    )
    author = models.CharField(max_length=200, blank=True)
    scripture_focus = models.TextField(blank=True)
    number_of_lessons = models.PositiveIntegerField(default=1)
    duration_weeks = models.PositiveIntegerField(null=True, blank=True)

    # Files
    cover_image = models.ImageField(
        upload_to="study_materials/covers/", blank=True, null=True
    )
    file = models.FileField(upload_to="study_materials/files/", blank=True, null=True)
    external_link = models.URLField(blank=True)

    # Status
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]
        verbose_name = "Bible Study Material"
        verbose_name_plural = "Bible Study Materials"

    def __str__(self):
        return self.title
