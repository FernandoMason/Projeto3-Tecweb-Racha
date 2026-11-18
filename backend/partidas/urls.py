from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import PartidasDoGrupoView, PartidaViewSet

router = SimpleRouter()
router.register('partidas', PartidaViewSet, basename='partida')

urlpatterns = [
    path('grupos/<int:grupo_id>/partidas/', PartidasDoGrupoView.as_view(), name='partidas-do-grupo'),
    *router.urls,
]
