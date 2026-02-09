"""
Management command to import CSV data.
"""

from django.core.management.base import BaseCommand

from data.import_csv import run_import


class Command(BaseCommand):
    help = 'Import horse data from CSV files'

    def handle(self, *args, **options):
        self.stdout.write('Starting data import...')
        run_import()
        self.stdout.write(self.style.SUCCESS('Data import completed!'))
