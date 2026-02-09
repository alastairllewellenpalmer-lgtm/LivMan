"""
Django admin configuration for core models.
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import (
    BusinessSettings,
    Horse,
    Invoice,
    InvoiceLineItem,
    Location,
    Owner,
    Placement,
    RateType,
)


@admin.register(Owner)
class OwnerAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'phone', 'active_horse_count', 'created_at']
    search_fields = ['name', 'email', 'phone']
    list_filter = ['created_at']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ['name', 'site', 'capacity', 'current_horse_count', 'availability']
    list_filter = ['site']
    search_fields = ['name', 'site']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Horse)
class HorseAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'age', 'sex', 'color', 'current_owner_display',
        'current_location_display', 'is_active'
    ]
    list_filter = ['sex', 'color', 'is_active', 'has_passport']
    search_fields = ['name', 'passport_number', 'notes']
    readonly_fields = ['created_at', 'updated_at']

    def current_owner_display(self, obj):
        owner = obj.current_owner
        return owner.name if owner else '-'
    current_owner_display.short_description = 'Owner'

    def current_location_display(self, obj):
        location = obj.current_location
        return location.name if location else '-'
    current_location_display.short_description = 'Location'


@admin.register(RateType)
class RateTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'daily_rate', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name']


class PlacementInline(admin.TabularInline):
    model = Placement
    extra = 0
    readonly_fields = ['created_at']


@admin.register(Placement)
class PlacementAdmin(admin.ModelAdmin):
    list_display = [
        'horse', 'owner', 'location', 'rate_type',
        'start_date', 'end_date', 'is_current'
    ]
    list_filter = ['location', 'owner', 'rate_type', 'start_date']
    search_fields = ['horse__name', 'owner__name', 'location__name']
    date_hierarchy = 'start_date'
    raw_id_fields = ['horse', 'owner']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(BusinessSettings)
class BusinessSettingsAdmin(admin.ModelAdmin):
    list_display = ['business_name', 'email', 'phone', 'default_payment_terms']

    def has_add_permission(self, request):
        # Only allow one instance
        return not BusinessSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


class InvoiceLineItemInline(admin.TabularInline):
    model = InvoiceLineItem
    extra = 0
    readonly_fields = ['line_total']


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = [
        'invoice_number', 'owner', 'period_start', 'period_end',
        'total', 'status', 'due_date', 'is_overdue_display'
    ]
    list_filter = ['status', 'created_at', 'due_date']
    search_fields = ['invoice_number', 'owner__name']
    date_hierarchy = 'created_at'
    raw_id_fields = ['owner']
    readonly_fields = ['created_at', 'sent_at', 'paid_at']
    inlines = [InvoiceLineItemInline]

    def is_overdue_display(self, obj):
        if obj.is_overdue:
            return format_html('<span style="color: red;">Overdue</span>')
        return '-'
    is_overdue_display.short_description = 'Overdue'


@admin.register(InvoiceLineItem)
class InvoiceLineItemAdmin(admin.ModelAdmin):
    list_display = [
        'invoice', 'horse', 'line_type', 'description',
        'quantity', 'unit_price', 'line_total'
    ]
    list_filter = ['line_type']
    search_fields = ['description', 'horse__name', 'invoice__invoice_number']
    raw_id_fields = ['invoice', 'horse', 'placement', 'charge']
