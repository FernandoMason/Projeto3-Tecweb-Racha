from django.contrib import admin

from .models import Cronica, Gol, Narracao, Resultado


class GolInline(admin.TabularInline):
    model = Gol
    extra = 0


@admin.register(Resultado)
class ResultadoAdmin(admin.ModelAdmin):
    list_display = ['partida', 'registrado_por', 'registrado_em']
    inlines = [GolInline]


@admin.register(Cronica)
class CronicaAdmin(admin.ModelAdmin):
    list_display = ['resultado', 'status', 'titulo', 'craque', 'origem_craque', 'gerada_em']
    list_filter = ['status', 'origem_craque']


@admin.register(Narracao)
class NarracaoAdmin(admin.ModelAdmin):
    list_display = ['grito', 'partida', 'autor', 'protagonista', 'publicada', 'criada_em']
    list_filter = ['publicada']
