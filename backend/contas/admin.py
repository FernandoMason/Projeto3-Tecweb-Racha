from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    ordering = ['email']
    list_display = ['email', 'nome', 'posicao', 'is_staff']
    search_fields = ['email', 'nome']
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Perfil', {'fields': ('nome', 'posicao')}),
        ('Permissoes', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {'classes': ('wide',), 'fields': ('email', 'nome', 'posicao', 'password1', 'password2')}),
    )
