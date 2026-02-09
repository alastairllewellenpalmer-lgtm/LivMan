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

from .forms import FarrierVisitForm, VaccinationForm
from .models import FarrierVisit, Vaccination, VaccinationType


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
