from rest_framework.test import APITestCase

from contas.models import Usuario

from .models import Grupo, Membro


class GruposTests(APITestCase):
    def setUp(self):
        self.ana = Usuario.objects.create_user('ana@teste.com', 'chuteira123', nome='Ana', posicao='GOL')
        self.bia = Usuario.objects.create_user('bia@teste.com', 'chuteira123', nome='Bia', posicao='ZAG')

    def test_criar_grupo_vira_organizador(self):
        self.client.force_authenticate(self.ana)
        r = self.client.post('/api/grupos/', {'nome': 'Pelada de quinta'}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertRegex(r.data['codigo_convite'], r'^RACHA-[A-Z2-9]{3}$')
        self.assertEqual(r.data['total_membros'], 1)
        self.assertEqual(r.data['meu_papel'], 'organizador')
        membro = Membro.objects.get(grupo_id=r.data['id'], usuario=self.ana)
        self.assertEqual(membro.posicao, 'GOL')

    def test_nome_curto(self):
        self.client.force_authenticate(self.ana)
        r = self.client.post('/api/grupos/', {'nome': ' a '}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_entrar_com_codigo_e_listar(self):
        grupo = Grupo.objects.create(nome='Futsal', criado_por=self.ana)
        Membro.objects.create(grupo=grupo, usuario=self.ana, papel='organizador')

        self.client.force_authenticate(self.bia)
        self.assertEqual(self.client.get('/api/grupos/').data, [])

        codigo_sem_prefixo = grupo.codigo_convite.split('-')[1].lower()
        r = self.client.post('/api/grupos/entrar/', {'codigo': codigo_sem_prefixo}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data['meu_papel'], 'jogador')
        self.assertEqual(r.data['total_membros'], 2)

        # entrar de novo nao duplica
        r = self.client.post('/api/grupos/entrar/', {'codigo': grupo.codigo_convite}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(grupo.membros.count(), 2)

        lista = self.client.get('/api/grupos/')
        self.assertEqual(len(lista.data), 1)

        membros = self.client.get(f'/api/grupos/{grupo.id}/membros/')
        self.assertEqual([m['nome'] for m in membros.data], ['Ana', 'Bia'])

    def test_codigo_invalido(self):
        self.client.force_authenticate(self.bia)
        r = self.client.post('/api/grupos/entrar/', {'codigo': 'RACHA-ZZZ'}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_nao_membro_nao_ve_grupo(self):
        grupo = Grupo.objects.create(nome='Futsal', criado_por=self.ana)
        Membro.objects.create(grupo=grupo, usuario=self.ana, papel='organizador')
        self.client.force_authenticate(self.bia)
        self.assertEqual(self.client.get(f'/api/grupos/{grupo.id}/').status_code, 404)
        self.assertEqual(self.client.get(f'/api/grupos/{grupo.id}/membros/').status_code, 404)

    def test_exige_login(self):
        self.assertEqual(self.client.get('/api/grupos/').status_code, 401)
