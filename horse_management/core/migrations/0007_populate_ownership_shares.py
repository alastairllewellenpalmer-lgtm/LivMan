"""
Data migration: seed OwnershipShare records from existing active placements.

For each active placement (end_date IS NULL), creates a 100% OwnershipShare
for the placement's owner, ensuring zero disruption to existing billing.
"""

from decimal import Decimal

from django.db import migrations


def populate_ownership_shares(apps, schema_editor):
    Placement = apps.get_model('core', 'Placement')
    OwnershipShare = apps.get_model('core', 'OwnershipShare')

    active_placements = Placement.objects.filter(end_date__isnull=True)
    for placement in active_placements:
        if not OwnershipShare.objects.filter(
            horse=placement.horse, owner=placement.owner
        ).exists():
            OwnershipShare.objects.create(
                horse=placement.horse,
                owner=placement.owner,
                share_percentage=Decimal('100.00'),
                is_primary_contact=True,
            )


def reverse_populate(apps, schema_editor):
    OwnershipShare = apps.get_model('core', 'OwnershipShare')
    OwnershipShare.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_add_ownership_share'),
    ]

    operations = [
        migrations.RunPython(populate_ownership_shares, reverse_populate),
    ]
