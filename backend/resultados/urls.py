from django.urls import path

from .views import ResultadoView
from .views_cronica import CronicaView

urlpatterns = [
    path('partidas/<int:partida_id>/resultado/', ResultadoView.as_view(), name='resultado'),
    path('partidas/<int:partida_id>/resultado/cronica/', CronicaView.as_view(), name='cronica'),
]
