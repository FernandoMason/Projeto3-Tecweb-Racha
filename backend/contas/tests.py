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
