"""
Forms for health app.
"""

from django import forms

from .models import FarrierVisit, Vaccination, VaccinationType


class VaccinationForm(forms.ModelForm):
    class Meta:
        model = Vaccination
        fields = [
            'horse', 'vaccination_type', 'date_given', 'next_due_date',
            'vet_name', 'batch_number', 'notes'
        ]
        widgets = {
            'horse': forms.Select(attrs={'class': 'form-select'}),
            'vaccination_type': forms.Select(attrs={'class': 'form-select'}),
            'date_given': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'next_due_date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'vet_name': forms.TextInput(attrs={'class': 'form-input'}),
            'batch_number': forms.TextInput(attrs={'class': 'form-input'}),
            'notes': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2}),
        }


class FarrierVisitForm(forms.ModelForm):
    class Meta:
        model = FarrierVisit
        fields = [
            'horse', 'date', 'service_provider', 'work_done',
            'next_due_date', 'cost', 'notes'
        ]
        widgets = {
            'horse': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'service_provider': forms.Select(attrs={'class': 'form-select'}),
            'work_done': forms.Select(attrs={'class': 'form-select'}),
            'next_due_date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'cost': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}),
            'notes': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2}),
        }


class VaccinationTypeForm(forms.ModelForm):
    class Meta:
        model = VaccinationType
        fields = ['name', 'interval_months', 'reminder_days_before', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input'}),
            'interval_months': forms.NumberInput(attrs={'class': 'form-input'}),
            'reminder_days_before': forms.NumberInput(attrs={'class': 'form-input'}),
            'description': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }
