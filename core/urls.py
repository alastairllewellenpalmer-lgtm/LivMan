"""
URL configuration for core app.
"""

from django.urls import path

from . import views

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),

    # Horses
    path('horses/', views.HorseListView.as_view(), name='horse_list'),
    path('horses/add/', views.HorseCreateView.as_view(), name='horse_create'),
    path('horses/<int:pk>/', views.HorseDetailView.as_view(), name='horse_detail'),
    path('horses/<int:pk>/edit/', views.HorseUpdateView.as_view(), name='horse_update'),
    path('horses/<int:pk>/move/', views.horse_move, name='horse_move'),

    # Owners
    path('owners/', views.OwnerListView.as_view(), name='owner_list'),
    path('owners/add/', views.OwnerCreateView.as_view(), name='owner_create'),
    path('owners/<int:pk>/', views.OwnerDetailView.as_view(), name='owner_detail'),
    path('owners/<int:pk>/edit/', views.OwnerUpdateView.as_view(), name='owner_update'),

    # Locations
    path('locations/', views.LocationListView.as_view(), name='location_list'),
    path('locations/add/', views.LocationCreateView.as_view(), name='location_create'),
    path('locations/<int:pk>/', views.LocationDetailView.as_view(), name='location_detail'),
    path('locations/<int:pk>/edit/', views.LocationUpdateView.as_view(), name='location_update'),

    # Placements
    path('placements/', views.PlacementListView.as_view(), name='placement_list'),
    path('placements/add/', views.PlacementCreateView.as_view(), name='placement_create'),
    path('placements/<int:pk>/edit/', views.PlacementUpdateView.as_view(), name='placement_update'),

    # Horse Ownership
    path('ownership/', views.HorseOwnershipListView.as_view(), name='ownership_list'),
    path('ownership/add/', views.HorseOwnershipCreateView.as_view(), name='ownership_create'),
    path('ownership/<int:pk>/edit/', views.HorseOwnershipUpdateView.as_view(), name='ownership_update'),
    path('ownership/<int:pk>/end/', views.horse_ownership_end, name='ownership_end'),
]
