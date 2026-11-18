"""
Testes da cronica da rodada (#40). A IA e sempre simulada (mock de ia.gemini.gerar_json).
"""

import logging
from unittest.mock import patch

from django.utils import timezone

from ia.gemini import IAIndisponivel, RespostaInvalida
from partidas.equilibrio import Jogador, montar_por_algoritmo
from partidas.sorteio import salvar_times
from partidas.tests import BaseAPITest

from .cronica import MSG_IA_FORA, dados_da_partida
from .models import Cronica, Resultado


class CronicaBase(BaseAPITest):
    def setUp(self):
        super().setUp()
        log = logging.getLogger('resultados.cronica')
        log.disabled = True  # os avisos de falha da IA sao esperados aqui
        self.addCleanup(setattr, log, 'disabled', False)

        self.partida = self.criar_partida(local='Arena Society')
        self.confirmar(self.partida, self.membros)
        jogadores = [Jogador(m.id, m.usuario.nome, m.posicao, m.nota) for m in self.membros]
        salvar_times(self.partida, montar_por_algoritmo(jogadores, 2), jogadores, 'ok', 'ia', publicar=True)
        self.verde, self.preto = self.partida.times.all()
        self.artilheiro = self.verde.jogadores.first()
        self.url_resultado = f'/api/partidas/{self.partida.id}/resultado/'
        self.url = f'/api/partidas/{self.partida.id}/resultado/cronica/'

    def lancar(self, gols=None):
        if gols is None:  # Verde 3 x 2 Preto: artilheiro com 3, um do Preto com 1 e um gol contra
            gols = [
                {'time': self.verde.id, 'jogador': self.artilheiro.id, 'quantidade': 3},
                {'time': self.preto.id, 'jogador': self.preto.jogadores.first().id, 'quantidade': 1},
                {'time': self.preto.id, 'jogador': None},
            ]
        r = self.cliente(self.org).put(self.url_resultado, {'gols': gols}, format='json')
        self.assertEqual(r.status_code, 200, r.data)

    def resposta_da_ia(self, craque_id=None, **extra):
        return {
            'titulo': 'Noite de gala',
            'texto': 'Primeiro parágrafo.\n\nSegundo parágrafo.',
            'craque_id': craque_id if craque_id is not None else self.artilheiro.id,
            'motivo_craque': 'Fez os três gols do Verde.',
            **extra,
        }


class DadosDaPartidaTests(CronicaBase):
    def test_monta_placar_gols_e_jogadores(self):
        self.lancar()
        dados = dados_da_partida(Resultado.objects.get(partida=self.partida))
        self.assertEqual(dados['grupo'], 'Pelada')
        self.assertEqual(dados['local'], 'Arena Society')
        # data com a hora local, para a cronica saber se foi de manha, tarde ou noite
        self.assertRegex(dados['data'], r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$')
        self.assertEqual(dados['data'], timezone.localtime(self.partida.data_hora).strftime('%Y-%m-%dT%H:%M'))
        self.assertEqual([(t['nome'], t['gols']) for t in dados['times']], [('Verde', 3), ('Preto', 2)])
        jogadores_verde = {j['id']: j for j in dados['times'][0]['jogadores']}
        self.assertEqual(len(jogadores_verde), self.verde.jogadores.count())
        self.assertEqual(jogadores_verde[self.artilheiro.id]['gols'], 3)
        self.assertEqual(jogadores_verde[self.artilheiro.id]['nome'], self.artilheiro.usuario.nome)
        # 2 gols do Preto, 1 com autor: o gol contra fica sem autor
        self.assertEqual(sum(j['gols'] for j in dados['times'][1]['jogadores']), 1)


class GerarCronicaTests(CronicaBase):
    @patch('ia.gemini.gerar_json')
    def test_organizador_gera_e_membro_ve(self, ia):
        ia.return_value = self.resposta_da_ia()
        self.lancar()

        r = self.cliente(self.org).post(self.url)
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['status'], 'ok')
        self.assertEqual(r.data['titulo'], 'Noite de gala')
        self.assertEqual(r.data['craque']['membro'], self.artilheiro.id)
        self.assertEqual(r.data['origem_craque'], 'ia')
        self.assertFalse(r.data['desatualizada'])
        self.assertIn('Verde 3 x 2 Preto', ia.call_args.args[0])

        r = self.cliente(self.jogador).get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['texto'], 'Primeiro parágrafo.\n\nSegundo parágrafo.')

    @patch('ia.gemini.gerar_json')
    def test_put_do_resultado_nao_chama_a_ia(self, ia):
        self.lancar()
        ia.assert_not_called()
        self.assertFalse(Cronica.objects.exists())

    @patch('ia.gemini.gerar_json', side_effect=IAIndisponivel('429 RESOURCE_EXHAUSTED chave=abc'))
    def test_ia_fora_salva_erro_com_artilheiro(self, ia):
        self.lancar()
        r = self.cliente(self.org).post(self.url)
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['status'], 'erro')
        self.assertEqual(r.data['erro'], MSG_IA_FORA)
        self.assertNotIn('abc', str(r.data))  # detalhe tecnico nao vai para a tela
        self.assertEqual(r.data['craque']['membro'], self.artilheiro.id)
        self.assertEqual(r.data['origem_craque'], 'artilheiro')
        self.assertEqual(r.data['texto'], '')

    @patch('ia.gemini.gerar_json', side_effect=RespostaInvalida('json quebrado'))
    def test_zero_a_zero_sem_ia_fica_sem_craque(self, ia):
        self.lancar(gols=[])
        r = self.cliente(self.org).post(self.url)
        self.assertEqual(r.data['status'], 'erro')
        self.assertIsNone(r.data['craque'])
        self.assertEqual(r.data['origem_craque'], '')

    @patch('ia.gemini.gerar_json')
    def test_gerar_de_novo_depois_do_erro(self, ia):
        self.lancar()
        ia.side_effect = IAIndisponivel('fora')
        self.assertEqual(self.cliente(self.org).post(self.url).data['status'], 'erro')
        ia.side_effect = None
        ia.return_value = self.resposta_da_ia()
        r = self.cliente(self.org).post(self.url)
        self.assertEqual(r.data['status'], 'ok')
        self.assertEqual(r.data['erro'], '')
        self.assertEqual(Cronica.objects.count(), 1)

    @patch('ia.gemini.gerar_json')
    def test_falha_ao_gerar_de_novo_mantem_a_cronica_boa(self, ia):
        self.lancar()
        ia.return_value = self.resposta_da_ia()
        self.cliente(self.org).post(self.url)

        ia.side_effect = IAIndisponivel('fora')
        r = self.cliente(self.org).post(self.url)
        self.assertEqual(r.status_code, 503)
        self.assertEqual(r.data['detail'], MSG_IA_FORA)
        self.assertEqual(r.data['cronica']['titulo'], 'Noite de gala')
        self.assertEqual(Cronica.objects.get().status, Cronica.Status.OK)

    @patch('ia.gemini.gerar_json')
    def test_corrigir_placar_deixa_desatualizada(self, ia):
        self.lancar()
        ia.return_value = self.resposta_da_ia()
        self.cliente(self.org).post(self.url)

        self.lancar(gols=[{'time': self.preto.id, 'jogador': None, 'quantidade': 1}])
        r = self.cliente(self.jogador).get(self.url)
        self.assertTrue(r.data['desatualizada'])

        # com o placar novo, a falha da IA nao mantem a cronica velha: vira erro com o plano B
        ia.side_effect = IAIndisponivel('fora')
        r = self.cliente(self.org).post(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['status'], 'erro')
        self.assertFalse(r.data['desatualizada'])

        ia.side_effect = None
        r = self.cliente(self.org).post(self.url)
        self.assertEqual(r.data['status'], 'ok')
        self.assertFalse(r.data['desatualizada'])
        self.assertIn('Verde 0 x 1 Preto', ia.call_args.args[0])

    @patch('ia.gemini.gerar_json')
    def test_craque_que_nao_jogou_vira_artilheiro(self, ia):
        ia.return_value = self.resposta_da_ia(craque_id=999999)
        self.lancar()
        r = self.cliente(self.org).post(self.url)
        self.assertEqual(r.data['status'], 'ok')
        self.assertEqual(r.data['origem_craque'], 'artilheiro')
        self.assertEqual(r.data['craque']['membro'], self.artilheiro.id)


class PermissoesCronicaTests(CronicaBase):
    @patch('ia.gemini.gerar_json')
    def test_so_organizador_gera(self, ia):
        self.lancar()
        self.assertEqual(self.cliente(self.jogador).post(self.url).status_code, 403)
        ia.assert_not_called()

    def test_de_fora_nao_ve_nem_gera(self):
        self.lancar()
        self.assertEqual(self.cliente(self.de_fora).get(self.url).status_code, 404)
        self.assertEqual(self.cliente(self.de_fora).post(self.url).status_code, 404)

    @patch('ia.gemini.gerar_json')
    def test_sem_resultado_da_404(self, ia):
        self.assertEqual(self.cliente(self.org).post(self.url).status_code, 404)
        self.assertEqual(self.cliente(self.jogador).get(self.url).status_code, 404)
        ia.assert_not_called()

    def test_antes_de_gerar_da_404(self):
        self.lancar()
        r = self.cliente(self.jogador).get(self.url)
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.data['detail'], 'A crônica ainda não foi gerada.')
