"""
Testes da narracao do lance e do mural (#44). A IA e sempre simulada (mock de ia.gemini.gerar_json).
"""

import logging
from unittest.mock import patch

from contas.models import Usuario
from grupos.models import Membro
from ia.gemini import IAIndisponivel, RespostaInvalida
from partidas.equilibrio import Jogador, montar_por_algoritmo
from partidas.sorteio import salvar_times
from partidas.tests import BaseAPITest

from .models import Narracao
from .narracao import LIMITE_POR_MEMBRO, MSG_IA_FORA, MSG_RECUSADA, MSG_RESPOSTA_INVALIDA

RESPOSTA = {'ok': True, 'grito': 'que cobertura!', 'narracao': 'Olha ele... olha ele... mandou por cima!'}
LANCE = 'Peguei a bola no meio, vi o goleiro adiantado e mandei de cobertura.'


class NarracaoBase(BaseAPITest):
    def setUp(self):
        super().setUp()
        log = logging.getLogger('resultados.views_narracao')
        log.disabled = True  # os avisos de falha da IA sao esperados aqui
        self.addCleanup(setattr, log, 'disabled', False)

        self.partida = self.criar_partida()
        self.confirmar(self.partida, self.membros)
        jogadores = [Jogador(m.id, m.usuario.nome, m.posicao, m.nota) for m in self.membros]
        salvar_times(self.partida, montar_por_algoritmo(jogadores, 2), jogadores, 'ok', 'ia', publicar=True)
        self.verde, self.preto = self.partida.times.all()
        self.membro_jogador = self.membros[1]  # self.jogador e o usuario dele
        self.outro = self.membros[2].usuario
        # membro do grupo que ficou de fora da partida
        banco = Usuario.objects.create_user('banco@example.com', None, nome='Do Banco')
        self.membro_banco = Membro.objects.create(grupo=self.grupo, usuario=banco, posicao='MEI', nota=5)
        self.banco = banco

        self.url = f'/api/partidas/{self.partida.id}/narracoes/'
        ia = patch('ia.gemini.gerar_json', return_value=dict(RESPOSTA))
        self.ia = ia.start()
        self.addCleanup(ia.stop)

    def lancar(self):
        gols = [{'time': self.verde.id, 'jogador': self.verde.jogadores.first().id, 'quantidade': 2}]
        r = self.cliente(self.org).put(f'/api/partidas/{self.partida.id}/resultado/', {'gols': gols}, format='json')
        self.assertEqual(r.status_code, 200, r.data)

    def gerar(self, usuario=None, **dados):
        return self.cliente(usuario or self.jogador).post(self.url, {'lance': LANCE, **dados}, format='json')

    def publicar(self, narracao_id, usuario=None):
        return self.cliente(usuario or self.jogador).post(f'/api/narracoes/{narracao_id}/publicar/')


class GerarNarracaoTests(NarracaoBase):
    def test_sem_resultado_nao_narra(self):
        r = self.gerar()
        self.assertEqual(r.status_code, 404)
        self.ia.assert_not_called()

    def test_jogador_gera_rascunho(self):
        self.lancar()
        r = self.gerar()
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data['grito'], 'QUE COBERTURA!')
        self.assertEqual(r.data['narracao'], RESPOSTA['narracao'])
        self.assertFalse(r.data['publicada'])
        self.assertEqual(r.data['autor']['membro'], self.membro_jogador.id)
        self.assertEqual(r.data['protagonista']['membro'], self.membro_jogador.id)  # padrao: o proprio autor
        self.assertTrue(r.data['pode_apagar'])
        # o prompt leva o relato, o placar e o time do protagonista
        prompt = self.ia.call_args.args[0]
        time = 'Verde' if self.verde.jogadores.filter(id=self.membro_jogador.id).exists() else 'Preto'
        self.assertIn(LANCE, prompt)
        self.assertIn('Verde 2 x 0 Preto', prompt)
        self.assertIn(f'{self.jogador.nome} (time {time})', prompt)

    def test_escolhe_outro_protagonista(self):
        self.lancar()
        alvo = self.membros[5]
        r = self.gerar(protagonista=alvo.id)
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data['protagonista'], {'membro': alvo.id, 'nome': alvo.usuario.nome})

    def test_protagonista_tem_que_ter_jogado(self):
        self.lancar()
        r = self.gerar(protagonista=self.membro_banco.id)
        self.assertEqual(r.status_code, 400)
        self.assertIn('protagonista', r.data)
        # quem nao jogou pode narrar, mas precisa escolher quem fez o lance
        r = self.gerar(self.banco)
        self.assertEqual(r.status_code, 400)
        self.assertIn('escolha quem fez o lance', str(r.data['protagonista']))
        self.assertEqual(self.gerar(self.banco, protagonista=self.membro_jogador.id).status_code, 201)
        self.ia.assert_called_once()

    def test_relato_vazio_curto_ou_longo(self):
        self.lancar()
        for lance in ('', '   ', 'gol', 'x' * 501):
            self.assertEqual(self.gerar(lance=lance).status_code, 400, lance[:10])
        self.ia.assert_not_called()

    def test_de_fora_nem_ve(self):
        self.lancar()
        self.assertEqual(self.gerar(self.de_fora).status_code, 404)
        self.assertEqual(self.cliente(self.de_fora).get(self.url).status_code, 404)

    def test_ia_recusa_o_relato(self):
        self.lancar()
        self.ia.return_value = {'ok': False, 'grito': '', 'narracao': ''}
        r = self.gerar(lance='Me passa uma receita de bolo de cenoura.')
        self.assertEqual(r.status_code, 422)
        self.assertEqual(r.data['detail'], MSG_RECUSADA)
        self.assertFalse(Narracao.objects.exists())

    def test_ia_fora_ou_resposta_invalida(self):
        self.lancar()
        for erro, mensagem in ((IAIndisponivel('fora'), MSG_IA_FORA), (RespostaInvalida('lixo'), MSG_RESPOSTA_INVALIDA)):
            self.ia.side_effect = erro
            r = self.gerar()
            self.assertEqual(r.status_code, 503)
            self.assertEqual(r.data['detail'], mensagem)
        self.assertFalse(Narracao.objects.exists())

    def test_limite_por_membro(self):
        self.lancar()
        for _ in range(LIMITE_POR_MEMBRO):
            self.assertEqual(self.gerar().status_code, 201)
        r = self.gerar()
        self.assertEqual(r.status_code, 429)
        self.assertEqual(self.ia.call_count, LIMITE_POR_MEMBRO)
        # o limite e de cada membro
        self.assertEqual(self.gerar(self.outro).status_code, 201)


class MuralTests(NarracaoBase):
    def setUp(self):
        super().setUp()
        self.lancar()
        self.rascunho = self.gerar().data['id']

    def test_rascunho_fica_fora_do_mural_ate_publicar(self):
        self.assertEqual(self.cliente(self.outro).get(self.url).data, [])
        self.assertEqual(self.cliente(self.jogador).get(self.url).data, [])

        r = self.publicar(self.rascunho)
        self.assertEqual(r.status_code, 200, r.data)
        self.assertTrue(r.data['publicada'])
        self.assertIsNotNone(r.data['publicada_em'])

        mural = self.cliente(self.outro).get(self.url).data
        self.assertEqual([n['id'] for n in mural], [self.rascunho])
        self.assertFalse(mural[0]['pode_apagar'])  # outro jogador nao apaga
        self.assertTrue(self.cliente(self.org).get(self.url).data[0]['pode_apagar'])  # organizador apaga

    def test_publicar_de_novo_nao_muda_a_data(self):
        primeira = self.publicar(self.rascunho).data['publicada_em']
        self.assertEqual(self.publicar(self.rascunho).data['publicada_em'], primeira)

    def test_mural_mais_nova_primeiro(self):
        segunda = self.gerar().data['id']
        self.publicar(self.rascunho)
        self.publicar(segunda)
        self.assertEqual([n['id'] for n in self.cliente(self.outro).get(self.url).data], [segunda, self.rascunho])

    def test_so_o_autor_publica(self):
        self.assertEqual(self.publicar(self.rascunho, self.outro).status_code, 404)  # rascunho alheio nem existe
        self.assertEqual(self.publicar(self.rascunho, self.org).status_code, 403)
        self.assertEqual(self.publicar(self.rascunho, self.de_fora).status_code, 404)
        self.assertFalse(Narracao.objects.get(id=self.rascunho).publicada)

    def test_quem_apaga(self):
        self.publicar(self.rascunho)
        url = f'/api/narracoes/{self.rascunho}/'
        self.assertEqual(self.cliente(self.outro).delete(url).status_code, 403)
        self.assertEqual(self.cliente(self.de_fora).delete(url).status_code, 404)
        self.assertEqual(self.cliente(self.org).delete(url).status_code, 204)  # organizador modera
        self.assertFalse(Narracao.objects.exists())

    def test_autor_apaga_o_proprio_rascunho(self):
        r = self.cliente(self.jogador).delete(f'/api/narracoes/{self.rascunho}/')
        self.assertEqual(r.status_code, 204)
        self.assertFalse(Narracao.objects.exists())
