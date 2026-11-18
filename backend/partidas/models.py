from datetime import timedelta

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from grupos.models import Grupo, Membro

# Nome e cor de cada time, na ordem (no maximo 4 times por partida).
TIMES_PADRAO = [
    ('Verde', '#15803d'),
    ('Preto', '#1f2937'),
    ('Branco', '#e5e7eb'),
    ('Azul', '#1d4ed8'),
]

ANTECEDENCIAS = [1, 2, 3, 6, 12, 24]  # horas antes do jogo em que a IA monta os times


class Partida(models.Model):
    """Um jogo marcado no grupo."""

    class Status(models.TextChoices):
        ABERTA = 'aberta', 'Presenca aberta'
        SORTEANDO = 'sorteando', 'IA montando os times'
        RASCUNHO = 'rascunho', 'Times aguardando o organizador'
        PUBLICADA = 'publicada', 'Times publicados'
        ENCERRADA = 'encerrada', 'Encerrada'

    class Origem(models.TextChoices):
        IA = 'ia', 'IA (Gemini)'
        RESERVA = 'reserva', 'Algoritmo de reserva'

    grupo = models.ForeignKey(Grupo, on_delete=models.CASCADE, related_name='partidas')
    criada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='partidas_criadas'
    )
    data_hora = models.DateTimeField()
    local = models.CharField(max_length=120)
    num_times = models.PositiveSmallIntegerField(
        default=2, validators=[MinValueValidator(2), MaxValueValidator(len(TIMES_PADRAO))]
    )
    jogadores_por_time = models.PositiveSmallIntegerField(
        default=5, validators=[MinValueValidator(2), MaxValueValidator(11)]
    )
    antecedencia_horas = models.PositiveSmallIntegerField(
        default=2, choices=[(h, f'{h}h antes') for h in ANTECEDENCIAS]
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ABERTA)

    # Preenchidos quando os times sao montados
    explicacao_ia = models.TextField(blank=True)
    origem_times = models.CharField(max_length=7, choices=Origem.choices, blank=True)
    times_montados_em = models.DateTimeField(null=True, blank=True)
    times_publicados_em = models.DateTimeField(null=True, blank=True)
    # True quando o organizador troca jogadores depois do sorteio (a explicacao da IA fica defasada).
    ajustado_pelo_organizador = models.BooleanField(default=False)

    criada_em = models.DateTimeField(auto_now_add=True)
    atualizada_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['data_hora']

    def __str__(self):
        return f'{self.grupo.nome} - {timezone.localtime(self.data_hora):%d/%m %H:%M}'

    @property
    def vagas(self):
        return self.num_times * self.jogadores_por_time

    @property
    def sorteio_em(self):
        """Horario em que a IA monta os times sozinha."""
        return self.data_hora - timedelta(hours=self.antecedencia_horas)

    @property
    def minimo_para_sortear(self):
        return self.num_times * 2

    def confirmados(self):
        """Quem disse 'vou', na ordem de confirmacao (os primeiros ocupam as vagas)."""
        return (
            self.presencas.filter(status=Presenca.Status.VOU)
            .select_related('membro__usuario')
            .order_by('confirmada_em', 'id')
        )

    def titulares(self):
        return list(self.confirmados()[: self.vagas])


class Presenca(models.Model):
    class Status(models.TextChoices):
        VOU = 'vou', 'Vou'
        NAO_VOU = 'nao_vou', 'Nao vou'

    partida = models.ForeignKey(Partida, on_delete=models.CASCADE, related_name='presencas')
    membro = models.ForeignKey(Membro, on_delete=models.CASCADE, related_name='presencas')
    status = models.CharField(max_length=7, choices=Status.choices)
    # Muda toda vez que a pessoa passa para "vou": quem cancela e volta vai pro fim da fila.
    confirmada_em = models.DateTimeField(null=True, blank=True)
    atualizada_em = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['partida', 'membro'], name='presenca_unica_por_partida'),
        ]

    def __str__(self):
        return f'{self.membro.usuario.nome}: {self.status}'


class Time(models.Model):
    partida = models.ForeignKey(Partida, on_delete=models.CASCADE, related_name='times')
    nome = models.CharField(max_length=20)
    cor = models.CharField(max_length=7)
    ordem = models.PositiveSmallIntegerField()
    jogadores = models.ManyToManyField(Membro, related_name='times', blank=True)
    # Media das notas no momento do sorteio (a nota do membro pode mudar depois).
    forca = models.FloatField(default=0)

    class Meta:
        ordering = ['ordem']
        constraints = [
            models.UniqueConstraint(fields=['partida', 'ordem'], name='time_ordem_unica'),
        ]

    def __str__(self):
        return f'{self.nome} ({self.partida})'
