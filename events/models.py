from datetime import date, timedelta
import calendar

from django.core.exceptions import ValidationError
from django.db import models
from members.models import Member


class Event(models.Model):
    """Church events and programs."""

    EVENT_TYPE_CHOICES = [
        ("service", "Regular Service"),
        ("special", "Special Program"),
        ("conference", "Conference"),
        ("meeting", "Meeting"),
        ("wedding", "Wedding"),
        ("funeral", "Funeral Service"),
        ("baptism", "Baptism"),
        ("dedication", "Child Dedication"),
        ("fellowship", "Fellowship"),
        ("other", "Other"),
    ]
    WEEKDAY_CHOICES = [
        (0, "Monday"),
        (1, "Tuesday"),
        (2, "Wednesday"),
        (3, "Thursday"),
        (4, "Friday"),
        (5, "Saturday"),
        (6, "Sunday"),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    event_outline = models.TextField(blank=True)
    event_type = models.CharField(
        max_length=20, choices=EVENT_TYPE_CHOICES, default="service"
    )

    # Date and Time
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    start_time = models.TimeField()
    end_time = models.TimeField(null=True, blank=True)

    # Location
    location = models.CharField(max_length=200, default="Main Sanctuary")
    address = models.TextField(blank=True)
    is_online = models.BooleanField(default=False)
    online_link = models.URLField(blank=True)

    # Organization
    organizer = models.ForeignKey(
        Member,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="organized_events",
    )
    speakers = models.ManyToManyField(
        Member, blank=True, related_name="speaking_events"
    )
    expected_attendees = models.PositiveIntegerField(default=0)

    # Status
    is_public = models.BooleanField(default=True)
    requires_registration = models.BooleanField(default=False)
    registration_deadline = models.DateTimeField(null=True, blank=True)
    is_recurring = models.BooleanField(default=False)
    recurrence_pattern = models.CharField(
        max_length=50,
        choices=[
            ("daily", "Daily"),
            ("weekly", "Weekly"),
            ("biweekly", "Bi-weekly"),
            ("monthly", "Monthly"),
        ],
        blank=True,
    )
    recurrence_weekday = models.PositiveSmallIntegerField(
        choices=WEEKDAY_CHOICES,
        null=True,
        blank=True,
        help_text="Required for weekly/bi-weekly recurrence.",
    )
    recurrence_until = models.DateField(null=True, blank=True)

    # Media
    banner_image = models.ImageField(
        upload_to="events/banners/", blank=True, null=True
    )
    attachments = models.FileField(
        upload_to="events/attachments/", blank=True, null=True
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_date", "-start_time"]
        verbose_name = "Event"
        verbose_name_plural = "Events"

    def __str__(self):
        return f"{self.title} - {self.start_date}"

    @property
    def is_past(self):
        return self.start_date < date.today()

    @property
    def actual_attendees(self):
        return self.attendances.filter(is_present=True).count()

    def _next_occurrence_date(self, current_date):
        if self.recurrence_pattern == "daily":
            return current_date + timedelta(days=1)
        if self.recurrence_pattern == "weekly":
            return current_date + timedelta(days=7)
        if self.recurrence_pattern == "biweekly":
            return current_date + timedelta(days=14)
        if self.recurrence_pattern == "monthly":
            year = current_date.year + (1 if current_date.month == 12 else 0)
            month = 1 if current_date.month == 12 else current_date.month + 1
            day = min(current_date.day, calendar.monthrange(year, month)[1])
            return date(year, month, day)
        return None

    def _first_recurrence_cursor(self):
        if (
            self.recurrence_pattern in {"weekly", "biweekly"}
            and self.recurrence_weekday is not None
        ):
            offset = (self.recurrence_weekday - self.start_date.weekday()) % 7
            return self.start_date + timedelta(days=offset)
        return self.start_date

    def _fast_forward_cursor(self, cursor: date, start: date) -> date:
        """Jump recurrence cursor to start window to avoid long linear scans."""
        if cursor >= start:
            return cursor

        if self.recurrence_pattern == "daily":
            delta_days = (start - cursor).days
            return cursor + timedelta(days=delta_days)

        if self.recurrence_pattern == "weekly":
            delta_weeks = (start - cursor).days // 7
            candidate = cursor + timedelta(days=delta_weeks * 7)
            while candidate < start:
                candidate += timedelta(days=7)
            return candidate

        if self.recurrence_pattern == "biweekly":
            delta_steps = (start - cursor).days // 14
            candidate = cursor + timedelta(days=delta_steps * 14)
            while candidate < start:
                candidate += timedelta(days=14)
            return candidate

        if self.recurrence_pattern == "monthly":
            months_apart = (start.year - cursor.year) * 12 + (start.month - cursor.month)
            if months_apart <= 0:
                return cursor
            year, month = cursor.year, cursor.month
            for _ in range(months_apart):
                year += 1 if month == 12 else 0
                month = 1 if month == 12 else month + 1
            day = min(cursor.day, calendar.monthrange(year, month)[1])
            candidate = date(year, month, day)
            while candidate < start:
                candidate = self._next_occurrence_date(candidate)
            return candidate

        return cursor

    def clean(self):
        super().clean()
        if (
            self.is_recurring
            and self.recurrence_pattern in {"weekly", "biweekly"}
            and self.recurrence_weekday is None
        ):
            raise ValidationError(
                {
                    "recurrence_weekday": (
                        "Select a recurrence day for weekly or bi-weekly events."
                    )
                }
            )

    def generate_occurrences(
        self,
        range_start=None,
        range_end=None,
        replace_existing=False,
    ):
        if not self.is_recurring:
            return 0

        start = range_start or self.start_date
        max_end = self.recurrence_until or self.end_date or self.start_date
        end = range_end or max_end
        if end < start:
            return 0

        if replace_existing:
            self.occurrences.filter(
                occurrence_date__gte=start,
                occurrence_date__lte=end,
            ).delete()

        created = 0
        cursor = self._first_recurrence_cursor()
        cursor = self._fast_forward_cursor(cursor, start)
        while cursor and cursor <= end:
            if cursor >= start and (not self.recurrence_until or cursor <= self.recurrence_until):
                _, was_created = EventOccurrence.objects.get_or_create(
                    event=self,
                    occurrence_date=cursor,
                    defaults={
                        "start_time": self.start_time,
                        "end_time": self.end_time,
                    },
                )
                if was_created:
                    created += 1
            cursor = self._next_occurrence_date(cursor)
        return created


class EventAttendance(models.Model):
    """Attendance tracking for events."""

    event = models.ForeignKey(
        Event, on_delete=models.CASCADE, related_name="attendances"
    )
    member = models.ForeignKey(
        Member,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="event_attendances",
    )
    visitor_name = models.CharField(max_length=200, blank=True)
    visitor_email = models.EmailField(blank=True)
    visitor_phone = models.CharField(max_length=17, blank=True)
    is_present = models.BooleanField(default=True)
    check_in_time = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    registered_by = models.ForeignKey(
        Member,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="registered_attendances",
    )

    class Meta:
        unique_together = ["event", "member"]
        ordering = ["-check_in_time"]
        verbose_name = "Event Attendance"
        verbose_name_plural = "Event Attendances"

    def __str__(self):
        if self.member:
            return f"{self.member} - {self.event}"
        return f"{self.visitor_name} (Visitor) - {self.event}"


class EventRegistration(models.Model):
    """Event registration for members."""

    REGISTRATION_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("cancelled", "Cancelled"),
        ("attended", "Attended"),
    ]

    event = models.ForeignKey(
        Event, on_delete=models.CASCADE, related_name="registrations"
    )
    member = models.ForeignKey(
        Member,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="event_registrations",
    )
    guest_name = models.CharField(max_length=200, blank=True)
    guest_email = models.EmailField(blank=True)
    guest_phone = models.CharField(max_length=17, blank=True)
    number_of_guests = models.PositiveIntegerField(default=1)
    dietary_requirements = models.TextField(blank=True)
    special_requests = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=REGISTRATION_STATUS_CHOICES,
        default="pending",
    )
    registered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-registered_at"]
        verbose_name = "Event Registration"
        verbose_name_plural = "Event Registrations"

    def __str__(self):
        if self.member:
            return f"{self.member} - {self.event}"
        return f"{self.guest_name} - {self.event}"


class EventOccurrence(models.Model):
    """Concrete dates generated from a recurring event rule."""

    event = models.ForeignKey(
        Event, on_delete=models.CASCADE, related_name="occurrences"
    )
    occurrence_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField(null=True, blank=True)
    leader = models.ForeignKey(
        Member,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="event_occurrences_led",
    )
    is_cancelled = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["occurrence_date", "start_time"]
        unique_together = ["event", "occurrence_date"]
        verbose_name = "Event Occurrence"
        verbose_name_plural = "Event Occurrences"

    def __str__(self):
        return f"{self.event.title} - {self.occurrence_date}"

    @property
    def day_name(self):
        return self.occurrence_date.strftime("%A")

    @property
    def leaders_display(self):
        return self.leader.full_name if self.leader else ""

    def clean(self):
        super().clean()
        event = getattr(self, "event", None)
        if event is None or self.occurrence_date is None:
            return
        recurrence_until = event.recurrence_until
        if recurrence_until and self.occurrence_date > recurrence_until:
            raise ValidationError(
                {
                    "occurrence_date": (
                        f"Occurrence date cannot be after recurrence end date "
                        f"({recurrence_until})."
                    )
                }
            )
