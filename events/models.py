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

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
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
        from datetime import date

        return self.start_date < date.today()

    @property
    def actual_attendees(self):
        return self.attendances.filter(is_present=True).count()


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
