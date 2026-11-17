from partidas.equilibrio import Jogador, montar_por_algoritmo
from partidas.models import Partida
from partidas.sorteio import salvar_times
from partidas.tests import BaseAPITest


class ResultadoAPITests(BaseAPITest):
    def setUp(self):
        super().setUp()
        self.partida = self.criar_partida()
        self.confirmar(self.partida, self.membros)
        jogadores = [Jogador(m.id, m.usuario.nome, m.posicao, m.nota) for m in self.membros]
        salvar_times(self.partida, montar_por_algoritmo(jogadores, 2), jogadores, 'ok', 'ia', publicar=True)
        self.verde, self.preto = self.partida.times.all()
        self.url = f'/api/partidas/{self.partida.id}/resultado/'

    def gols(self):
        artilheiro = self.verde.jogadores.first()
        return {
            'gols': [
                {'time': self.verde.id, 'jogador': artilheiro.id, 'quantidade': 3},
                {'time': self.preto.id, 'jogador': self.preto.jogadores.first().id, 'quantidade': 1},
                {'time': self.preto.id, 'jogador': None},  # gol contra
            ]
        }

    def test_organizador_lanca_placar_e_encerra(self):
        r = self.cliente(self.org).put(self.url, self.gols(), format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual([p['gols'] for p in r.data['placar']], [3, 2])
        self.assertEqual(r.data['vencedor']['nome'], 'Verde')
        self.partida.refresh_from_db()
        self.assertEqual(self.partida.status, Partida.Status.ENCERRADA)

        # qualquer membro ve o resultado, e ele aparece no detalhe da partida
        r = self.cliente(self.jogador).get(self.url)
        self.assertEqual(len(r.data['gols']), 3)
        r = self.cliente(self.jogador).get(f'/api/partidas/{self.partida.id}/')
        self.assertEqual(r.data['placar'][0]['gols'], 3)

    def test_corrigir_placar_substitui_os_gols(self):
        c = self.cliente(self.org)
        c.put(self.url, self.gols(), format='json')
        r = c.put(self.url, {'gols': []}, format='json')
        self.assertEqual([p['gols'] for p in r.data['placar']], [0, 0])
        self.assertIsNone(r.data['vencedor'])

    def test_jogador_de_outro_time_e_recusado(self):
        dados = {'gols': [{'time': self.verde.id, 'jogador': self.preto.jogadores.first().id}]}
        r = self.cliente(self.org).put(self.url, dados, format='json')
        self.assertEqual(r.status_code, 400)

    def test_so_organizador_lanca(self):
        self.assertEqual(self.cliente(self.jogador).put(self.url, self.gols(), format='json').status_code, 403)

    def test_precisa_dos_times_publicados(self):
        Partida.objects.filter(pk=self.partida.pk).update(status=Partida.Status.RASCUNHO)
        r = self.cliente(self.org).put(self.url, self.gols(), format='json')
        self.assertEqual(r.status_code, 400)

    def test_sem_resultado_da_404_e_de_fora_tambem(self):
        self.assertEqual(self.cliente(self.jogador).get(self.url).status_code, 404)
        self.assertEqual(self.cliente(self.de_fora).put(self.url, self.gols(), format='json').status_code, 404)
