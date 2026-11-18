"""Testes do ranking do grupo (#42). Nenhum teste chama a IA."""

from datetime import timedelta

from django.test import SimpleTestCase
from django.utils import timezone

from partidas.equilibrio import Jogador, montar_por_algoritmo
from partidas.sorteio import salvar_times
from partidas.tests import BaseAPITest

from .models import Cronica, Resultado
from .ranking import _ordenar_com_colocacao


class ColocacaoTests(SimpleTestCase):
    def test_empate_divide_a_colocacao_e_zero_nao_entra(self):
        itens = [
            {'nome': 'Caio', 'gols': 5, 'jogos': 3},
            {'nome': 'João', 'gols': 12, 'jogos': 6},
            {'nome': 'Pedro', 'gols': 9, 'jogos': 6},
            {'nome': 'Lucas', 'gols': 9, 'jogos': 4},
            {'nome': 'Zé', 'gols': 0, 'jogos': 2},
        ]
        ordenado = _ordenar_com_colocacao(itens, 'gols')
        self.assertEqual(
            [(i['colocacao'], i['nome']) for i in ordenado],
            [(1, 'João'), (2, 'Lucas'), (2, 'Pedro'), (4, 'Caio')],  # no empate, menos jogos primeiro
        )


class RankingAPITests(BaseAPITest):
    def setUp(self):
        super().setUp()
        self.url = f'/api/grupos/{self.grupo.id}/ranking/'

    def partida_com_times(self, dias_atras):
        partida = self.criar_partida(data_hora=timezone.now() - timedelta(days=dias_atras))
        self.confirmar(partida, self.membros)
        jogadores = [Jogador(m.id, m.usuario.nome, m.posicao, m.nota) for m in self.membros]
        salvar_times(partida, montar_por_algoritmo(jogadores, 2), jogadores, 'ok', 'ia', publicar=True)
        return partida

    def lancar(self, partida, gols):
        r = self.cliente(self.org).put(f'/api/partidas/{partida.id}/resultado/', {'gols': gols}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        return Resultado.objects.get(partida=partida)

    def cronica(self, resultado, craque, desatualizada=False):
        baseada_em = resultado.registrado_em - timedelta(minutes=1) if desatualizada else resultado.registrado_em
        Cronica.objects.create(
            resultado=resultado, status='ok', titulo='t', texto='x', craque=craque, motivo_craque='m',
            origem_craque='ia', gerada_em=timezone.now(), baseada_em=baseada_em,
        )

    def montar_cenario(self):
        # Partida 1: Verde 3 x 2 Preto (A faz 3; B faz 1 pelo Preto; 1 gol contra)
        p1 = self.partida_com_times(dias_atras=7)
        verde, preto = p1.times.all()
        self.verde1 = set(verde.jogadores.values_list('id', flat=True))
        self.preto1 = set(preto.jogadores.values_list('id', flat=True))
        self.a = verde.jogadores.order_by('id').first()
        self.b = preto.jogadores.order_by('id').first()
        r1 = self.lancar(p1, [
            {'time': verde.id, 'jogador': self.a.id, 'quantidade': 3},
            {'time': preto.id, 'jogador': self.b.id, 'quantidade': 1},
            {'time': preto.id, 'jogador': None},
        ])
        self.cronica(r1, craque=self.a)

        # Partida 2: 1 x 1 (A marca pelo time dele; C, do outro time, empata)
        p2 = self.partida_com_times(dias_atras=1)
        time_a = p2.times.get(jogadores=self.a)
        time_c = p2.times.exclude(pk=time_a.pk).get()
        self.c = time_c.jogadores.order_by('id').first()
        r2 = self.lancar(p2, [
            {'time': time_a.id, 'jogador': self.a.id, 'quantidade': 1},
            {'time': time_c.id, 'jogador': self.c.id, 'quantidade': 1},
        ])
        self.cronica(r2, craque=self.c, desatualizada=True)  # nao conta

        # Partida 3: sem resultado, nao conta
        self.partida_com_times(dias_atras=0)

    def por_membro(self, lista):
        return {item['membro']: item for item in lista}

    def test_ranking_soma_as_partidas_com_resultado(self):
        self.montar_cenario()
        r = self.cliente(self.jogador).get(self.url)
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['jogos'], 2)

        artilharia = self.por_membro(r.data['artilharia'])
        self.assertEqual(r.data['artilharia'][0]['membro'], self.a.id)
        self.assertEqual(artilharia[self.a.id]['gols'], 4)  # 3 + 1, somando as duas partidas
        self.assertEqual(artilharia[self.a.id]['jogos'], 2)
        self.assertEqual(artilharia[self.a.id]['colocacao'], 1)
        # 6 gols com autor no total (3 + 1 na partida 1, 1 + 1 na 2); o gol contra nao vai para ninguem
        self.assertEqual(sum(i['gols'] for i in r.data['artilharia']), 6)
        self.assertEqual(set(artilharia), {self.a.id, self.b.id, self.c.id})

        vitorias = self.por_membro(r.data['vitorias'])
        self.assertEqual(set(vitorias), self.verde1)  # so o Verde da partida 1 venceu
        for item in vitorias.values():
            self.assertEqual((item['vitorias'], item['empates'], item['derrotas'], item['jogos']), (1, 1, 0, 2))
            self.assertEqual(item['colocacao'], 1)

        # a cronica desatualizada da partida 2 nao conta
        self.assertEqual(
            [(c['membro'], c['vezes'], c['colocacao']) for c in r.data['craques']], [(self.a.id, 1, 1)]
        )

    def test_grupo_sem_resultado(self):
        self.partida_com_times(dias_atras=1)
        r = self.cliente(self.org).get(self.url)
        self.assertEqual(r.data, {'jogos': 0, 'artilharia': [], 'vitorias': [], 'craques': []})

    def test_de_fora_recebe_404(self):
        self.assertEqual(self.cliente(self.de_fora).get(self.url).status_code, 404)
        self.assertEqual(self.cliente(self.org).get('/api/grupos/999999/ranking/').status_code, 404)

    def test_corrigir_placar_muda_o_ranking(self):
        self.montar_cenario()
        p1 = Resultado.objects.order_by('partida__data_hora').first().partida
        verde, preto = p1.times.all()
        self.lancar(p1, [{'time': preto.id, 'jogador': self.b.id, 'quantidade': 2}])  # agora 0 x 2

        r = self.cliente(self.org).get(self.url)
        self.assertEqual(set(self.por_membro(r.data['vitorias'])), self.preto1)
        self.assertEqual(r.data['craques'], [])  # a cronica da partida 1 ficou desatualizada
