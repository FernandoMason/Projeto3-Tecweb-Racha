from django.contrib import admin

from .models import Gol, Resultado


class GolInline(admin.TabularInline):
    model = Gol
    extra = 0


@admin.register(Resultado)
class ResultadoAdmin(admin.ModelAdmin):
    list_display = ['partida', 'registrado_por', 'registrado_em']
    inlines = [GolInline]
