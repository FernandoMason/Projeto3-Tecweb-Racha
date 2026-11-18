"""
Testes de partidas, presenca e sorteio (#32).

A IA e sempre simulada (mock de ia.gemini.gerar_json): os testes nao usam
internet nem gastam cota, e conseguimos forcar respostas erradas da IA para
conferir que a validacao e o plano B funcionam.
"""

from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from contas.models import Usuario
from grupos.models import Grupo, Membro
from ia.gemini import IAIndisponivel

from . import equilibrio
from .equilibrio import Jogador
from .models import Partida, Presenca

NOTAS = [('GOL', 7), ('GOL', 6), ('ZAG', 7), ('ZAG', 5), ('MEI', 8), ('MEI', 6), ('ATA', 9), ('ATA', 5), ('MEI', 4), ('ATA', 7)]


# ---------------------------------------------------------------- equilibrio (sem banco)
class EquilibrioTests(TestCase):
    def setUp(self):
        self.jogadores = [Jogador(i, f'J{i}', pos, nota) for i, (pos, nota) in enumerate(NOTAS, start=1)]

    def test_algoritmo_coloca_todo_mundo_uma_vez_e_separa_goleiros(self):
        for _ in range(20):  # tem aleatoriedade nos empates
            times = equilibrio.montar_por_algoritmo(self.jogadores, 2)
            self.assertEqual(sorted(i for t in times for i in t), list(range(1, 11)))
            self.assertEqual([len(t) for t in times], [5, 5])
            self.assertEqual(equilibrio.validar(times, self.jogadores, 2, referencia=0), [])

    def test_algoritmo_com_tres_times_e_sobra(self):
        jogadores = self.jogadores + [Jogador(11, 'J11', 'ZAG', 6)]
        times = equilibrio.montar_por_algoritmo(jogadores, 3)
        self.assertEqual(sorted(len(t) for t in times), [3, 4, 4])

    def test_validar_aponta_cada_tipo_de_erro(self):
        def erros(times):
            return ' '.join(equilibrio.validar(times, self.jogadores, 2, referencia=0))

        self.assertIn('Eram 2 times', erros([[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]]))
        self.assertIn('nao esta na lista', erros([[1, 3, 5, 7, 99], [2, 4, 6, 8, 10]]))
        self.assertIn('mais de um time', erros([[1, 3, 5, 7, 9], [2, 4, 6, 8, 9, 10]]))
        self.assertIn('Ficaram de fora', erros([[1, 3, 5, 7], [2, 4, 6, 8, 10]]))
        self.assertIn('diferenca maxima e de 1', erros([[1, 3, 5], [2, 4, 6, 7, 8, 9, 10]]))
        self.assertIn('goleiros', erros([[1, 2, 3, 4, 5], [6, 7, 8, 9, 10]]))
        # todos os fortes de um lado: estrutura ok, mas desequilibrado
        self.assertIn('desequilibrados', erros([[1, 3, 5, 7, 10], [2, 4, 6, 8, 9]]))

    def test_forca_e_media(self):
        self.assertEqual(equilibrio.forca([Jogador(1, 'a', 'MEI', 6), Jogador(2, 'b', 'MEI', 9)]), 7.5)


# ---------------------------------------------------------------- API
class BaseAPITest(TestCase):
    def setUp(self):
        # senha None = sem hash (os testes usam force_authenticate), deixa a suite bem mais rapida
        self.org = Usuario.objects.create_user('org@example.com', None, nome='Org')
        self.grupo = Grupo.objects.create(nome='Pelada', criado_por=self.org)
        self.membros = []
        for i, (pos, nota) in enumerate(NOTAS):
            usuario = self.org if i == 0 else Usuario.objects.create_user(f'j{i}@example.com', None, nome=f'Jogador {i}')
            papel = Membro.Papel.ORGANIZADOR if i == 0 else Membro.Papel.JOGADOR
            self.membros.append(
                Membro.objects.create(grupo=self.grupo, usuario=usuario, posicao=pos, nota=nota, papel=papel)
            )
        self.jogador = self.membros[1].usuario
        self.de_fora = Usuario.objects.create_user('fora@example.com', None, nome='De fora')

    def cliente(self, usuario):
        c = APIClient()
        c.force_authenticate(usuario)
        return c

    def criar_partida(self, **extra):
        dados = {'data_hora': timezone.now() + timedelta(days=2), 'local': 'Arena', **extra}
        return Partida.objects.create(grupo=self.grupo, criada_por=self.org, **dados)

    def confirmar(self, partida, membros):
        inicio = timezone.now() - timedelta(hours=1)  # todos confirmaram antes de "agora"
        for i, m in enumerate(membros):
            Presenca.objects.create(partida=partida, membro=m, status='vou', confirmada_em=inicio + timedelta(seconds=i))


class PartidaAPITests(BaseAPITest):
    def test_organizador_cria_partida(self):
        url = f'/api/grupos/{self.grupo.id}/partidas/'
        dados = {'data_hora': (timezone.now() + timedelta(days=1)).isoformat(), 'local': ' Arena ', 'jogadores_por_time': 6}
        r = self.cliente(self.org).post(url, dados, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data['local'], 'Arena')
        self.assertEqual(r.data['vagas'], 12)
        self.assertEqual(r.data['status'], 'aberta')

    def test_jogador_nao_cria_e_de_fora_nem_ve(self):
        url = f'/api/grupos/{self.grupo.id}/partidas/'
        dados = {'data_hora': (timezone.now() + timedelta(days=1)).isoformat(), 'local': 'Arena'}
        self.assertEqual(self.cliente(self.jogador).post(url, dados, format='json').status_code, 403)
        self.assertEqual(self.cliente(self.de_fora).get(url).status_code, 404)
        partida = self.criar_partida()
        self.assertEqual(self.cliente(self.de_fora).get(f'/api/partidas/{partida.id}/').status_code, 404)

    def test_nao_cria_partida_no_passado(self):
        url = f'/api/grupos/{self.grupo.id}/partidas/'
        dados = {'data_hora': (timezone.now() - timedelta(hours=1)).isoformat(), 'local': 'Arena'}
        r = self.cliente(self.org).post(url, dados, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('data_hora', r.data)

    def test_lista_mostra_total_e_minha_presenca(self):
        partida = self.criar_partida()
        self.confirmar(partida, self.membros[:3])
        r = self.cliente(self.jogador).get(f'/api/grupos/{self.grupo.id}/partidas/')
        self.assertEqual(r.data[0]['total_confirmados'], 3)
        self.assertEqual(r.data[0]['minha_presenca'], 'vou')


class PresencaAPITests(BaseAPITest):
    def test_confirmar_e_cancelar(self):
        partida = self.criar_partida()
        c = self.cliente(self.jogador)
        r = c.post(f'/api/partidas/{partida.id}/presenca/', {'vou': True}, format='json')
        self.assertEqual(r.data['minha_presenca'], 'vou')
        self.assertEqual(r.data['total_confirmados'], 1)
        r = c.post(f'/api/partidas/{partida.id}/presenca/', {'vou': False}, format='json')
        self.assertEqual(r.data['minha_presenca'], 'nao_vou')
        self.assertEqual(r.data['total_confirmados'], 0)
        self.assertEqual(len(r.data['nao_vao']), 1)

    def test_quem_passa_das_vagas_vai_para_a_espera(self):
        partida = self.criar_partida(jogadores_por_time=2)  # 4 vagas
        self.confirmar(partida, self.membros[:6])
        r = self.cliente(self.jogador).get(f'/api/partidas/{partida.id}/')
        self.assertEqual(len(r.data['confirmados']), 4)
        self.assertEqual([j['membro_id'] for j in r.data['lista_espera']], [self.membros[4].id, self.membros[5].id])

    def test_quem_cancela_e_volta_vai_pro_fim_da_fila(self):
        partida = self.criar_partida(jogadores_por_time=2)
        self.confirmar(partida, self.membros[:4])
        c = self.cliente(self.jogador)  # membros[1]
        c.post(f'/api/partidas/{partida.id}/presenca/', {'vou': False}, format='json')
        r = c.post(f'/api/partidas/{partida.id}/presenca/', {'vou': True}, format='json')
        self.assertEqual(r.data['confirmados'][-1]['membro_id'], self.membros[1].id)

    def test_presenca_fechada_depois_dos_times(self):
        partida = self.criar_partida(status=Partida.Status.PUBLICADA)
        r = self.cliente(self.jogador).post(f'/api/partidas/{partida.id}/presenca/', {'vou': True}, format='json')
        self.assertEqual(r.status_code, 400)


def ia_que_acerta(prompt, **kwargs):
    """Simula o Gemini respondendo times validos (usa o proprio algoritmo para montar)."""
    jogadores = []
    for linha in prompt.splitlines():
        if linha.startswith('- id '):
            partes = [p.strip() for p in linha[2:].split('|')]
            jogadores.append(Jogador(int(partes[0][3:]), partes[1], partes[2], int(partes[3][5:])))
    times = equilibrio.montar_por_algoritmo(jogadores, 2)
    return {
        'times': [{'nome': 'Verde', 'jogadores': times[0]}, {'nome': 'Preto', 'jogadores': times[1]}],
        'explicacao': 'Separei os goleiros e equilibrei o ataque.',
    }


class SorteioAPITests(BaseAPITest):
    def setUp(self):
        super().setUp()
        self.partida = self.criar_partida()
        self.confirmar(self.partida, self.membros)
        self.url = f'/api/partidas/{self.partida.id}'

    @patch('ia.gemini.gerar_json', side_effect=ia_que_acerta)
    def test_ia_monta_rascunho_que_so_o_organizador_ve(self, mock_ia):
        r = self.cliente(self.org).post(f'{self.url}/montar-times/')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['status'], 'rascunho')
        self.assertEqual(r.data['origem_times'], 'ia')
        self.assertEqual(len(r.data['times']), 2)
        self.assertIn('nota', r.data['times'][0]['jogadores'][0])  # organizador ve notas
        self.assertEqual(mock_ia.call_count, 1)

        r = self.cliente(self.jogador).get(f'{self.url}/')
        self.assertEqual(r.data['times'], [])
        self.assertEqual(r.data['explicacao_ia'], '')

        self.cliente(self.org).post(f'{self.url}/confirmar-times/')
        r = self.cliente(self.jogador).get(f'{self.url}/')
        self.assertEqual(r.data['status'], 'publicada')
        self.assertEqual(len(r.data['times']), 2)
        self.assertNotIn('nota', r.data['times'][0]['jogadores'][0])  # jogador nao ve notas
        self.assertIn('goleiros', r.data['explicacao_ia'])

    @patch('ia.gemini.gerar_json')
    def test_resposta_errada_volta_para_ia_com_os_erros(self, mock_ia):
        ids = [m.id for m in self.membros]
        errada = {'times': [{'nome': 'Verde', 'jogadores': ids[:4]}, {'nome': 'Preto', 'jogadores': ids[4:]}],
                  'explicacao': 'x'}
        mock_ia.side_effect = [errada, ia_que_acerta(mock_prompt(self))]
        r = self.cliente(self.org).post(f'{self.url}/montar-times/')
        self.assertEqual(r.data['origem_times'], 'ia')
        self.assertEqual(mock_ia.call_count, 2)
        segundo_prompt = mock_ia.call_args_list[1].args[0]
        self.assertIn('recusada pela validacao', segundo_prompt)
        self.assertIn('[4, 6]', segundo_prompt)

    @patch('ia.gemini.gerar_json')
    def test_ia_erra_duas_vezes_usa_plano_b(self, mock_ia):
        mock_ia.return_value = {'times': [{'nome': 'Verde', 'jogadores': [1]}], 'explicacao': 'x'}
        r = self.cliente(self.org).post(f'{self.url}/montar-times/')
        self.assertEqual(r.data['origem_times'], 'reserva')
        self.assertIn('plano B', r.data['explicacao_ia'])
        self.assertLessEqual(r.data['diferenca_forca'], equilibrio.LIMITE_DIFERENCA)

    @patch('ia.gemini.gerar_json', side_effect=IAIndisponivel('sem rede'))
    def test_ia_fora_do_ar_usa_plano_b_sem_insistir(self, mock_ia):
        r = self.cliente(self.org).post(f'{self.url}/montar-times/')
        self.assertEqual(r.data['origem_times'], 'reserva')
        self.assertEqual(mock_ia.call_count, 1)

    @override_settings(GEMINI_API_KEY='')
    def test_sem_chave_funciona_com_plano_b(self):
        r = self.cliente(self.org).post(f'{self.url}/montar-times/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['origem_times'], 'reserva')

    def test_jogador_nao_monta_times(self):
        self.assertEqual(self.cliente(self.jogador).post(f'{self.url}/montar-times/').status_code, 403)

    @patch('ia.gemini.gerar_json', side_effect=ia_que_acerta)
    def test_poucos_confirmados(self, _):
        outra = self.criar_partida()
        self.confirmar(outra, self.membros[:3])
        r = self.cliente(self.org).post(f'/api/partidas/{outra.id}/montar-times/')
        self.assertEqual(r.status_code, 400)
        self.assertIn('pelo menos 4', r.data['detail'])

    @patch('ia.gemini.gerar_json', side_effect=ia_que_acerta)
    def test_sortear_de_novo_manda_os_times_anteriores(self, mock_ia):
        c = self.cliente(self.org)
        c.post(f'{self.url}/montar-times/')
        c.post(f'{self.url}/montar-times/')
        self.assertIn('NOVO sorteio', mock_ia.call_args_list[1].args[0])

    @patch('ia.gemini.gerar_json', side_effect=ia_que_acerta)
    def test_trocar_jogadores_recalcula_forca(self, _):
        c = self.cliente(self.org)
        r = c.post(f'{self.url}/montar-times/')
        verde, preto = r.data['times']
        a = next(j for j in verde['jogadores'] if j['posicao'] != 'GOL')
        b = next(j for j in preto['jogadores'] if j['posicao'] != 'GOL' and j['nota'] != a['nota'])
        r = c.post(f'{self.url}/trocar/', {'jogador_a': a['membro_id'], 'jogador_b': b['membro_id']}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        novo_verde = {j['membro_id'] for j in r.data['times'][0]['jogadores']}
        self.assertIn(b['membro_id'], novo_verde)
        self.assertNotIn(a['membro_id'], novo_verde)
        self.assertNotEqual(r.data['times'][0]['forca'], verde['forca'])
        self.assertTrue(r.data['ajustado_pelo_organizador'])

        mesmo_time = [j['membro_id'] for j in r.data['times'][0]['jogadores'][:2]]
        r = c.post(f'{self.url}/trocar/', dict(zip(['jogador_a', 'jogador_b'], mesmo_time)), format='json')
        self.assertEqual(r.status_code, 400)

    @patch('ia.gemini.gerar_json', side_effect=ia_que_acerta)
    def test_montagem_automatica_quando_chega_a_hora(self, mock_ia):
        # jogo daqui a 1h, IA monta 2h antes -> ja passou da hora
        Partida.objects.filter(pk=self.partida.pk).update(data_hora=timezone.now() + timedelta(hours=1))
        r = self.cliente(self.jogador).get(f'{self.url}/')
        self.assertEqual(r.data['status'], 'publicada')
        self.assertEqual(len(r.data['times']), 2)
        # abrir de novo nao chama a IA de novo
        self.cliente(self.jogador).get(f'{self.url}/')
        self.assertEqual(mock_ia.call_count, 1)

    @patch('ia.gemini.gerar_json', side_effect=ia_que_acerta)
    def test_antes_da_hora_nao_monta(self, mock_ia):
        r = self.cliente(self.jogador).get(f'{self.url}/')
        self.assertEqual(r.data['status'], 'aberta')
        mock_ia.assert_not_called()


def mock_prompt(teste):
    """Prompt equivalente ao que o sorteio monta, para gerar a resposta certa no mock."""
    linhas = [f'- id {m.id} | {m.usuario.nome} | {m.posicao} | nota {m.nota}' for m in teste.membros]
    return '\n'.join(linhas)
