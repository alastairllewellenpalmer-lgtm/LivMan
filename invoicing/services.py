"""
Invoice calculation and generation services.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from billing.models import ExtraCharge
from core.models import (
    BusinessSettings,
    Invoice,
    InvoiceLineItem,
    Owner,
    Placement,
)
from .utils import format_date_short, format_date_short_year, group_preview_charges_by_horse


class DuplicateInvoiceError(Exception):
    """Raised when an invoice would overlap with an existing one."""
    pass


class InvoiceService:
    """Service for generating and managing invoices."""

    @staticmethod
    def check_for_overlapping_invoices(owner, period_start, period_end):
        """Check if an invoice already exists for this owner overlapping the given period.

        Returns the overlapping invoice if found, None otherwise.
        """
        return Invoice.objects.filter(
            owner=owner,
            period_start__lte=period_end,
            period_end__gte=period_start,
        ).exclude(
            status=Invoice.Status.CANCELLED,
        ).first()

    @staticmethod
    def calculate_livery_charges(owner, period_start, period_end):
        """Calculate livery charges for an owner in a period."""
        charges = []

        # Get all placements for this owner that overlap with the period
        # A placement overlaps if it started before period ends AND hasn't ended before period starts
        placements = Placement.objects.filter(
            owner=owner,
            start_date__lte=period_end,
        ).exclude(
            end_date__lt=period_start
        ).select_related('horse', 'location', 'rate_type')

        for placement in placements:
            days = placement.get_days_in_period(period_start, period_end)
            if days > 0:
                amount = placement.calculate_charge(period_start, period_end)
                eff_start, eff_end = placement.get_effective_dates_in_period(
                    period_start, period_end
                )
                # Rich description: "Grass Livery incl hay £5 per day - 59 days (6 Nov to 3 Jan 2026)"
                rate_str = f"£{placement.daily_rate:g}"
                date_from = format_date_short(eff_start)
                date_to = format_date_short_year(eff_end)
                description = (
                    f"{placement.rate_type.name} {rate_str} per day "
                    f"- {days} days ({date_from} to {date_to})"
                )
                charges.append({
                    'horse': placement.horse,
                    'placement': placement,
                    'description': description,
                    'days': days,
                    'daily_rate': placement.daily_rate,
                    'amount': amount,
                    'line_type': 'livery',
                })

        return charges

    @staticmethod
    def get_unbilled_charges(owner, period_end):
        """Get extra charges that haven't been invoiced yet."""
        charges = ExtraCharge.objects.filter(
            owner=owner,
            invoiced=False,
            date__lte=period_end
        ).select_related('horse', 'service_provider')

        return [
            {
                'horse': charge.horse,
                'charge': charge,
                'description': f"{charge.get_charge_type_display()} - {charge.description}",
                'date': charge.date,
                'days': 1,
                'daily_rate': charge.amount,
                'amount': charge.amount,
                'line_type': charge.charge_type,
            }
            for charge in charges
        ]

    @classmethod
    def calculate_invoice_preview(cls, owner, period_start, period_end):
        """Calculate a preview of invoice charges without creating anything."""
        livery_charges = cls.calculate_livery_charges(owner, period_start, period_end)
        extra_charges = cls.get_unbilled_charges(owner, period_end)

        all_charges = livery_charges + extra_charges
        subtotal = sum(c['amount'] for c in all_charges)
        horse_groups = group_preview_charges_by_horse(all_charges)

        return {
            'livery_charges': livery_charges,
            'extra_charges': extra_charges,
            'all_charges': all_charges,
            'horse_groups': horse_groups,
            'subtotal': subtotal,
            'total': subtotal,  # No tax for now
        }

    @classmethod
    @transaction.atomic
    def create_invoice(cls, owner, period_start, period_end, notes=''):
        """Create an invoice for an owner."""
        existing = cls.check_for_overlapping_invoices(owner, period_start, period_end)
        if existing:
            raise DuplicateInvoiceError(
                f"{owner.name} already has invoice {existing.invoice_number} "
                f"covering {existing.period_start} to {existing.period_end} "
                f"which overlaps with this period."
            )

        settings = BusinessSettings.get_settings()

        # Create the invoice
        invoice = Invoice.objects.create(
            owner=owner,
            invoice_number=settings.get_next_invoice_number(),
            period_start=period_start,
            period_end=period_end,
            payment_terms_days=settings.default_payment_terms,
            due_date=period_end + timedelta(days=settings.default_payment_terms),
            notes=notes,
        )

        # Add livery line items
        livery_charges = cls.calculate_livery_charges(owner, period_start, period_end)
        for charge in livery_charges:
            InvoiceLineItem.objects.create(
                invoice=invoice,
                horse=charge['horse'],
                placement=charge['placement'],
                line_type=InvoiceLineItem.LineType.LIVERY,
                description=charge['description'],
                quantity=Decimal(str(charge['days'])),
                unit_price=charge['daily_rate'],
                line_total=charge['amount'],
            )

        # Add extra charge line items
        extra_charges = cls.get_unbilled_charges(owner, period_end)
        for charge in extra_charges:
            line_type_map = {
                'vet': InvoiceLineItem.LineType.VET,
                'farrier': InvoiceLineItem.LineType.FARRIER,
                'vaccination': InvoiceLineItem.LineType.VACCINATION,
                'feed': InvoiceLineItem.LineType.FEED,
                'medication': InvoiceLineItem.LineType.OTHER,
                'transport': InvoiceLineItem.LineType.OTHER,
                'equipment': InvoiceLineItem.LineType.OTHER,
                'dentist': InvoiceLineItem.LineType.OTHER,
                'physio': InvoiceLineItem.LineType.OTHER,
            }
            line_type = line_type_map.get(
                charge['line_type'],
                InvoiceLineItem.LineType.OTHER
            )

            InvoiceLineItem.objects.create(
                invoice=invoice,
                horse=charge['horse'],
                charge=charge['charge'],
                line_type=line_type,
                description=charge['description'],
                quantity=Decimal('1'),
                unit_price=charge['amount'],
                line_total=charge['amount'],
            )

            # Mark the charge as invoiced
            charge['charge'].mark_as_invoiced(invoice)

        # Recalculate totals
        invoice.recalculate_totals()

        return invoice

    @staticmethod
    def generate_monthly_invoices(year, month):
        """Generate invoices for all owners for a given month."""
        from calendar import monthrange

        # Calculate period
        first_day = date(year, month, 1)
        last_day = date(year, month, monthrange(year, month)[1])

        # Get all owners with placements overlapping this period
        owners_with_placements = Owner.objects.filter(
            placements__start_date__lte=last_day,
        ).exclude(
            placements__end_date__lt=first_day
        ).distinct()

        invoices = []
        skipped = []
        for owner in owners_with_placements:
            existing = InvoiceService.check_for_overlapping_invoices(
                owner, first_day, last_day
            )
            if existing:
                skipped.append(owner)
                continue

            invoice = InvoiceService.create_invoice(owner, first_day, last_day)
            if invoice.total > 0:
                invoices.append(invoice)
            else:
                # Delete zero-total invoices to avoid orphaned records
                invoice.delete()

        return invoices, skipped
