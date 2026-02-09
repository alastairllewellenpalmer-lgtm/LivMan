"""
Health and care tracking models.
"""

from datetime import timedelta
from decimal import Decimal

from django.db import models


class VaccinationType(models.Model):
    """Types of vaccinations with their schedules."""

    name = models.CharField(max_length=100)
    interval_months = models.PositiveIntegerField(
        default=12,
        help_text="Months between vaccinations"
    )
    reminder_days_before = models.PositiveIntegerField(
        default=30,
        help_text="Days before due date to send reminder"
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} (every {self.interval_months} months)"


class Vaccination(models.Model):
    """Individual vaccination record for a horse."""

    horse = models.ForeignKey(
        'core.Horse',
        on_delete=models.CASCADE,
        related_name='vaccinations'
    )
    vaccination_type = models.ForeignKey(
        VaccinationType,
        on_delete=models.PROTECT,
        related_name='vaccinations'
    )
    date_given = models.DateField()
    next_due_date = models.DateField()
    vet_name = models.CharField(max_length=200, blank=True)
    batch_number = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    reminder_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date_given']

    def __str__(self):
        return f"{self.horse.name} - {self.vaccination_type.name} ({self.date_given})"

    def save(self, *args, **kwargs):
        # Auto-calculate next due date if not set
        if not self.next_due_date:
            months = self.vaccination_type.interval_months
            self.next_due_date = self.date_given + timedelta(days=months * 30)
        super().save(*args, **kwargs)

    @property
    def is_due_soon(self):
        """Check if vaccination is due within reminder period."""
        from django.utils import timezone
        days_until = (self.next_due_date - timezone.now().date()).days
        return 0 <= days_until <= self.vaccination_type.reminder_days_before

    @property
    def is_overdue(self):
        """Check if vaccination is overdue."""
        from django.utils import timezone
        return timezone.now().date() > self.next_due_date


class FarrierVisit(models.Model):
    """Farrier visit record."""

    class WorkType(models.TextChoices):
        TRIM = 'trim', 'Trim Only'
        FRONT_SHOES = 'front_shoes', 'Front Shoes'
        FULL_SET = 'full_set', 'Full Set'
        REMEDIAL = 'remedial', 'Remedial Work'
        REMOVE = 'remove', 'Shoe Removal'

    horse = models.ForeignKey(
        'core.Horse',
        on_delete=models.CASCADE,
        related_name='farrier_visits'
    )
    date = models.DateField()
    service_provider = models.ForeignKey(
        'billing.ServiceProvider',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='farrier_visits'
    )
    work_done = models.CharField(
        max_length=20,
        choices=WorkType.choices,
        default=WorkType.TRIM
    )
    next_due_date = models.DateField(null=True, blank=True)
    cost = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00')
    )
    notes = models.TextField(blank=True)
    extra_charge = models.OneToOneField(
        'billing.ExtraCharge',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='farrier_visit'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.horse.name} - {self.get_work_done_display()} ({self.date})"

    def save(self, *args, **kwargs):
        # Auto-calculate next due date (typically 6-8 weeks)
        if not self.next_due_date:
            self.next_due_date = self.date + timedelta(weeks=6)
        super().save(*args, **kwargs)

    @property
    def is_due_soon(self):
        """Check if farrier visit is due within 2 weeks."""
        from django.utils import timezone
        if not self.next_due_date:
            return False
        days_until = (self.next_due_date - timezone.now().date()).days
        return 0 <= days_until <= 14

    @property
    def is_overdue(self):
        """Check if farrier visit is overdue."""
        from django.utils import timezone
        if not self.next_due_date:
            return False
        return timezone.now().date() > self.next_due_date
