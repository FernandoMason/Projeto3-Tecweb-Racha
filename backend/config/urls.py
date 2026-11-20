from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def saude(request):
    """GET /api/saude/ -> {"ok": true}. Health check do Render (sem login e sem banco)."""
    return JsonResponse({'ok': True})


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/saude/', saude, name='saude'),
    path('api/auth/', include('contas.urls')),
    path('api/', include('grupos.urls')),
    path('api/', include('partidas.urls')),
    path('api/', include('resultados.urls')),
]
