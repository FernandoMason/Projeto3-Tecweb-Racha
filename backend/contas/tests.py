from rest_framework.test import APITestCase

from .models import Usuario


class AuthTests(APITestCase):
    def cadastrar(self, **extra):
        dados = {'nome': 'Joao', 'email': 'Joao@Teste.com', 'senha': 'chuteira123', 'posicao': 'ATA'}
        dados.update(extra)
        return self.client.post('/api/auth/cadastro/', dados, format='json')

    def test_cadastro_cria_usuario_e_devolve_tokens(self):
        r = self.cadastrar()
        self.assertEqual(r.status_code, 201, r.data)
        self.assertIn('access', r.data)
        self.assertIn('refresh', r.data)
        self.assertEqual(r.data['usuario']['email'], 'joao@teste.com')
        self.assertEqual(r.data['usuario']['posicao'], 'ATA')
        self.assertTrue(Usuario.objects.get(email='joao@teste.com').check_password('chuteira123'))

    def test_cadastro_email_repetido(self):
        self.cadastrar()
        r = self.cadastrar(email='joao@teste.com')
        self.assertEqual(r.status_code, 400)
        self.assertIn('email', r.data)

    def test_cadastro_senha_fraca(self):
        r = self.cadastrar(senha='12345678')
        self.assertEqual(r.status_code, 400)

    def test_login_refresh_e_me(self):
        self.cadastrar()
        r = self.client.post('/api/auth/login/', {'email': 'JOAO@teste.com', 'password': 'chuteira123'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['usuario']['nome'], 'Joao')

        r2 = self.client.post('/api/auth/refresh/', {'refresh': r.data['refresh']}, format='json')
        self.assertEqual(r2.status_code, 200)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")
        me = self.client.get('/api/auth/me/')
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.data['email'], 'joao@teste.com')

    def test_login_senha_errada(self):
        self.cadastrar()
        r = self.client.post('/api/auth/login/', {'email': 'joao@teste.com', 'password': 'errada999'}, format='json')
        self.assertEqual(r.status_code, 401)

    def test_me_sem_token(self):
        self.assertEqual(self.client.get('/api/auth/me/').status_code, 401)

    def test_cadastro_email_repetido_com_maiusculas(self):
        self.cadastrar()
        r = self.cadastrar(email='JOAO@TESTE.COM')
        self.assertEqual(r.status_code, 400)
        self.assertEqual(Usuario.objects.count(), 1)

    def test_cadastro_campos_obrigatorios_e_posicao_invalida(self):
        r = self.client.post('/api/auth/cadastro/', {}, format='json')
        self.assertEqual(r.status_code, 400)
        for campo in ('nome', 'email', 'senha'):
            self.assertIn(campo, r.data)
        r = self.cadastrar(posicao='PIV')
        self.assertEqual(r.status_code, 400)
        self.assertIn('posicao', r.data)

    def test_cadastro_senha_parecida_com_o_email(self):
        r = self.cadastrar(email='chuteira123@teste.com', senha='chuteira123')
        self.assertEqual(r.status_code, 400)

    def test_cadastro_nao_devolve_senha(self):
        r = self.cadastrar()
        self.assertNotIn('senha', r.data['usuario'])
        self.assertNotIn('password', r.data['usuario'])

    def test_me_patch_muda_nome_e_posicao_mas_nao_o_email(self):
        self.cadastrar()
        usuario = Usuario.objects.get()
        self.client.force_authenticate(usuario)
        r = self.client.patch(
            '/api/auth/me/', {'nome': 'João', 'posicao': 'GOL', 'email': 'outro@teste.com'}, format='json'
        )
        self.assertEqual(r.status_code, 200, r.data)
        usuario.refresh_from_db()
        self.assertEqual((usuario.nome, usuario.posicao, usuario.email), ('João', 'GOL', 'joao@teste.com'))

    def test_refresh_invalido(self):
        r = self.client.post('/api/auth/refresh/', {'refresh': 'nao-e-um-token'}, format='json')
        self.assertEqual(r.status_code, 401)

    def test_saude_responde_sem_login(self):
        # health check do deploy (#17)
        r = self.client.get('/api/saude/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {'ok': True})

    def test_token_invalido_e_recusado(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer nao-e-um-token')
        self.assertEqual(self.client.get('/api/auth/me/').status_code, 401)
