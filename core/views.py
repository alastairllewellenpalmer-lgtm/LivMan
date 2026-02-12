"""
Views for core app.
"""

from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import Count, Q, Sum
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from billing.models import ExtraCharge
from health.models import FarrierVisit, Vaccination

from .forms import HorseForm, LocationForm, MoveHorseForm, OwnerForm, PlacementForm
from .models import Horse, Invoice, Location, Owner, Placement, RateType


@login_required
def dashboard(request):
    """Main dashboard view."""
    today = timezone.now().date()
    thirty_days = today + timedelta(days=30)
    two_weeks = today + timedelta(days=14)

    # Horse counts
    total_horses = Horse.objects.filter(is_active=True).count()
    horses_by_location = Location.objects.annotate(
        horse_count=Count(
            'placements',
            filter=Q(placements__end_date__isnull=True)
        )
    ).filter(horse_count__gt=0).order_by('-horse_count')

    # Owner summary
    owners_with_horses = Owner.objects.annotate(
        horse_count=Count(
            'placements',
            filter=Q(placements__end_date__isnull=True)
        )
    ).filter(horse_count__gt=0).order_by('-horse_count')[:10]

    # Vaccinations due soon
    vaccinations_due = Vaccination.objects.filter(
        next_due_date__lte=thirty_days,
        next_due_date__gte=today,
        horse__is_active=True
    ).select_related('horse', 'vaccination_type').order_by('next_due_date')[:10]

    # Farrier due soon
    farrier_due = FarrierVisit.objects.filter(
        next_due_date__lte=two_weeks,
        next_due_date__gte=today,
        horse__is_active=True
    ).select_related('horse').order_by('next_due_date')[:10]

    # Outstanding invoices
    outstanding_invoices = Invoice.objects.filter(
        status__in=[Invoice.Status.SENT, Invoice.Status.OVERDUE]
    ).select_related('owner').order_by('due_date')[:10]

    # Unbilled charges
    unbilled_charges = ExtraCharge.objects.filter(
        invoiced=False
    ).select_related('horse', 'owner').order_by('-date')[:10]

    unbilled_total = ExtraCharge.objects.filter(invoiced=False).aggregate(
        total=Sum('amount')
    )['total'] or 0

    context = {
        'total_horses': total_horses,
        'horses_by_location': horses_by_location,
        'owners_with_horses': owners_with_horses,
        'vaccinations_due': vaccinations_due,
        'farrier_due': farrier_due,
        'outstanding_invoices': outstanding_invoices,
        'unbilled_charges': unbilled_charges,
        'unbilled_total': unbilled_total,
    }

    return render(request, 'dashboard.html', context)


# Horse Views
class HorseListView(LoginRequiredMixin, ListView):
    model = Horse
    template_name = 'horses/horse_list.html'
    context_object_name = 'horses'
    paginate_by = 50

    def get_queryset(self):
        queryset = Horse.objects.filter(is_active=True)

        # Search filter
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(notes__icontains=search)
            )

        # Location filter
        location = self.request.GET.get('location')
        if location:
            queryset = queryset.filter(
                placements__location_id=location,
                placements__end_date__isnull=True
            )

        # Owner filter
        owner = self.request.GET.get('owner')
        if owner:
            queryset = queryset.filter(
                placements__owner_id=owner,
                placements__end_date__isnull=True
            )

        # Prefetch current placements with owner/location to avoid N+1 queries
        queryset = queryset.prefetch_related(
            Prefetch(
                'placements',
                queryset=Placement.objects.filter(
                    end_date__isnull=True
                ).select_related('owner', 'location', 'rate_type'),
                to_attr='_prefetched_current_placements',
            )
        )

        return queryset.distinct().order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['locations'] = Location.objects.all()
        context['owners'] = Owner.objects.all()
        return context


class HorseDetailView(LoginRequiredMixin, DetailView):
    model = Horse
    template_name = 'horses/horse_detail.html'
    context_object_name = 'horse'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['placements'] = self.object.placements.all()[:10]
        context['vaccinations'] = self.object.vaccinations.all()[:5]
        context['farrier_visits'] = self.object.farrier_visits.all()[:5]
        context['extra_charges'] = self.object.extra_charges.all()[:10]
        return context


class HorseCreateView(LoginRequiredMixin, CreateView):
    model = Horse
    form_class = HorseForm
    template_name = 'horses/horse_form.html'
    success_url = reverse_lazy('horse_list')

    def form_valid(self, form):
        messages.success(self.request, f"Horse '{form.instance.name}' created successfully.")
        return super().form_valid(form)


class HorseUpdateView(LoginRequiredMixin, UpdateView):
    model = Horse
    form_class = HorseForm
    template_name = 'horses/horse_form.html'

    def get_success_url(self):
        return reverse_lazy('horse_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, f"Horse '{form.instance.name}' updated successfully.")
        return super().form_valid(form)


@login_required
def horse_move(request, pk):
    """Move a horse to a new location."""
    horse = get_object_or_404(Horse, pk=pk)
    current_placement = horse.current_placement

    if request.method == 'POST':
        form = MoveHorseForm(request.POST)
        if form.is_valid():
            move_date = form.cleaned_data['move_date']

            # End current placement
            if current_placement:
                current_placement.end_date = move_date - timedelta(days=1)
                current_placement.save()

            # Create new placement
            new_owner = form.cleaned_data['new_owner']
            new_rate_type = form.cleaned_data['new_rate_type']

            if not new_owner and current_placement:
                new_owner = current_placement.owner
            if not new_rate_type and current_placement:
                new_rate_type = current_placement.rate_type

            if not new_owner or not new_rate_type:
                messages.error(request, "Owner and rate type are required when the horse has no current placement.")
                return render(request, 'horses/horse_move.html', {
                    'horse': horse, 'form': form, 'current_placement': current_placement
                })

            new_placement = Placement(
                horse=horse,
                owner=new_owner,
                location=form.cleaned_data['new_location'],
                rate_type=new_rate_type,
                start_date=move_date,
                notes=form.cleaned_data['notes']
            )
            try:
                new_placement.full_clean()
            except ValidationError as e:
                messages.error(request, e.message)
                return render(request, 'horses/horse_move.html', {
                    'horse': horse, 'form': form, 'current_placement': current_placement
                })
            new_placement.save()

            messages.success(request, f"{horse.name} moved successfully.")
            return redirect('horse_detail', pk=horse.pk)
    else:
        form = MoveHorseForm(initial={
            'move_date': timezone.now().date()
        })

    return render(request, 'horses/horse_move.html', {
        'horse': horse,
        'form': form,
        'current_placement': current_placement
    })


# Owner Views
class OwnerListView(LoginRequiredMixin, ListView):
    model = Owner
    template_name = 'owners/owner_list.html'
    context_object_name = 'owners'

    def get_queryset(self):
        return Owner.objects.annotate(
            horse_count=Count(
                'placements',
                filter=Q(placements__end_date__isnull=True)
            )
        ).order_by('name')


class OwnerDetailView(LoginRequiredMixin, DetailView):
    model = Owner
    template_name = 'owners/owner_detail.html'
    context_object_name = 'owner'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['horses'] = self.object.active_horses
        context['invoices'] = self.object.invoices.all()[:10]
        context['extra_charges'] = self.object.extra_charges.filter(invoiced=False)
        return context


class OwnerCreateView(LoginRequiredMixin, CreateView):
    model = Owner
    form_class = OwnerForm
    template_name = 'owners/owner_form.html'
    success_url = reverse_lazy('owner_list')


class OwnerUpdateView(LoginRequiredMixin, UpdateView):
    model = Owner
    form_class = OwnerForm
    template_name = 'owners/owner_form.html'

    def get_success_url(self):
        return reverse_lazy('owner_detail', kwargs={'pk': self.object.pk})


# Location Views
class LocationListView(LoginRequiredMixin, ListView):
    model = Location
    template_name = 'locations/location_list.html'
    context_object_name = 'locations'

    def get_queryset(self):
        return Location.objects.annotate(
            horse_count=Count(
                'placements',
                filter=Q(placements__end_date__isnull=True)
            )
        ).order_by('site', 'name')


class LocationDetailView(LoginRequiredMixin, DetailView):
    model = Location
    template_name = 'locations/location_detail.html'
    context_object_name = 'location'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['horses'] = self.object.current_horses
        return context


class LocationCreateView(LoginRequiredMixin, CreateView):
    model = Location
    form_class = LocationForm
    template_name = 'locations/location_form.html'
    success_url = reverse_lazy('location_list')


class LocationUpdateView(LoginRequiredMixin, UpdateView):
    model = Location
    form_class = LocationForm
    template_name = 'locations/location_form.html'

    def get_success_url(self):
        return reverse_lazy('location_detail', kwargs={'pk': self.object.pk})


# Placement Views
class PlacementListView(LoginRequiredMixin, ListView):
    model = Placement
    template_name = 'placements/placement_list.html'
    context_object_name = 'placements'
    paginate_by = 50

    def get_queryset(self):
        queryset = Placement.objects.select_related(
            'horse', 'owner', 'location', 'rate_type'
        )

        # Status filter
        status = self.request.GET.get('status', 'active')
        if status == 'active':
            queryset = queryset.filter(end_date__isnull=True)
        elif status == 'ended':
            queryset = queryset.filter(end_date__isnull=False)
        # 'all' = no end_date filter

        # Location filter
        location = self.request.GET.get('location')
        if location:
            queryset = queryset.filter(location_id=location)

        # Owner filter
        owner = self.request.GET.get('owner')
        if owner:
            queryset = queryset.filter(owner_id=owner)

        return queryset.order_by('-start_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_status'] = self.request.GET.get('status', 'active')
        context['locations'] = Location.objects.all()
        context['owners'] = Owner.objects.all()
        return context


class PlacementCreateView(LoginRequiredMixin, CreateView):
    model = Placement
    form_class = PlacementForm
    template_name = 'placements/placement_form.html'
    success_url = reverse_lazy('placement_list')


class PlacementUpdateView(LoginRequiredMixin, UpdateView):
    model = Placement
    form_class = PlacementForm
    template_name = 'placements/placement_form.html'
    success_url = reverse_lazy('placement_list')
