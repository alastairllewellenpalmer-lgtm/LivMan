# Generated manually for fractional horse ownership

import django.core.validators
import django.db.models.deletion
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_horse_dam_horse_date_of_birth_horse_photo_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='HorseOwnership',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('share_percentage', models.DecimalField(
                    decimal_places=2,
                    help_text='Ownership percentage (0.01 to 100.00)',
                    max_digits=5,
                    validators=[
                        django.core.validators.MinValueValidator(Decimal('0.01')),
                        django.core.validators.MaxValueValidator(Decimal('100.00')),
                    ],
                )),
                ('effective_from', models.DateField()),
                ('effective_to', models.DateField(blank=True, help_text='Leave blank if ownership is ongoing', null=True)),
                ('is_billing_contact', models.BooleanField(default=False, help_text='Primary contact for billing communications about this horse')),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('horse', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ownerships', to='core.horse')),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='horse_ownerships', to='core.owner')),
            ],
            options={
                'verbose_name': 'Horse Ownership',
                'verbose_name_plural': 'Horse Ownerships',
                'ordering': ['-effective_from', 'owner__name'],
            },
        ),
    ]
