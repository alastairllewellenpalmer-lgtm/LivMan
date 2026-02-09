"""
Views for billing app.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from core.models import Horse, Owner

from .forms import ExtraChargeForm, ServiceProviderForm
from .models import ExtraCharge, ServiceProvider


class ExtraChargeListView(LoginRequiredMixin, ListView):
    model = ExtraCharge
    template_name = 'billing/charge_list.html'
    context_object_name = 'charges'
    paginate_by = 50

    def get_queryset(self):
        queryset = ExtraCharge.objects.select_related(
            'horse', 'owner', 'service_provider', 'invoice'
        )

        # Filter by invoiced status
        invoiced = self.request.GET.get('invoiced')
        if invoiced == 'yes':
            queryset = queryset.filter(invoiced=True)
        elif invoiced == 'no':
            queryset = queryset.filter(invoiced=False)

        # Filter by type
        charge_type = self.request.GET.get('type')
        if charge_type:
            queryset = queryset.filter(charge_type=charge_type)

        # Filter by horse
        horse = self.request.GET.get('horse')
        if horse:
            queryset = queryset.filter(horse_id=horse)

        # Filter by owner
        owner = self.request.GET.get('owner')
        if owner:
            queryset = queryset.filter(owner_id=owner)

        return queryset.order_by('-date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['horses'] = Horse.objects.filter(is_active=True)
        context['owners'] = Owner.objects.all()
        context['charge_types'] = ExtraCharge.ChargeType.choices
        return context


class ExtraChargeCreateView(LoginRequiredMixin, CreateView):
    model = ExtraCharge
    form_class = ExtraChargeForm
    template_name = 'billing/charge_form.html'
    success_url = reverse_lazy('charge_list')

    def get_initial(self):
        initial = super().get_initial()
        horse_id = self.request.GET.get('horse')
        if horse_id:
            initial['horse'] = horse_id
            try:
                horse = Horse.objects.get(pk=horse_id)
                if horse.current_owner:
                    initial['owner'] = horse.current_owner.pk
            except Horse.DoesNotExist:
                pass
        initial['date'] = timezone.now().date()
        return initial

    def form_valid(self, form):
        messages.success(self.request, "Charge added successfully.")
        return super().form_valid(form)


class ExtraChargeUpdateView(LoginRequiredMixin, UpdateView):
    model = ExtraCharge
    form_class = ExtraChargeForm
    template_name = 'billing/charge_form.html'
    success_url = reverse_lazy('charge_list')

    def form_valid(self, form):
        messages.success(self.request, "Charge updated successfully.")
        return super().form_valid(form)


class ExtraChargeDeleteView(LoginRequiredMixin, DeleteView):
    model = ExtraCharge
    template_name = 'billing/charge_confirm_delete.html'
    success_url = reverse_lazy('charge_list')

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Charge deleted successfully.")
        return super().delete(request, *args, **kwargs)


class ServiceProviderListView(LoginRequiredMixin, ListView):
    model = ServiceProvider
    template_name = 'billing/provider_list.html'
    context_object_name = 'providers'

    def get_queryset(self):
        queryset = ServiceProvider.objects.all()

        provider_type = self.request.GET.get('type')
        if provider_type:
            queryset = queryset.filter(provider_type=provider_type)

        return queryset.order_by('provider_type', 'name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['provider_types'] = ServiceProvider.ProviderType.choices
        return context


class ServiceProviderCreateView(LoginRequiredMixin, CreateView):
    model = ServiceProvider
    form_class = ServiceProviderForm
    template_name = 'billing/provider_form.html'
    success_url = reverse_lazy('provider_list')


class ServiceProviderUpdateView(LoginRequiredMixin, UpdateView):
    model = ServiceProvider
    form_class = ServiceProviderForm
    template_name = 'billing/provider_form.html'
    success_url = reverse_lazy('provider_list')
