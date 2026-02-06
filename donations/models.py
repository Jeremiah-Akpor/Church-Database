import calendar
from datetime import date
from decimal import Decimal

from django.db import models
from members.models import Member


def _month_bounds(year: int, month: int) -> tuple[date, date]:
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)


def _months_ago_start(today: date, months: int) -> date:
    month_index = (today.year * 12 + today.month - 1) - (months - 1)
    year, month_zero = divmod(month_index, 12)
    return date(year, month_zero + 1, 1)


class DonationQuerySet(models.QuerySet):
    def total_amount(self) -> Decimal:
        total = self.aggregate(total=models.Sum("amount"))["total"]
        return total or Decimal("0")

    def for_month(self, year: int, month: int):
        start_date, end_date = _month_bounds(year, month)
        return self.filter(donation_date__gte=start_date, donation_date__lte=end_date)

    def for_last_n_months(self, months: int, today: date | None = None):
        if months < 1:
            return self.none()
        current = today or date.today()
        start_date = _months_ago_start(current, months)
        return self.filter(donation_date__gte=start_date, donation_date__lte=current)

    def for_year(self, year: int):
        return self.filter(donation_date__year=year)

    def offertory(self):
        return self.filter(category__name__iexact="offertory")


class DonationManager(models.Manager.from_queryset(DonationQuerySet)):
    pass


class DonationCategory(models.Model):
    """Categories for donations (tithes, offerings, etc.)."""

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_tax_deductible = models.BooleanField(default=False)
    target_amount = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Donation Category"
        verbose_name_plural = "Donation Categories"

    def __str__(self):
        return self.name


class Donation(models.Model):
    """Individual donation records."""
    objects = DonationManager()

    PAYMENT_METHOD_CHOICES = [
        ("cash", "Cash"),
        ("check", "Check"),
        ("bank_transfer", "Bank Transfer"),
        ("credit_card", "Credit Card"),
        ("debit_card", "Debit Card"),
        ("mobile_money", "Mobile Money"),
        ("online", "Online Payment"),
        ("crypto", "Cryptocurrency"),
        ("other", "Other"),
    ]

    FREQUENCY_CHOICES = [
        ("one_time", "One Time"),
        ("weekly", "Weekly"),
        ("biweekly", "Bi-weekly"),
        ("monthly", "Monthly"),
        ("quarterly", "Quarterly"),
        ("yearly", "Yearly"),
    ]

    CURRENCY_CHOICES = [
        ("EUR", "EUR"),
        ("USD", "USD"),
        ("GBP", "GBP"),
    ]

    # Donor Information
    member = models.ForeignKey(
        Member,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="donations",
    )
    anonymous_donor_name = models.CharField(
        max_length=200, blank=True, help_text="For anonymous donations"
    )
    is_anonymous = models.BooleanField(default=False)

    # Donation Details
    category = models.ForeignKey(
        DonationCategory,
        on_delete=models.PROTECT,
        related_name="donations",
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default="EUR")
    payment_method = models.CharField(
        max_length=20, choices=PAYMENT_METHOD_CHOICES, default="cash"
    )
    frequency = models.CharField(
        max_length=20, choices=FREQUENCY_CHOICES, default="one_time"
    )

    # Date and Event
    donation_date = models.DateField()
    event = models.ForeignKey(
        "events.Event",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="donations",
    )

    # Payment Details
    transaction_reference = models.CharField(max_length=100, blank=True)
    check_number = models.CharField(max_length=50, blank=True)
    bank_name = models.CharField(max_length=100, blank=True)
    payment_notes = models.TextField(blank=True)

    # Acknowledgment
    receipt_number = models.CharField(max_length=50, unique=True, blank=True)
    receipt_sent = models.BooleanField(default=False)
    receipt_sent_date = models.DateTimeField(null=True, blank=True)
    thank_you_sent = models.BooleanField(default=False)

    # Tax Information
    is_tax_receipt_required = models.BooleanField(default=False)
    tax_year = models.PositiveIntegerField(null=True, blank=True)

    # Internal Notes
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(
        Member,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recorded_donations",
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-donation_date", "-created_at"]
        verbose_name = "Donation"
        verbose_name_plural = "Donations"

    def __str__(self):
        donor = self.member if self.member else self.anonymous_donor_name
        return f"{donor} - {self.category}: {self.amount} ({self.donation_date})"

    def save(self, *args, **kwargs):
        if not self.receipt_number:
            from datetime import datetime

            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            self.receipt_number = f"RCP-{timestamp}"
        if not self.tax_year and self.donation_date:
            self.tax_year = self.donation_date.year
        super().save(*args, **kwargs)

    @classmethod
    def offertory_total_last_month(cls) -> Decimal:
        return cls.objects.offertory().for_last_n_months(1).total_amount()

    @classmethod
    def offertory_total_last_3_months(cls) -> Decimal:
        return cls.objects.offertory().for_last_n_months(3).total_amount()

    @classmethod
    def offertory_total_last_6_months(cls) -> Decimal:
        return cls.objects.offertory().for_last_n_months(6).total_amount()

    @classmethod
    def offertory_total_last_9_months(cls) -> Decimal:
        return cls.objects.offertory().for_last_n_months(9).total_amount()

    @classmethod
    def offertory_total_year(cls, year: int | None = None) -> Decimal:
        selected_year = year or date.today().year
        return cls.objects.offertory().for_year(selected_year).total_amount()

    @classmethod
    def offertory_total_for_month(cls, year: int, month: int) -> Decimal:
        return cls.objects.offertory().for_month(year, month).total_amount()


class Pledge(models.Model):
    """Donation pledges/commitments."""

    PLEDGE_STATUS_CHOICES = [
        ("active", "Active"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
        ("overdue", "Overdue"),
    ]

    FREQUENCY_CHOICES = [
        ("weekly", "Weekly"),
        ("monthly", "Monthly"),
        ("quarterly", "Quarterly"),
        ("yearly", "Yearly"),
        ("one_time", "One Time"),
    ]

    member = models.ForeignKey(
        Member, on_delete=models.CASCADE, related_name="pledges"
    )
    category = models.ForeignKey(
        DonationCategory, on_delete=models.PROTECT, related_name="pledges"
    )

    # Pledge Details
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="NGN")
    frequency = models.CharField(
        max_length=20, choices=FREQUENCY_CHOICES, default="monthly"
    )
    pledge_date = models.DateField()
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)

    # Status
    status = models.CharField(
        max_length=20, choices=PLEDGE_STATUS_CHOICES, default="active"
    )
    total_paid = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    last_payment_date = models.DateField(null=True, blank=True)

    # Notes
    purpose = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-pledge_date"]
        verbose_name = "Pledge"
        verbose_name_plural = "Pledges"

    def __str__(self):
        return f"{self.member} - {self.amount} {self.frequency}"

    @property
    def balance(self):
        return self.amount - self.total_paid

    @property
    def percentage_paid(self):
        if self.amount > 0:
            return (self.total_paid / self.amount) * 100
        return 0


class PledgePayment(models.Model):
    """Payments made towards a pledge."""

    pledge = models.ForeignKey(
        Pledge, on_delete=models.CASCADE, related_name="payments"
    )
    donation = models.OneToOneField(
        Donation,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="pledge_payment",
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-payment_date"]
        verbose_name = "Pledge Payment"
        verbose_name_plural = "Pledge Payments"

    def __str__(self):
        return f"{self.pledge.member} - {self.amount} ({self.payment_date})"
