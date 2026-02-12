"""
Core models for horse management system.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone


class Owner(models.Model):
    """Horse owner with contact information."""

    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    account_code = models.CharField(
        max_length=20,
        blank=True,
        help_text="Account code for accounting systems (e.g. Xero)"
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def active_horses(self):
        """Get horses currently placed with this owner."""
        return Horse.objects.filter(
            placements__owner=self,
            placements__end_date__isnull=True
        ).distinct()

    @property
    def active_horse_count(self):
        return self.active_horses.count()


class Location(models.Model):
    """Physical location where horses are kept."""

    name = models.CharField(max_length=200)
    site = models.CharField(
        max_length=100,
        help_text="Main site name (e.g., Colgate, Somerford, California Farm)"
    )
    description = models.TextField(blank=True)
    capacity = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['site', 'name']

    def __str__(self):
        return f"{self.name} ({self.site})"

    @property
    def current_horses(self):
        """Get horses currently at this location."""
        return Horse.objects.filter(
            placements__location=self,
            placements__end_date__isnull=True
        ).distinct()

    @property
    def current_horse_count(self):
        return self.current_horses.count()

    @property
    def availability(self):
        """Return available spaces if capacity is set."""
        if self.capacity:
            return self.capacity - self.current_horse_count
        return None


class Horse(models.Model):
    """Individual horse record."""

    class Sex(models.TextChoices):
        MARE = 'mare', 'Mare'
        GELDING = 'gelding', 'Gelding'
        STALLION = 'stallion', 'Stallion'
        COLT = 'colt', 'Colt'
        FILLY = 'filly', 'Filly'

    class Color(models.TextChoices):
        BAY = 'bay', 'Bay'
        CHESTNUT = 'chestnut', 'Chestnut'
        GREY = 'grey', 'Grey'
        BLACK = 'black', 'Black'
        BROWN = 'brown', 'Brown'
        PALOMINO = 'palomino', 'Palomino'
        SKEWBALD = 'skewbald', 'Skewbald'
        PIEBALD = 'piebald', 'Piebald'
        ROAN = 'roan', 'Roan'
        DUN = 'dun', 'Dun'
        CREAM = 'cream', 'Cream'
        OTHER = 'other', 'Other'

    name = models.CharField(max_length=200)
    date_of_birth = models.DateField(null=True, blank=True, help_text="Date of birth")
    age = models.PositiveIntegerField(null=True, blank=True, help_text="Age in years (used if DOB unknown)")
    color = models.CharField(max_length=20, choices=Color.choices, blank=True)
    sex = models.CharField(max_length=20, choices=Sex.choices, blank=True)
    breeding = models.TextField(blank=True, help_text="Sire/dam information (free text)")
    dam = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='offspring_as_dam', help_text="Dam (mother) if she is in the system"
    )
    sire_name = models.CharField(max_length=200, blank=True, help_text="Stallion name")
    photo = models.ImageField(upload_to='horses/', blank=True, null=True)
    notes = models.TextField(blank=True, help_text="Special notes (e.g., first winter, lame, needs rug)")
    passport_number = models.CharField(max_length=100, blank=True)
    has_passport = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True, help_text="False if horse has left permanently")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def calculated_age(self):
        """Return age from DOB if set, else fall back to age field."""
        if self.date_of_birth:
            today = date.today()
            return today.year - self.date_of_birth.year - (
                (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
            )
        return self.age

    @property
    def is_mare(self):
        return self.sex == self.Sex.MARE

    @property
    def foals(self):
        """Return offspring where this horse is the dam."""
        return Horse.objects.filter(dam=self)

    @property
    def current_placement(self):
        """Get the current active placement."""
        return self.placements.filter(end_date__isnull=True).first()

    @property
    def current_location(self):
        """Get the current location."""
        placement = self.current_placement
        return placement.location if placement else None

    @property
    def current_owner(self):
        """Get the current owner from placement (legacy single-owner)."""
        placement = self.current_placement
        return placement.owner if placement else None

    @property
    def current_owners(self):
        """Get all current fractional owners with their share percentages.

        Returns a list of (owner, share_percentage) tuples.
        Falls back to placement owner at 100% if no ownership records exist.
        """
        from core.models import HorseOwnership
        shares = HorseOwnership.get_ownership_shares(self)
        if shares:
            return shares
        # Fallback to placement owner
        if self.current_owner:
            return [(self.current_owner, Decimal('100.00'))]
        return []

    @property
    def has_fractional_ownership(self):
        """Check if this horse has multiple owners or explicit ownership records."""
        return self.ownerships.filter(
            effective_from__lte=date.today()
        ).filter(
            models.Q(effective_to__isnull=True) | models.Q(effective_to__gte=date.today())
        ).exists()


class RateType(models.Model):
    """Rate configuration for different livery types."""

    name = models.CharField(max_length=100)
    daily_rate = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['daily_rate']

    def __str__(self):
        return f"{self.name} (£{self.daily_rate}/day)"


class Placement(models.Model):
    """Tracks where a horse is located and who owns it."""

    horse = models.ForeignKey(
        Horse,
        on_delete=models.CASCADE,
        related_name='placements'
    )
    owner = models.ForeignKey(
        Owner,
        on_delete=models.PROTECT,
        related_name='placements'
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name='placements'
    )
    rate_type = models.ForeignKey(
        RateType,
        on_delete=models.PROTECT,
        related_name='placements'
    )
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date']

    def __str__(self):
        status = "current" if self.is_current else f"ended {self.end_date}"
        return f"{self.horse.name} at {self.location.name} ({status})"

    def clean(self):
        from django.core.exceptions import ValidationError
        super().clean()
        if not self.horse_id or not self.start_date:
            return

        # Find overlapping placements for the same horse
        overlapping = Placement.objects.filter(horse=self.horse)
        if self.pk:
            overlapping = overlapping.exclude(pk=self.pk)

        # A placement overlaps if it starts before this one ends
        # and ends after this one starts (or is still open)
        if self.end_date:
            # This placement has a defined range
            overlapping = overlapping.filter(
                start_date__lte=self.end_date
            ).exclude(
                end_date__isnull=False, end_date__lt=self.start_date
            )
        else:
            # This placement is open-ended — overlaps with anything
            # that hasn't ended before this one starts
            overlapping = overlapping.exclude(
                end_date__isnull=False, end_date__lt=self.start_date
            )

        if overlapping.exists():
            conflict = overlapping.first()
            end = conflict.end_date or "present"
            raise ValidationError(
                f"{self.horse.name} already has a placement from "
                f"{conflict.start_date} to {end} that overlaps with these dates."
            )

    @property
    def is_current(self):
        return self.end_date is None

    @property
    def daily_rate(self):
        return self.rate_type.daily_rate

    def get_effective_dates_in_period(self, period_start, period_end):
        """Return (effective_start, effective_end) tuple for a billing period."""
        effective_start = max(self.start_date, period_start)
        effective_end = min(self.end_date or period_end, period_end)
        return (effective_start, effective_end)

    def get_days_in_period(self, period_start, period_end):
        """Calculate billable days within a billing period."""
        effective_start, effective_end = self.get_effective_dates_in_period(period_start, period_end)

        if effective_start > effective_end:
            return 0

        return (effective_end - effective_start).days + 1

    def calculate_charge(self, period_start, period_end):
        """Calculate the charge for this placement in a billing period."""
        days = self.get_days_in_period(period_start, period_end)
        return days * self.daily_rate


class HorseOwnership(models.Model):
    """Tracks fractional ownership of a horse by multiple owners.

    This allows horses to be owned by multiple owners with different
    percentage shares. Invoice charges are split according to these
    ownership percentages.
    """

    horse = models.ForeignKey(
        Horse,
        on_delete=models.CASCADE,
        related_name='ownerships'
    )
    owner = models.ForeignKey(
        Owner,
        on_delete=models.PROTECT,
        related_name='horse_ownerships'
    )
    share_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal('0.01')),
            MaxValueValidator(Decimal('100.00'))
        ],
        help_text="Ownership percentage (0.01 to 100.00)"
    )
    effective_from = models.DateField()
    effective_to = models.DateField(
        null=True,
        blank=True,
        help_text="Leave blank if ownership is ongoing"
    )
    is_billing_contact = models.BooleanField(
        default=False,
        help_text="Primary contact for billing communications about this horse"
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-effective_from', 'owner__name']
        verbose_name = "Horse Ownership"
        verbose_name_plural = "Horse Ownerships"

    def __str__(self):
        return f"{self.horse.name} - {self.owner.name} ({self.share_percentage}%)"

    def clean(self):
        from django.core.exceptions import ValidationError
        super().clean()

        if self.effective_to and self.effective_from and self.effective_to < self.effective_from:
            raise ValidationError("Effective end date cannot be before start date.")

    @property
    def is_current(self):
        """Check if this ownership is currently active."""
        today = date.today()
        if self.effective_from > today:
            return False
        if self.effective_to and self.effective_to < today:
            return False
        return True

    @classmethod
    def get_ownership_shares(cls, horse, as_of_date=None):
        """Get all active ownership shares for a horse on a given date.

        Returns a list of (owner, share_percentage) tuples.
        If no ownership records exist, returns empty list.
        """
        if as_of_date is None:
            as_of_date = date.today()

        ownerships = cls.objects.filter(
            horse=horse,
            effective_from__lte=as_of_date,
        ).filter(
            models.Q(effective_to__isnull=True) | models.Q(effective_to__gte=as_of_date)
        ).select_related('owner')

        return [(o.owner, o.share_percentage) for o in ownerships]

    @classmethod
    def get_ownership_for_period(cls, horse, period_start, period_end):
        """Get ownership shares that overlap with a billing period.

        Returns a list of dicts with owner, percentage, and effective dates.
        """
        ownerships = cls.objects.filter(
            horse=horse,
            effective_from__lte=period_end,
        ).filter(
            models.Q(effective_to__isnull=True) | models.Q(effective_to__gte=period_start)
        ).select_related('owner')

        result = []
        for ownership in ownerships:
            eff_start = max(ownership.effective_from, period_start)
            eff_end = min(ownership.effective_to or period_end, period_end)
            result.append({
                'owner': ownership.owner,
                'percentage': ownership.share_percentage,
                'effective_start': eff_start,
                'effective_end': eff_end,
            })
        return result


class BusinessSettings(models.Model):
    """Singleton model for business configuration."""

    business_name = models.CharField(max_length=200, default="Horse Livery")
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    vat_registration = models.CharField(
        max_length=50,
        blank=True,
        default="N/A",
        help_text="VAT registration number, or N/A if not registered"
    )
    logo = models.ImageField(upload_to='business/', blank=True, null=True)
    bank_details = models.TextField(blank=True, help_text="Bank details for payment")
    card_payment_url = models.URLField(
        blank=True,
        help_text="URL for online card payment (e.g. SumUp link)"
    )
    default_payment_terms = models.PositiveIntegerField(
        default=30,
        help_text="Default payment terms in days"
    )
    invoice_prefix = models.CharField(max_length=10, default="INV")
    next_invoice_number = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Business Settings"
        verbose_name_plural = "Business Settings"

    def __str__(self):
        return self.business_name

    def save(self, *args, **kwargs):
        # Ensure only one instance exists
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_settings(cls):
        """Get or create the singleton settings instance."""
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

    def get_next_invoice_number(self):
        """Get and increment the next invoice number."""
        number = self.next_invoice_number
        self.next_invoice_number += 1
        self.save(update_fields=['next_invoice_number'])
        return f"{self.invoice_prefix}{number:05d}"


class Invoice(models.Model):
    """Invoice for an owner covering a billing period."""

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        SENT = 'sent', 'Sent'
        PAID = 'paid', 'Paid'
        OVERDUE = 'overdue', 'Overdue'
        CANCELLED = 'cancelled', 'Cancelled'

    owner = models.ForeignKey(
        Owner,
        on_delete=models.PROTECT,
        related_name='invoices'
    )
    invoice_number = models.CharField(max_length=50, unique=True)
    period_start = models.DateField()
    period_end = models.DateField()
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )
    payment_terms_days = models.PositiveIntegerField(default=30)
    due_date = models.DateField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.invoice_number} - {self.owner.name}"

    def save(self, *args, **kwargs):
        # Auto-calculate due date if not set
        if not self.due_date:
            self.due_date = self.period_end + timedelta(days=self.payment_terms_days)
        super().save(*args, **kwargs)

    def recalculate_totals(self):
        """Recalculate invoice totals from line items."""
        self.subtotal = sum(item.line_total for item in self.line_items.all())
        self.total = self.subtotal  # No tax for now
        self.save(update_fields=['subtotal', 'total'])

    def mark_as_sent(self):
        """Mark invoice as sent."""
        self.status = self.Status.SENT
        self.sent_at = timezone.now()
        self.save(update_fields=['status', 'sent_at'])

    def mark_as_paid(self):
        """Mark invoice as paid."""
        self.status = self.Status.PAID
        self.paid_at = timezone.now()
        self.save(update_fields=['status', 'paid_at'])

    @property
    def is_overdue(self):
        """Check if invoice is overdue."""
        if self.status in [self.Status.PAID, self.Status.CANCELLED]:
            return False
        return timezone.now().date() > self.due_date


class InvoiceLineItem(models.Model):
    """Individual line item on an invoice."""

    class LineType(models.TextChoices):
        LIVERY = 'livery', 'Livery'
        VET = 'vet', 'Veterinary'
        FARRIER = 'farrier', 'Farrier'
        VACCINATION = 'vaccination', 'Vaccination'
        FEED = 'feed', 'Feed'
        OTHER = 'other', 'Other'

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='line_items'
    )
    horse = models.ForeignKey(
        Horse,
        on_delete=models.PROTECT,
        related_name='invoice_items',
        null=True,
        blank=True
    )
    placement = models.ForeignKey(
        Placement,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invoice_items'
    )
    charge = models.ForeignKey(
        'billing.ExtraCharge',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invoice_items'
    )
    line_type = models.CharField(
        max_length=20,
        choices=LineType.choices,
        default=LineType.LIVERY
    )
    description = models.CharField(max_length=500)
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('1.00')
    )
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    line_total = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    class Meta:
        ordering = ['line_type', 'description']

    def __str__(self):
        return f"{self.description}: £{self.line_total}"

    def save(self, *args, **kwargs):
        # Auto-calculate line total unless explicitly provided
        if self.line_total is None:
            self.line_total = self.quantity * self.unit_price
        super().save(*args, **kwargs)
