"""
Forms for billing app.
"""

from django import forms

from .models import ExtraCharge, ServiceProvider


class ExtraChargeForm(forms.ModelForm):
    class Meta:
        model = ExtraCharge
        fields = [
            'horse', 'owner', 'service_provider', 'charge_type',
            'date', 'description', 'amount', 'receipt_image', 'notes',
            'split_by_ownership'
        ]
        widgets = {
            'horse': forms.Select(attrs={'class': 'form-select'}),
            'owner': forms.Select(attrs={'class': 'form-select'}),
            'service_provider': forms.Select(attrs={'class': 'form-select'}),
            'charge_type': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'description': forms.TextInput(attrs={'class': 'form-input'}),
            'amount': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}),
            'receipt_image': forms.FileInput(attrs={'class': 'form-input'}),
            'notes': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2}),
            'split_by_ownership': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }


class ServiceProviderForm(forms.ModelForm):
    class Meta:
        model = ServiceProvider
        fields = ['name', 'provider_type', 'phone', 'email', 'address', 'notes', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input'}),
            'provider_type': forms.Select(attrs={'class': 'form-select'}),
            'phone': forms.TextInput(attrs={'class': 'form-input'}),
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
            'address': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2}),
            'notes': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }
