"""
python manage.py montar_times_agendados

Monta (IA) e publica os times de toda partida que ja passou do horario do sorteio.
O app ja faz isso quando alguem abre a partida; este comando e para um cron
no deploy (ex.: a cada 10 min), para os times sairem mesmo que ninguem abra o app.
"""

from django.core.management.base import BaseCommand

from partidas.models import Partida
from partidas.sorteio import montar_se_chegou_a_hora


class Command(BaseCommand):
    help = 'Monta e publica os times das partidas cujo horario de sorteio ja chegou.'

    def handle(self, *args, **opcoes):
        montadas = 0
        for partida in Partida.objects.filter(status=Partida.Status.ABERTA):
            if montar_se_chegou_a_hora(partida).status == Partida.Status.PUBLICADA:
                montadas += 1
                self.stdout.write(f'Times publicados: {partida}')
        self.stdout.write(self.style.SUCCESS(f'{montadas} partida(s) com times montados.'))
