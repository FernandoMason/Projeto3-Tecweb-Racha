from django.urls import path

from .views import ResultadoView

urlpatterns = [
    path('partidas/<int:partida_id>/resultado/', ResultadoView.as_view(), name='resultado'),
]
