"""
Views for health app.
"""

from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from billing.models import ExtraCharge
from core.models import Horse

from .forms import (
    BreedingRecordForm,
    FarrierVisitForm,
    MedicalConditionForm,
    VaccinationForm,
    VaccinationTypeForm,
    VetVisitForm,
    WormEggCountForm,
    WormingTreatmentForm,
)
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


# ─── Vaccination Views ───────────────────────────────────────────────

class VaccinationListView(LoginRequiredMixin, ListView):
    model = Vaccination
    template_name = 'health/vaccination_list.html'
    context_object_name = 'vaccinations'
    paginate_by = 50

    def get_queryset(self):
        queryset = Vaccination.objects.select_related(
            'horse', 'vaccination_type'
        ).filter(horse__is_active=True)

        # Filter by status
        status = self.request.GET.get('status')
        today = timezone.now().date()

        if status == 'due':
            thirty_days = today + timedelta(days=30)
            queryset = queryset.filter(
                next_due_date__lte=thirty_days,
                next_due_date__gte=today
            )
        elif status == 'overdue':
            queryset = queryset.filter(next_due_date__lt=today)

        # Filter by horse
        horse = self.request.GET.get('horse')
        if horse:
            queryset = queryset.filter(horse_id=horse)

        return queryset.order_by('next_due_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['horses'] = Horse.objects.filter(is_active=True)
        context['today'] = timezone.now().date()
        return context


class VaccinationCreateView(LoginRequiredMixin, CreateView):
    model = Vaccination
    form_class = VaccinationForm
    template_name = 'health/vaccination_form.html'
    success_url = reverse_lazy('vaccination_list')

    def get_initial(self):
        initial = super().get_initial()
        horse_id = self.request.GET.get('horse')
        if horse_id:
            initial['horse'] = horse_id
        initial['date_given'] = timezone.now().date()
        return initial

    def form_valid(self, form):
        messages.success(self.request, "Vaccination record added successfully.")
        return super().form_valid(form)


class VaccinationUpdateView(LoginRequiredMixin, UpdateView):
    model = Vaccination
    form_class = VaccinationForm
    template_name = 'health/vaccination_form.html'
    success_url = reverse_lazy('vaccination_list')


# ─── Vaccination Type Views ──────────────────────────────────────────

class VaccinationTypeListView(LoginRequiredMixin, ListView):
    model = VaccinationType
    template_name = 'health/vaccination_type_list.html'
    context_object_name = 'vaccination_types'
    paginate_by = 50

    def get_queryset(self):
        queryset = VaccinationType.objects.all()
        status = self.request.GET.get('status')
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
        return queryset.order_by('name')


class VaccinationTypeCreateView(LoginRequiredMixin, CreateView):
    model = VaccinationType
    form_class = VaccinationTypeForm
    template_name = 'health/vaccination_type_form.html'
    success_url = reverse_lazy('vaccination_type_list')

    def form_valid(self, form):
        messages.success(self.request, "Vaccination type added successfully.")
        return super().form_valid(form)


class VaccinationTypeUpdateView(LoginRequiredMixin, UpdateView):
    model = VaccinationType
    form_class = VaccinationTypeForm
    template_name = 'health/vaccination_type_form.html'
    success_url = reverse_lazy('vaccination_type_list')

    def form_valid(self, form):
        messages.success(self.request, "Vaccination type updated successfully.")
        return super().form_valid(form)


# ─── Farrier Views ───────────────────────────────────────────────────

class FarrierListView(LoginRequiredMixin, ListView):
    model = FarrierVisit
    template_name = 'health/farrier_list.html'
    context_object_name = 'visits'
    paginate_by = 50

    def get_queryset(self):
        queryset = FarrierVisit.objects.select_related(
            'horse', 'service_provider'
        ).filter(horse__is_active=True)

        # Filter by status
        status = self.request.GET.get('status')
        today = timezone.now().date()

        if status == 'due':
            two_weeks = today + timedelta(days=14)
            queryset = queryset.filter(
                next_due_date__lte=two_weeks,
                next_due_date__gte=today
            )
        elif status == 'overdue':
            queryset = queryset.filter(next_due_date__lt=today)

        # Filter by horse
        horse = self.request.GET.get('horse')
        if horse:
            queryset = queryset.filter(horse_id=horse)

        return queryset.order_by('-date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['horses'] = Horse.objects.filter(is_active=True)
        context['today'] = timezone.now().date()
        return context


class FarrierCreateView(LoginRequiredMixin, CreateView):
    model = FarrierVisit
    form_class = FarrierVisitForm
    template_name = 'health/farrier_form.html'
    success_url = reverse_lazy('farrier_list')

    def get_initial(self):
        initial = super().get_initial()
        horse_id = self.request.GET.get('horse')
        if horse_id:
            initial['horse'] = horse_id
        initial['date'] = timezone.now().date()
        return initial

    def form_valid(self, form):
        response = super().form_valid(form)

        # Optionally create an extra charge for the farrier visit
        if form.cleaned_data['cost'] > 0:
            horse = form.instance.horse
            owner = horse.current_owner

            if owner:
                charge = ExtraCharge.objects.create(
                    horse=horse,
                    owner=owner,
                    service_provider=form.instance.service_provider,
                    charge_type='farrier',
                    date=form.instance.date,
                    description=f"Farrier - {form.instance.get_work_done_display()}",
                    amount=form.instance.cost,
                )
                form.instance.extra_charge = charge
                form.instance.save()

        messages.success(self.request, "Farrier visit recorded successfully.")
        return response


class FarrierUpdateView(LoginRequiredMixin, UpdateView):
    model = FarrierVisit
    form_class = FarrierVisitForm
    template_name = 'health/farrier_form.html'
    success_url = reverse_lazy('farrier_list')

    def form_valid(self, form):
        response = super().form_valid(form)

        # Sync linked ExtraCharge if it exists and hasn't been invoiced
        if form.instance.extra_charge and not form.instance.extra_charge.invoiced:
            charge = form.instance.extra_charge
            charge.amount = form.instance.cost
            charge.date = form.instance.date
            charge.description = f"Farrier - {form.instance.get_work_done_display()}"
            charge.service_provider = form.instance.service_provider
            charge.save(update_fields=['amount', 'date', 'description', 'service_provider'])

        messages.success(self.request, "Farrier visit updated successfully.")
        return response


# ─── Worming Treatment Views ─────────────────────────────────────────

class WormingListView(LoginRequiredMixin, ListView):
    model = WormingTreatment
    template_name = 'health/worming_list.html'
    context_object_name = 'treatments'
    paginate_by = 50

    def get_queryset(self):
        queryset = WormingTreatment.objects.select_related('horse').filter(
            horse__is_active=True
        )
        horse = self.request.GET.get('horse')
        if horse:
            queryset = queryset.filter(horse_id=horse)
        return queryset.order_by('-date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['horses'] = Horse.objects.filter(is_active=True)
        return context


class WormingCreateView(LoginRequiredMixin, CreateView):
    model = WormingTreatment
    form_class = WormingTreatmentForm
    template_name = 'health/worming_form.html'
    success_url = reverse_lazy('worming_list')

    def get_initial(self):
        initial = super().get_initial()
        horse_id = self.request.GET.get('horse')
        if horse_id:
            initial['horse'] = horse_id
        initial['date'] = timezone.now().date()
        return initial

    def form_valid(self, form):
        messages.success(self.request, "Worming treatment recorded successfully.")
        return super().form_valid(form)


class WormingUpdateView(LoginRequiredMixin, UpdateView):
    model = WormingTreatment
    form_class = WormingTreatmentForm
    template_name = 'health/worming_form.html'
    success_url = reverse_lazy('worming_list')


# ─── Worm Egg Count Views ────────────────────────────────────────────

class WormEggCountListView(LoginRequiredMixin, ListView):
    model = WormEggCount
    template_name = 'health/egg_count_list.html'
    context_object_name = 'egg_counts'
    paginate_by = 50

    def get_queryset(self):
        queryset = WormEggCount.objects.select_related('horse').filter(
            horse__is_active=True
        )
        horse = self.request.GET.get('horse')
        if horse:
            queryset = queryset.filter(horse_id=horse)
        return queryset.order_by('-date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['horses'] = Horse.objects.filter(is_active=True)
        return context


class WormEggCountCreateView(LoginRequiredMixin, CreateView):
    model = WormEggCount
    form_class = WormEggCountForm
    template_name = 'health/egg_count_form.html'
    success_url = reverse_lazy('egg_count_list')

    def get_initial(self):
        initial = super().get_initial()
        horse_id = self.request.GET.get('horse')
        if horse_id:
            initial['horse'] = horse_id
        initial['date'] = timezone.now().date()
        return initial

    def form_valid(self, form):
        messages.success(self.request, "Egg count recorded successfully.")
        return super().form_valid(form)


class WormEggCountUpdateView(LoginRequiredMixin, UpdateView):
    model = WormEggCount
    form_class = WormEggCountForm
    template_name = 'health/egg_count_form.html'
    success_url = reverse_lazy('egg_count_list')


# ─── Medical Condition Views ─────────────────────────────────────────

class MedicalConditionListView(LoginRequiredMixin, ListView):
    model = MedicalCondition
    template_name = 'health/condition_list.html'
    context_object_name = 'conditions'
    paginate_by = 50

    def get_queryset(self):
        queryset = MedicalCondition.objects.select_related('horse').filter(
            horse__is_active=True
        )
        horse = self.request.GET.get('horse')
        if horse:
            queryset = queryset.filter(horse_id=horse)
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['horses'] = Horse.objects.filter(is_active=True)
        return context


class MedicalConditionCreateView(LoginRequiredMixin, CreateView):
    model = MedicalCondition
    form_class = MedicalConditionForm
    template_name = 'health/condition_form.html'
    success_url = reverse_lazy('condition_list')

    def get_initial(self):
        initial = super().get_initial()
        horse_id = self.request.GET.get('horse')
        if horse_id:
            initial['horse'] = horse_id
        return initial

    def form_valid(self, form):
        messages.success(self.request, "Medical condition recorded successfully.")
        return super().form_valid(form)


class MedicalConditionUpdateView(LoginRequiredMixin, UpdateView):
    model = MedicalCondition
    form_class = MedicalConditionForm
    template_name = 'health/condition_form.html'
    success_url = reverse_lazy('condition_list')


# ─── Vet Visit Views ─────────────────────────────────────────────────

class VetVisitListView(LoginRequiredMixin, ListView):
    model = VetVisit
    template_name = 'health/vet_visit_list.html'
    context_object_name = 'vet_visits'
    paginate_by = 50

    def get_queryset(self):
        queryset = VetVisit.objects.select_related('horse', 'vet').filter(
            horse__is_active=True
        )
        horse = self.request.GET.get('horse')
        if horse:
            queryset = queryset.filter(horse_id=horse)
        return queryset.order_by('-date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['horses'] = Horse.objects.filter(is_active=True)
        return context


class VetVisitCreateView(LoginRequiredMixin, CreateView):
    model = VetVisit
    form_class = VetVisitForm
    template_name = 'health/vet_visit_form.html'
    success_url = reverse_lazy('vet_visit_list')

    def get_initial(self):
        initial = super().get_initial()
        horse_id = self.request.GET.get('horse')
        if horse_id:
            initial['horse'] = horse_id
        initial['date'] = timezone.now().date()
        return initial

    def form_valid(self, form):
        response = super().form_valid(form)

        # Auto-create ExtraCharge if cost > 0 (same pattern as FarrierCreateView)
        if form.cleaned_data['cost'] > 0:
            horse = form.instance.horse
            owner = horse.current_owner

            if owner:
                charge = ExtraCharge.objects.create(
                    horse=horse,
                    owner=owner,
                    service_provider=form.instance.vet,
                    charge_type='vet',
                    date=form.instance.date,
                    description=f"Vet - {form.instance.reason[:200]}",
                    amount=form.instance.cost,
                )
                form.instance.extra_charge = charge
                form.instance.save()

        messages.success(self.request, "Vet visit recorded successfully.")
        return response


class VetVisitUpdateView(LoginRequiredMixin, UpdateView):
    model = VetVisit
    form_class = VetVisitForm
    template_name = 'health/vet_visit_form.html'
    success_url = reverse_lazy('vet_visit_list')

    def form_valid(self, form):
        response = super().form_valid(form)

        # Sync linked ExtraCharge if it exists and hasn't been invoiced
        if form.instance.extra_charge and not form.instance.extra_charge.invoiced:
            charge = form.instance.extra_charge
            charge.amount = form.instance.cost
            charge.date = form.instance.date
            charge.description = f"Vet - {form.instance.reason[:200]}"
            charge.service_provider = form.instance.vet
            charge.save(update_fields=['amount', 'date', 'description', 'service_provider'])

        messages.success(self.request, "Vet visit updated successfully.")
        return response


# ─── Breeding Record Views ───────────────────────────────────────────

class BreedingRecordListView(LoginRequiredMixin, ListView):
    model = BreedingRecord
    template_name = 'health/breeding_list.html'
    context_object_name = 'breeding_records'
    paginate_by = 50

    def get_queryset(self):
        queryset = BreedingRecord.objects.select_related('mare', 'foal').filter(
            mare__is_active=True
        )
        horse = self.request.GET.get('horse')
        if horse:
            queryset = queryset.filter(mare_id=horse)
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        return queryset.order_by('-date_covered')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['horses'] = Horse.objects.filter(is_active=True, sex='mare')
        return context


class BreedingRecordCreateView(LoginRequiredMixin, CreateView):
    model = BreedingRecord
    form_class = BreedingRecordForm
    template_name = 'health/breeding_form.html'
    success_url = reverse_lazy('breeding_list')

    def get_initial(self):
        initial = super().get_initial()
        horse_id = self.request.GET.get('horse')
        if horse_id:
            initial['mare'] = horse_id
        return initial

    def form_valid(self, form):
        messages.success(self.request, "Breeding record added successfully.")
        return super().form_valid(form)


class BreedingRecordUpdateView(LoginRequiredMixin, UpdateView):
    model = BreedingRecord
    form_class = BreedingRecordForm
    template_name = 'health/breeding_form.html'
    success_url = reverse_lazy('breeding_list')
