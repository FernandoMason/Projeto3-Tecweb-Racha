from django.urls import path

from .views import ResultadoView
from .views_cronica import CronicaView
from .views_ranking import RankingView

urlpatterns = [
    path('partidas/<int:partida_id>/resultado/', ResultadoView.as_view(), name='resultado'),
    path('partidas/<int:partida_id>/resultado/cronica/', CronicaView.as_view(), name='cronica'),
    path('grupos/<int:grupo_id>/ranking/', RankingView.as_view(), name='ranking'),
]
