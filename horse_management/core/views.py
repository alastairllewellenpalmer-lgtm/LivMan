"""
Views for core app.
"""

from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import Count, Exists, OuterRef, Prefetch, Q, Sum
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
from health.models import (
    BreedingRecord,
    FarrierVisit,
    MedicalCondition,
    Vaccination,
    VetVisit,
    WormEggCount,
    WormingTreatment,
)

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

    # Mares with EHV vaccinations due soon
    ehv_due = BreedingRecord.objects.filter(
        status='confirmed',
        mare__is_active=True,
    ).select_related('mare')[:10]

    # Recent high worm egg counts (>200 EPG)
    high_egg_counts = WormEggCount.objects.filter(
        count__gt=200,
        horse__is_active=True,
    ).select_related('horse').order_by('-date')[:10]

    # Upcoming vet follow-ups
    vet_follow_ups = VetVisit.objects.filter(
        follow_up_date__gte=today,
        follow_up_date__lte=thirty_days,
        horse__is_active=True,
    ).select_related('horse', 'vet').order_by('follow_up_date')[:10]

    context = {
        'total_horses': total_horses,
        'horses_by_location': horses_by_location,
        'owners_with_horses': owners_with_horses,
        'vaccinations_due': vaccinations_due,
        'farrier_due': farrier_due,
        'outstanding_invoices': outstanding_invoices,
        'unbilled_charges': unbilled_charges,
        'unbilled_total': unbilled_total,
        'ehv_due': ehv_due,
        'high_egg_counts': high_egg_counts,
        'vet_follow_ups': vet_follow_ups,
    }

    return render(request, 'dashboard.html', context)


# Horse Views
class HorseListView(LoginRequiredMixin, ListView):
    model = Horse
    template_name = 'horses/horse_list.html'
    context_object_name = 'horses'
    paginate_by = 25

    def get_queryset(self):
        active_placements = Prefetch(
            'placements',
            queryset=Placement.objects.filter(
                end_date__isnull=True
            ).select_related('owner', 'location'),
            to_attr='active_placements',
        )
        queryset = Horse.objects.filter(is_active=True).only(
            'id', 'name', 'age', 'date_of_birth', 'color', 'sex', 'is_active'
        ).prefetch_related(active_placements)

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
                Exists(Placement.objects.filter(
                    horse=OuterRef('pk'),
                    location_id=location,
                    end_date__isnull=True,
                ))
            )

        # Owner filter
        owner = self.request.GET.get('owner')
        if owner:
            queryset = queryset.filter(
                Exists(Placement.objects.filter(
                    horse=OuterRef('pk'),
                    owner_id=owner,
                    end_date__isnull=True,
                ))
            )

        return queryset.order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['locations'] = Location.objects.values('pk', 'name')
        context['owners'] = Owner.objects.values('pk', 'name')
        return context


class HorseDetailView(LoginRequiredMixin, DetailView):
    model = Horse
    template_name = 'horses/horse_detail.html'
    context_object_name = 'horse'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        horse = self.object
        # Prefetch current placement once to avoid repeated DB hits in template
        context['current_placement'] = horse.placements.filter(
            end_date__isnull=True
        ).select_related('owner', 'location', 'rate_type').first()
        context['placements'] = horse.placements.select_related(
            'owner', 'location', 'rate_type'
        ).all()[:10]
        context['vaccinations'] = horse.vaccinations.select_related(
            'vaccination_type'
        ).all()[:5]
        context['farrier_visits'] = horse.farrier_visits.all()[:5]
        context['extra_charges'] = horse.extra_charges.select_related(
            'owner'
        ).all()[:10]
        # New sections
        context['worming_treatments'] = horse.worming_treatments.all()[:10]
        context['egg_counts'] = horse.worm_egg_counts.all()[:10]
        context['medical_conditions'] = horse.medical_conditions.all()
        context['vet_visits'] = horse.vet_visits.select_related('vet').all()[:10]
        # Breeding (mare only)
        if horse.is_mare:
            context['breeding_records'] = horse.breeding_records.select_related('foal').all()
            context['active_pregnancy'] = horse.breeding_records.filter(
                status__in=['covered', 'confirmed']
            ).first()
        # Foals via dam FK
        context['foals'] = Horse.objects.filter(dam=horse) if horse.is_mare else []
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
        # Optimized: prefetch active placements with location to avoid N+1
        active_placements = Prefetch(
            'placements',
            queryset=Placement.objects.filter(
                end_date__isnull=True
            ).select_related('location'),
            to_attr='active_placements',
        )
        context['horses'] = Horse.objects.filter(
            placements__owner=self.object,
            placements__end_date__isnull=True
        ).distinct().prefetch_related(active_placements)
        context['invoices'] = self.object.invoices.all()[:10]
        context['extra_charges'] = self.object.extra_charges.filter(
            invoiced=False
        ).select_related('horse')
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
        # Optimized: prefetch active placements with owner to avoid N+1
        active_placements = Prefetch(
            'placements',
            queryset=Placement.objects.filter(
                end_date__isnull=True
            ).select_related('owner'),
            to_attr='active_placements',
        )
        context['horses'] = Horse.objects.filter(
            placements__location=self.object,
            placements__end_date__isnull=True
        ).distinct().prefetch_related(active_placements)
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
