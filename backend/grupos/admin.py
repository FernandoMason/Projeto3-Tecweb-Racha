from django.contrib import admin

from .models import Grupo, Membro


class MembroInline(admin.TabularInline):
    model = Membro
    extra = 0


@admin.register(Grupo)
class GrupoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'codigo_convite', 'criado_por', 'criado_em']
    search_fields = ['nome', 'codigo_convite']
    inlines = [MembroInline]


@admin.register(Membro)
class MembroAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'grupo', 'papel', 'posicao', 'nota']
    list_filter = ['papel', 'posicao']
