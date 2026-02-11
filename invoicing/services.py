"""
Invoice calculation and generation services.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from billing.models import ExtraCharge
from core.models import (
    BusinessSettings,
    HorseOwnership,
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
        """Calculate livery charges for an owner in a period based on ownership percentages."""
        charges = []

        # Get all ownerships for this owner that overlap with the period
        ownerships = HorseOwnership.objects.filter(
            owner=owner,
            start_date__lte=period_end,
        ).exclude(
            end_date__isnull=False,
            end_date__lt=period_start
        ).select_related('horse')

        for ownership in ownerships:
            horse = ownership.horse

            # Get the placements for this horse that overlap with the period
            placements = Placement.objects.filter(
                horse=horse,
                start_date__lte=period_end,
            ).exclude(
                end_date__isnull=False,
                end_date__lt=period_start
            ).select_related('location', 'rate_type')

            for placement in placements:
                # Calculate the intersection of ownership period, placement period, and billing period
                ownership_start, ownership_end = ownership.get_effective_dates_in_period(
                    period_start, period_end
                )
                placement_start, placement_end = placement.get_effective_dates_in_period(
                    period_start, period_end
                )

                # Find the intersection
                eff_start = max(ownership_start, placement_start)
                eff_end = min(ownership_end, placement_end)

                if eff_start > eff_end:
                    continue  # No overlap

                days = (eff_end - eff_start).days + 1
                if days <= 0:
                    continue

                # Calculate full amount and owner's share
                full_amount = days * placement.daily_rate
                owner_amount = (full_amount * ownership.percentage / Decimal('100')).quantize(
                    Decimal('0.01'), rounding=ROUND_HALF_UP
                )

                # Build description
                rate_str = f"£{placement.daily_rate:g}"
                date_from = format_date_short(eff_start)
                date_to = format_date_short_year(eff_end)

                # Include ownership percentage in description if not 100%
                if ownership.percentage != Decimal('100.00'):
                    description = (
                        f"{placement.rate_type.name} {rate_str} per day "
                        f"- {days} days ({date_from} to {date_to}) "
                        f"@ {ownership.percentage:.2f}% ownership"
                    )
                else:
                    description = (
                        f"{placement.rate_type.name} {rate_str} per day "
                        f"- {days} days ({date_from} to {date_to})"
                    )

                charges.append({
                    'horse': horse,
                    'placement': placement,
                    'ownership': ownership,
                    'description': description,
                    'days': days,
                    'daily_rate': placement.daily_rate,
                    'full_amount': full_amount,
                    'amount': owner_amount,
                    'percentage': ownership.percentage,
                    'line_type': 'livery',
                })

        return charges

    @staticmethod
    def get_unbilled_charges(owner, period_end):
        """Get extra charges that haven't been invoiced yet.

        Handles both direct charges (split_by_ownership=False) and
        split charges (split_by_ownership=True).
        """
        charges = []

        # Direct charges - go entirely to the specified owner
        direct_charges = ExtraCharge.objects.filter(
            owner=owner,
            invoiced=False,
            date__lte=period_end,
            split_by_ownership=False,
        ).select_related('horse', 'service_provider')

        for charge in direct_charges:
            charges.append({
                'horse': charge.horse,
                'charge': charge,
                'ownership': None,
                'description': f"{charge.get_charge_type_display()} - {charge.description}",
                'date': charge.date,
                'days': 1,
                'daily_rate': charge.amount,
                'full_amount': charge.amount,
                'amount': charge.amount,
                'percentage': Decimal('100.00'),
                'line_type': charge.charge_type,
            })

        # Split charges - need to find charges for horses this owner has ownership of
        # and calculate their share based on ownership percentage at the charge date
        split_charges = ExtraCharge.objects.filter(
            invoiced=False,
            date__lte=period_end,
            split_by_ownership=True,
        ).select_related('horse', 'service_provider')

        for charge in split_charges:
            # Get this owner's ownership percentage at the charge date
            ownership = HorseOwnership.objects.filter(
                horse=charge.horse,
                owner=owner,
                start_date__lte=charge.date,
            ).exclude(
                end_date__isnull=False,
                end_date__lt=charge.date
            ).first()

            if not ownership:
                continue  # Owner has no ownership of this horse at charge date

            owner_amount = (charge.amount * ownership.percentage / Decimal('100')).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )

            # Include ownership percentage in description if not 100%
            if ownership.percentage != Decimal('100.00'):
                description = (
                    f"{charge.get_charge_type_display()} - {charge.description} "
                    f"@ {ownership.percentage:.2f}% ownership"
                )
            else:
                description = f"{charge.get_charge_type_display()} - {charge.description}"

            charges.append({
                'horse': charge.horse,
                'charge': charge,
                'ownership': ownership,
                'description': description,
                'date': charge.date,
                'days': 1,
                'daily_rate': charge.amount,
                'full_amount': charge.amount,
                'amount': owner_amount,
                'percentage': ownership.percentage,
                'line_type': charge.charge_type,
            })

        return charges

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
                ownership=charge.get('ownership'),
                ownership_percentage=charge.get('percentage'),
                line_type=InvoiceLineItem.LineType.LIVERY,
                description=charge['description'],
                quantity=Decimal(str(charge['days'])),
                unit_price=charge['daily_rate'],
                line_total=charge['amount'],
            )

        # Add extra charge line items
        extra_charges = cls.get_unbilled_charges(owner, period_end)

        # Track which charges have been processed to handle split charges
        processed_charges = set()

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
                ownership=charge.get('ownership'),
                ownership_percentage=charge.get('percentage'),
                line_type=line_type,
                description=charge['description'],
                quantity=Decimal('1'),
                unit_price=charge['amount'],
                line_total=charge['amount'],
            )

            # Mark the charge as invoiced only if it's a direct charge
            # For split charges, we track them separately
            extra_charge = charge['charge']
            if not extra_charge.split_by_ownership:
                extra_charge.mark_as_invoiced(invoice)
            else:
                # For split charges, track that we've processed this owner's portion
                processed_charges.add(extra_charge.pk)

        # For split charges, check if all owners have been invoiced
        # and mark as invoiced if so
        for charge_pk in processed_charges:
            extra_charge = ExtraCharge.objects.get(pk=charge_pk)
            if cls._all_owners_invoiced(extra_charge, period_end):
                extra_charge.mark_as_invoiced(invoice)

        # Recalculate totals
        invoice.recalculate_totals()

        return invoice

    @staticmethod
    def _all_owners_invoiced(extra_charge, period_end):
        """Check if all owners of a horse have been invoiced for a split charge."""
        # Get all owners at the charge date
        ownerships = HorseOwnership.get_ownerships_at_date(extra_charge.horse, extra_charge.date)

        for ownership in ownerships:
            # Check if this owner has an invoice covering the charge date
            has_invoice = Invoice.objects.filter(
                owner=ownership.owner,
                period_end__gte=extra_charge.date,
                line_items__charge=extra_charge,
            ).exclude(
                status=Invoice.Status.CANCELLED,
            ).exists()

            if not has_invoice:
                return False

        return True

    @staticmethod
    def generate_monthly_invoices(year, month):
        """Generate invoices for all owners for a given month."""
        from calendar import monthrange

        # Calculate period
        first_day = date(year, month, 1)
        last_day = date(year, month, monthrange(year, month)[1])

        # Get all owners with ownership records overlapping this period
        owners_with_ownerships = Owner.objects.filter(
            horse_ownerships__start_date__lte=last_day,
        ).exclude(
            horse_ownerships__end_date__isnull=False,
            horse_ownerships__end_date__lt=first_day
        ).distinct()

        invoices = []
        skipped = []
        for owner in owners_with_ownerships:
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
