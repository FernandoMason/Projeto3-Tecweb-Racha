from django.contrib import admin

from .models import Partida, Presenca, Time


class PresencaInline(admin.TabularInline):
    model = Presenca
    extra = 0


class TimeInline(admin.TabularInline):
    model = Time
    extra = 0
    filter_horizontal = ['jogadores']


@admin.register(Partida)
class PartidaAdmin(admin.ModelAdmin):
    list_display = ['grupo', 'data_hora', 'local', 'status', 'origem_times']
    list_filter = ['status', 'origem_times']
    inlines = [PresencaInline, TimeInline]
