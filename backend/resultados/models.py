from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from grupos.models import Membro
from partidas.models import Partida, Time


class Resultado(models.Model):
    """Placar de uma partida, lancado pelo organizador depois do jogo (#36)."""

    partida = models.OneToOneField(Partida, on_delete=models.CASCADE, related_name='resultado')
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='resultados_registrados'
    )
    registrado_em = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Resultado de {self.partida}'

    def placar(self):
        """[{time_id, nome, cor, gols}] na ordem dos times. O placar sai da soma dos gols."""
        gols = {}
        for gol in self.gols.all():
            gols[gol.time_id] = gols.get(gol.time_id, 0) + gol.quantidade
        return [
            {'time_id': t.id, 'nome': t.nome, 'cor': t.cor, 'gols': gols.get(t.id, 0)}
            for t in self.partida.times.all()
        ]

    def vencedor(self):
        """Time com mais gols, ou None se empatou no topo."""
        placar = sorted(self.placar(), key=lambda p: -p['gols'])
        if len(placar) < 2 or placar[0]['gols'] == placar[1]['gols']:
            return None
        return placar[0]


class Gol(models.Model):
    """Gols de um jogador num resultado. Sem jogador = gol contra / nao identificado."""

    resultado = models.ForeignKey(Resultado, on_delete=models.CASCADE, related_name='gols')
    time = models.ForeignKey(Time, on_delete=models.CASCADE, related_name='gols')
    jogador = models.ForeignKey(Membro, on_delete=models.CASCADE, null=True, blank=True, related_name='gols')
    quantidade = models.PositiveSmallIntegerField(default=1, validators=[MinValueValidator(1)])

    class Meta:
        ordering = ['time__ordem', '-quantidade']

    def __str__(self):
        autor = self.jogador.usuario.nome if self.jogador else 'sem autor'
        return f'{autor} x{self.quantidade} ({self.time.nome})'
