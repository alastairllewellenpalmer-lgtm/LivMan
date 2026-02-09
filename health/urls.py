"""
URL configuration for health app.
"""

from django.urls import path

from . import views

urlpatterns = [
    # Vaccinations
    path('vaccinations/', views.VaccinationListView.as_view(), name='vaccination_list'),
    path('vaccinations/add/', views.VaccinationCreateView.as_view(), name='vaccination_create'),
    path('vaccinations/<int:pk>/edit/', views.VaccinationUpdateView.as_view(), name='vaccination_update'),

    # Farrier
    path('farrier/', views.FarrierListView.as_view(), name='farrier_list'),
    path('farrier/add/', views.FarrierCreateView.as_view(), name='farrier_create'),
    path('farrier/<int:pk>/edit/', views.FarrierUpdateView.as_view(), name='farrier_update'),
]
