"""
Django admin configuration for health models.
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import FarrierVisit, Vaccination, VaccinationType


@admin.register(VaccinationType)
class VaccinationTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'interval_months', 'reminder_days_before', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name']


@admin.register(Vaccination)
class VaccinationAdmin(admin.ModelAdmin):
    list_display = [
        'horse', 'vaccination_type', 'date_given', 'next_due_date',
        'vet_name', 'status_display', 'reminder_sent'
    ]
    list_filter = ['vaccination_type', 'reminder_sent', 'date_given']
    search_fields = ['horse__name', 'vet_name', 'batch_number']
    date_hierarchy = 'date_given'
    raw_id_fields = ['horse']
    readonly_fields = ['created_at', 'updated_at']

    def status_display(self, obj):
        if obj.is_overdue:
            return format_html('<span style="color: red;">Overdue</span>')
        elif obj.is_due_soon:
            return format_html('<span style="color: orange;">Due Soon</span>')
        return format_html('<span style="color: green;">OK</span>')
    status_display.short_description = 'Status'


@admin.register(FarrierVisit)
class FarrierVisitAdmin(admin.ModelAdmin):
    list_display = [
        'horse', 'date', 'work_done', 'service_provider',
        'next_due_date', 'cost', 'status_display'
    ]
    list_filter = ['work_done', 'date', 'service_provider']
    search_fields = ['horse__name', 'notes']
    date_hierarchy = 'date'
    raw_id_fields = ['horse', 'extra_charge']
    readonly_fields = ['created_at', 'updated_at']

    def status_display(self, obj):
        if obj.is_overdue:
            return format_html('<span style="color: red;">Overdue</span>')
        elif obj.is_due_soon:
            return format_html('<span style="color: orange;">Due Soon</span>')
        return format_html('<span style="color: green;">OK</span>')
    status_display.short_description = 'Status'
