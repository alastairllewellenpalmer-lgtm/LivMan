"""
URL configuration for billing app.
"""

from django.urls import path

from . import views

urlpatterns = [
    # Extra charges
    path('charges/', views.ExtraChargeListView.as_view(), name='charge_list'),
    path('charges/add/', views.ExtraChargeCreateView.as_view(), name='charge_create'),
    path('charges/<int:pk>/edit/', views.ExtraChargeUpdateView.as_view(), name='charge_update'),
    path('charges/<int:pk>/delete/', views.ExtraChargeDeleteView.as_view(), name='charge_delete'),

    # Service providers
    path('providers/', views.ServiceProviderListView.as_view(), name='provider_list'),
    path('providers/add/', views.ServiceProviderCreateView.as_view(), name='provider_create'),
    path('providers/<int:pk>/edit/', views.ServiceProviderUpdateView.as_view(), name='provider_update'),
]
