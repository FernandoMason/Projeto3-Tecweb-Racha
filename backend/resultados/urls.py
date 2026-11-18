from django.urls import path

from .views import ResultadoView
from .views_cronica import CronicaView
from .views_narracao import NarracaoView, NarracoesDaPartidaView, PublicarNarracaoView
from .views_ranking import RankingView

urlpatterns = [
    path('partidas/<int:partida_id>/resultado/', ResultadoView.as_view(), name='resultado'),
    path('partidas/<int:partida_id>/resultado/cronica/', CronicaView.as_view(), name='cronica'),
    path('grupos/<int:grupo_id>/ranking/', RankingView.as_view(), name='ranking'),
    path('partidas/<int:partida_id>/narracoes/', NarracoesDaPartidaView.as_view(), name='narracoes'),
    path('narracoes/<int:narracao_id>/', NarracaoView.as_view(), name='narracao'),
    path('narracoes/<int:narracao_id>/publicar/', PublicarNarracaoView.as_view(), name='publicar-narracao'),
]
