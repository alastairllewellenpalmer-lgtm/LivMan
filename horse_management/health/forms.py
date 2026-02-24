"""
Forms for health app.
"""

from datetime import timedelta

from django import forms

from .models import (
    BreedingRecord,
    FarrierVisit,
    MedicalCondition,
    Vaccination,
    VaccinationType,
    VetVisit,
    WormEggCount,
    WormingTreatment,
)


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


class WormingTreatmentForm(forms.ModelForm):
    class Meta:
        model = WormingTreatment
        fields = [
            'horse', 'date', 'product_name', 'active_ingredient',
            'dose', 'administered_by', 'notes'
        ]
        widgets = {
            'horse': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'product_name': forms.TextInput(attrs={'class': 'form-input'}),
            'active_ingredient': forms.TextInput(attrs={'class': 'form-input'}),
            'dose': forms.TextInput(attrs={'class': 'form-input'}),
            'administered_by': forms.TextInput(attrs={'class': 'form-input'}),
            'notes': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2}),
        }


class WormEggCountForm(forms.ModelForm):
    class Meta:
        model = WormEggCount
        fields = ['horse', 'date', 'count', 'lab_name', 'sample_type', 'notes']
        widgets = {
            'horse': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'count': forms.NumberInput(attrs={'class': 'form-input'}),
            'lab_name': forms.TextInput(attrs={'class': 'form-input'}),
            'sample_type': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2}),
        }


class MedicalConditionForm(forms.ModelForm):
    class Meta:
        model = MedicalCondition
        fields = ['horse', 'name', 'diagnosed_date', 'status', 'notes']
        widgets = {
            'horse': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-input'}),
            'diagnosed_date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2}),
        }


class VetVisitForm(forms.ModelForm):
    class Meta:
        model = VetVisit
        fields = [
            'horse', 'date', 'vet', 'reason', 'diagnosis',
            'treatment', 'follow_up_date', 'cost', 'notes'
        ]
        widgets = {
            'horse': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'vet': forms.Select(attrs={'class': 'form-select'}),
            'reason': forms.TextInput(attrs={'class': 'form-input'}),
            'diagnosis': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2}),
            'treatment': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2}),
            'follow_up_date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'cost': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}),
            'notes': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2}),
        }


class BreedingRecordForm(forms.ModelForm):
    class Meta:
        model = BreedingRecord
        fields = [
            'mare', 'stallion_name', 'date_covered',
            'date_scanned_14_days', 'date_scanned_heartbeat', 'date_foal_due',
            'foal', 'foal_dob', 'foal_sex', 'foal_colour', 'foal_microchip',
            'foaling_notes', 'status'
        ]
        widgets = {
            'mare': forms.Select(attrs={'class': 'form-select'}),
            'stallion_name': forms.TextInput(attrs={'class': 'form-input'}),
            'date_covered': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'date_scanned_14_days': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'date_scanned_heartbeat': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'date_foal_due': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'foal': forms.Select(attrs={'class': 'form-select'}),
            'foal_dob': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'foal_sex': forms.Select(attrs={'class': 'form-select'}),
            'foal_colour': forms.Select(attrs={'class': 'form-select'}),
            'foal_microchip': forms.TextInput(attrs={'class': 'form-input'}),
            'foaling_notes': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        date_covered = cleaned_data.get('date_covered')
        date_foal_due = cleaned_data.get('date_foal_due')
        # Auto-calculate foal due date if not provided
        if date_covered and not date_foal_due:
            cleaned_data['date_foal_due'] = date_covered + timedelta(days=340)
        return cleaned_data
