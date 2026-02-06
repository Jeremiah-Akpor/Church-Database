from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator


class Department(models.Model):
    """Church departments/groups."""

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    leader = models.ForeignKey(
        "Member",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="departments_led",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Department"
        verbose_name_plural = "Departments"

    def __str__(self):
        return self.name


class Member(models.Model):
    """Church member profile."""

    MEMBERSHIP_STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
        ("visitor", "Visitor"),
        ("new_convert", "New Convert"),
    ]

    GENDER_CHOICES = [
        ("male", "Male"),
        ("female", "Female"),
        ("other", "Other"),
    ]

    MARITAL_STATUS_CHOICES = [
        ("single", "Single"),
        ("married", "Married"),
        ("divorced", "Divorced"),
        ("widowed", "Widowed"),
    ]

    # Personal Information
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, null=True, blank=True
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    email = models.EmailField(unique=True, blank=True, null=True)
    phone_regex = RegexValidator(
        regex=r"^\+?1?\d{9,15}$",
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.",
    )
    phone_number = models.CharField(
        validators=[phone_regex], max_length=17, blank=True
    )
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(
        max_length=10, choices=GENDER_CHOICES, blank=True
    )
    marital_status = models.CharField(
        max_length=10, choices=MARITAL_STATUS_CHOICES, default="single"
    )
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True, default="Nigeria")
    occupation = models.CharField(max_length=100, blank=True)
    employer = models.CharField(max_length=100, blank=True)

    # Church Information
    membership_status = models.CharField(
        max_length=20,
        choices=MEMBERSHIP_STATUS_CHOICES,
        default="visitor",
    )
    membership_date = models.DateField(null=True, blank=True)
    baptism_date = models.DateField(null=True, blank=True)
    baptism_type = models.CharField(
        max_length=50,
        choices=[
            ("water", "Water Baptism"),
            ("holy_spirit", "Holy Spirit Baptism"),
            ("both", "Both"),
        ],
        blank=True,
    )
    departments = models.ManyToManyField(
        Department, blank=True, related_name="members"
    )
    is_leader = models.BooleanField(default=False)
    leadership_position = models.CharField(max_length=100, blank=True)

    # Emergency Contact
    emergency_contact_name = models.CharField(max_length=200, blank=True)
    emergency_contact_phone = models.CharField(
        validators=[phone_regex], max_length=17, blank=True
    )
    emergency_contact_relationship = models.CharField(max_length=50, blank=True)

    # Metadata
    photo = models.ImageField(upload_to="members/photos/", blank=True, null=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Member"
        verbose_name_plural = "Members"

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name(self):
        if self.middle_name:
            return f"{self.first_name} {self.middle_name} {self.last_name}"
        return f"{self.first_name} {self.last_name}"

    @property
    def age(self):
        if self.date_of_birth:
            from datetime import date

            today = date.today()
            return (
                today.year
                - self.date_of_birth.year
                - (
                    (today.month, today.day)
                    < (self.date_of_birth.month, self.date_of_birth.day)
                )
            )
        return None


class Family(models.Model):
    """Family unit within the church."""

    FAMILY_TYPE_CHOICES = [
        ("nuclear", "Nuclear Family"),
        ("extended", "Extended Family"),
        ("single_parent", "Single Parent"),
    ]

    family_name = models.CharField(max_length=200)
    family_head = models.ForeignKey(
        Member,
        on_delete=models.SET_NULL,
        null=True,
        related_name="headed_families",
    )
    family_type = models.CharField(
        max_length=20, choices=FAMILY_TYPE_CHOICES, default="nuclear"
    )
    address = models.TextField(blank=True)
    home_phone = models.CharField(max_length=17, blank=True)
    anniversary_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["family_name"]
        verbose_name = "Family"
        verbose_name_plural = "Families"

    def __str__(self):
        return self.family_name


class FamilyMember(models.Model):
    """Relationship between family and member."""

    RELATIONSHIP_CHOICES = [
        ("spouse", "Spouse"),
        ("child", "Child"),
        ("parent", "Parent"),
        ("sibling", "Sibling"),
        ("relative", "Relative"),
        ("other", "Other"),
    ]

    family = models.ForeignKey(
        Family, on_delete=models.CASCADE, related_name="members"
    )
    member = models.ForeignKey(
        Member, on_delete=models.CASCADE, related_name="family_memberships"
    )
    relationship = models.CharField(
        max_length=20, choices=RELATIONSHIP_CHOICES
    )
    is_primary_contact = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["family", "member"]
        ordering = ["family", "member"]
        verbose_name = "Family Member"
        verbose_name_plural = "Family Members"

    def __str__(self):
        return f"{self.member} - {self.relationship} of {self.family}"
