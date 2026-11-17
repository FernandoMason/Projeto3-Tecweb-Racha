import secrets

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from contas.models import Posicao

# Sem 0/O/1/I para o codigo ser facil de ditar no grupo do zap.
ALFABETO_CONVITE = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'


def gerar_codigo_convite():
    while True:
        codigo = 'RACHA-' + ''.join(secrets.choice(ALFABETO_CONVITE) for _ in range(3))
        if not Grupo.objects.filter(codigo_convite=codigo).exists():
            return codigo


class Grupo(models.Model):
    nome = models.CharField(max_length=80)
    codigo_convite = models.CharField(max_length=12, unique=True, editable=False)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='grupos_criados'
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-criado_em']

    def save(self, *args, **kwargs):
        if not self.codigo_convite:
            self.codigo_convite = gerar_codigo_convite()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nome


class Membro(models.Model):
    class Papel(models.TextChoices):
        ORGANIZADOR = 'organizador', 'Organizador'
        JOGADOR = 'jogador', 'Jogador'

    grupo = models.ForeignKey(Grupo, on_delete=models.CASCADE, related_name='membros')
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='participacoes'
    )
    papel = models.CharField(max_length=12, choices=Papel.choices, default=Papel.JOGADOR)
    posicao = models.CharField(max_length=3, choices=Posicao.choices, default=Posicao.MEIA)
    # Nota de habilidade (1 a 10) usada pela IA para equilibrar os times.
    nota = models.PositiveSmallIntegerField(
        default=5, validators=[MinValueValidator(1), MaxValueValidator(10)]
    )
    entrou_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['entrou_em']
        constraints = [
            models.UniqueConstraint(fields=['grupo', 'usuario'], name='membro_unico_por_grupo'),
        ]

    @property
    def eh_organizador(self):
        return self.papel == self.Papel.ORGANIZADOR

    def __str__(self):
        return f'{self.usuario.nome} em {self.grupo.nome}'
