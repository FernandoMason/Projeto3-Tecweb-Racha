"""
Dados de teste (#26):  python manage.py popular_racha

Cria 14 jogadores (@example.com, senha racha1234), o grupo "Pelada de quinta",
uma partida ja jogada (times + placar) e a proxima quinta com 8 confirmados.
Rodar de novo apaga e recria so esses dados de exemplo.
"""

from datetime import datetime, time, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from contas.models import Usuario
from grupos.models import Grupo, Membro
from partidas import equilibrio
from partidas.models import Partida, Presenca
from partidas.sorteio import jogadores_da_partida, salvar_times
from resultados.models import Gol, Resultado

DOMINIO = '@example.com'
SENHA = 'racha1234'

# nome, posicao, nota
JOGADORES = [
    ('João', 'ATA', 9),
    ('Pedro', 'MEI', 8),
    ('Caio', 'ATA', 8),
    ('Lucas', 'ZAG', 7),
    ('Ana', 'MEI', 7),
    ('Gui', 'GOL', 7),
    ('Rafa', 'GOL', 6),
    ('Bia', 'MEI', 6),
    ('Leo', 'ZAG', 6),
    ('Duda', 'ATA', 6),
    ('Davi', 'ATA', 5),
    ('Theo', 'ZAG', 5),
    ('Nina', 'MEI', 4),
    ('Igor', 'MEI', 3),
]


def quinta(semanas, hora=20):
    """Quinta-feira relativa a hoje: 0 = a proxima (ou hoje), -1 = a anterior."""
    hoje = timezone.localdate()
    dias = (3 - hoje.weekday()) % 7 + 7 * semanas
    dia = hoje + timedelta(days=dias)
    return timezone.make_aware(datetime.combine(dia, time(hora)))


class Command(BaseCommand):
    help = 'Cria usuarios, grupo, membros e partidas de exemplo (senha racha1234).'

    @transaction.atomic
    def handle(self, *args, **opcoes):
        Grupo.objects.filter(criado_por__email__endswith=DOMINIO).delete()
        Usuario.objects.filter(email__endswith=DOMINIO).delete()

        usuarios = []
        for nome, posicao, _ in JOGADORES:
            email = nome.lower().replace('ã', 'a') + DOMINIO
            usuarios.append(Usuario.objects.create_user(email=email, password=SENHA, nome=nome, posicao=posicao))

        organizador = usuarios[0]
        grupo = Grupo.objects.create(nome='Pelada de quinta', criado_por=organizador)
        membros = [
            Membro.objects.create(
                grupo=grupo,
                usuario=u,
                posicao=posicao,
                nota=nota,
                papel=Membro.Papel.ORGANIZADOR if u == organizador else Membro.Papel.JOGADOR,
            )
            for u, (_, posicao, nota) in zip(usuarios, JOGADORES)
        ]

        # Partida da semana passada: ja jogada, com times e placar.
        passada = Partida.objects.create(
            grupo=grupo, criada_por=organizador, data_hora=quinta(-1), local='Arena Society'
        )
        agora = timezone.now()
        for i, m in enumerate(membros[:10]):
            Presenca.objects.create(
                partida=passada, membro=m, status='vou', confirmada_em=agora - timedelta(days=8, minutes=-i)
            )
        jogadores = jogadores_da_partida(passada)
        times_ids = equilibrio.montar_por_algoritmo(jogadores, passada.num_times)
        por_id = {j.id: j for j in jogadores}
        times = [[por_id[i] for i in ids] for ids in times_ids]
        goleiros = [next(j.nome for j in t if j.posicao == 'GOL') for t in times]
        craques = [max(t, key=lambda j: j.nota).nome for t in times]
        salvar_times(
            passada,
            times_ids,
            jogadores,
            f'Separei o {goleiros[0]} e o {goleiros[1]} no gol e coloquei o {craques[0]} e o {craques[1]} '
            'em lados opostos. Jogo pra ser decidido no detalhe!',
            Partida.Origem.IA,
            publicar=True,
        )
        verde, preto = passada.times.all()
        resultado = Resultado.objects.create(partida=passada, registrado_por=organizador)
        artilheiros_verde = [m for m in verde.jogadores.all() if m.posicao == 'ATA'] or list(verde.jogadores.all())
        artilheiros_preto = [m for m in preto.jogadores.all() if m.posicao == 'ATA'] or list(preto.jogadores.all())
        Gol.objects.create(resultado=resultado, time=verde, jogador=artilheiros_verde[0], quantidade=3)
        Gol.objects.create(resultado=resultado, time=verde, jogador=next(
            m for m in verde.jogadores.all() if m != artilheiros_verde[0]), quantidade=2)
        Gol.objects.create(resultado=resultado, time=preto, jogador=artilheiros_preto[0], quantidade=2)
        Gol.objects.create(resultado=resultado, time=preto, jogador=None, quantidade=1)
        passada.status = Partida.Status.ENCERRADA
        passada.save()

        # Proxima quinta: presenca aberta, 8 de 10 confirmados, 2 nao vao.
        proxima = Partida.objects.create(
            grupo=grupo, criada_por=organizador, data_hora=quinta(0 if quinta(0) > agora else 1),
            local='Arena Society',
        )
        for i, m in enumerate(membros[:8]):
            Presenca.objects.create(partida=proxima, membro=m, status='vou', confirmada_em=agora - timedelta(hours=10 - i))
        for m in membros[12:]:
            Presenca.objects.create(partida=proxima, membro=m, status='nao_vou')

        self.stdout.write(self.style.SUCCESS(
            f'Grupo "{grupo.nome}" ({grupo.codigo_convite}) com {len(membros)} jogadores e 2 partidas.\n'
            f'Entre como organizador: joao{DOMINIO} / {SENHA}  (jogador comum: pedro{DOMINIO})'
        ))
