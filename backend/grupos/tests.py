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


class GestaoMembrosTests(APITestCase):
    """#16: organizador edita posicao e nota; a nota so aparece para ele."""

    def setUp(self):
        self.org = Usuario.objects.create_user('org@teste.com', 'chuteira123', nome='Org', posicao='ATA')
        self.joga = Usuario.objects.create_user('joga@teste.com', 'chuteira123', nome='Joga', posicao='MEI')
        self.fora = Usuario.objects.create_user('fora@teste.com', 'chuteira123', nome='Fora', posicao='ZAG')
        self.grupo = Grupo.objects.create(nome='Pelada', criado_por=self.org)
        self.m_org = Membro.objects.create(grupo=self.grupo, usuario=self.org, papel='organizador', nota=8)
        self.m_joga = Membro.objects.create(grupo=self.grupo, usuario=self.joga, posicao='MEI', nota=5)
        self.url = f'/api/grupos/{self.grupo.id}/membros/{self.m_joga.id}/'

    def membros(self, usuario):
        self.client.force_authenticate(usuario)
        return self.client.get(f'/api/grupos/{self.grupo.id}/membros/')

    def test_nota_so_aparece_para_o_organizador(self):
        r = self.membros(self.org)
        self.assertEqual([m['nota'] for m in r.data], [8, 5])
        r = self.membros(self.joga)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(all('nota' not in m for m in r.data))

    def test_membros_nao_expoe_email(self):
        r = self.membros(self.org)
        self.assertTrue(all('email' not in m for m in r.data))

    def test_organizador_edita_posicao_e_nota(self):
        self.client.force_authenticate(self.org)
        r = self.client.patch(self.url, {'posicao': 'GOL', 'nota': 9}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual((r.data['posicao'], r.data['nota']), ('GOL', 9))
        self.m_joga.refresh_from_db()
        self.assertEqual((self.m_joga.posicao, self.m_joga.nota), ('GOL', 9))
        # a posicao no grupo nao muda a posicao preferida da conta
        self.joga.refresh_from_db()
        self.assertEqual(self.joga.posicao, 'MEI')

    def test_edicao_parcial(self):
        self.client.force_authenticate(self.org)
        r = self.client.patch(self.url, {'nota': 2}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.m_joga.refresh_from_db()
        self.assertEqual((self.m_joga.posicao, self.m_joga.nota), ('MEI', 2))

    def test_organizador_edita_a_propria_nota(self):
        self.client.force_authenticate(self.org)
        url = f'/api/grupos/{self.grupo.id}/membros/{self.m_org.id}/'
        self.assertEqual(self.client.patch(url, {'nota': 10}, format='json').status_code, 200)

    def test_papel_nao_pode_ser_alterado(self):
        self.client.force_authenticate(self.org)
        r = self.client.patch(self.url, {'papel': 'organizador', 'nota': 6}, format='json')
        self.assertEqual(r.status_code, 200)
        self.m_joga.refresh_from_db()
        self.assertEqual(self.m_joga.papel, 'jogador')

    def test_validacao(self):
        self.client.force_authenticate(self.org)
        for corpo in ({'nota': 0}, {'nota': 11}, {'nota': 'dez'}, {'posicao': 'PIV'}, {}):
            r = self.client.patch(self.url, corpo, format='json')
            self.assertEqual(r.status_code, 400, corpo)
        self.m_joga.refresh_from_db()
        self.assertEqual((self.m_joga.posicao, self.m_joga.nota), ('MEI', 5))

    def test_jogador_nao_edita(self):
        self.client.force_authenticate(self.joga)
        r = self.client.patch(self.url, {'nota': 10}, format='json')
        self.assertEqual(r.status_code, 403)
        self.assertIn('organizador', r.data['detail'])
        self.m_joga.refresh_from_db()
        self.assertEqual(self.m_joga.nota, 5)

    def test_quem_nao_e_do_grupo_recebe_404(self):
        self.client.force_authenticate(self.fora)
        self.assertEqual(self.client.patch(self.url, {'nota': 10}, format='json').status_code, 404)

    def test_membro_de_outro_grupo_recebe_404(self):
        outro = Grupo.objects.create(nome='Outro', criado_por=self.fora)
        m_fora = Membro.objects.create(grupo=outro, usuario=self.fora, papel='organizador')
        self.client.force_authenticate(self.org)
        r = self.client.patch(f'/api/grupos/{self.grupo.id}/membros/{m_fora.id}/', {'nota': 1}, format='json')
        self.assertEqual(r.status_code, 404)
        m_fora.refresh_from_db()
        self.assertEqual(m_fora.nota, 5)

    def test_exige_login(self):
        self.assertEqual(self.client.patch(self.url, {'nota': 1}, format='json').status_code, 401)


class GruposExtrasTests(APITestCase):
    def setUp(self):
        self.ana = Usuario.objects.create_user('ana@teste.com', 'chuteira123', nome='Ana', posicao='GOL')

    def test_entrar_aceita_espacos_e_usa_posicao_da_conta(self):
        dono = Usuario.objects.create_user('dono@teste.com', 'chuteira123', nome='Dono')
        grupo = Grupo.objects.create(nome='Society', criado_por=dono)
        Membro.objects.create(grupo=grupo, usuario=dono, papel='organizador')
        self.client.force_authenticate(self.ana)
        codigo = '  ' + grupo.codigo_convite.lower() + '  '
        r = self.client.post('/api/grupos/entrar/', {'codigo': codigo}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(Membro.objects.get(grupo=grupo, usuario=self.ana).posicao, 'GOL')

    def test_lista_mais_novo_primeiro_com_total_certo(self):
        self.client.force_authenticate(self.ana)
        a = self.client.post('/api/grupos/', {'nome': 'Primeiro'}, format='json').data
        b = self.client.post('/api/grupos/', {'nome': 'Segundo'}, format='json').data
        outro = Usuario.objects.create_user('beto@teste.com', 'chuteira123', nome='Beto')
        Membro.objects.create(grupo_id=a['id'], usuario=outro)
        lista = self.client.get('/api/grupos/').data
        self.assertEqual([g['id'] for g in lista], [b['id'], a['id']])
        self.assertEqual([g['total_membros'] for g in lista], [1, 2])

    def test_codigo_convite_nao_editavel_e_unico(self):
        self.client.force_authenticate(self.ana)
        r = self.client.post('/api/grupos/', {'nome': 'Pelada', 'codigo_convite': 'RACHA-AAA'}, format='json')
        self.assertEqual(r.status_code, 201)
        self.assertNotEqual(r.data['codigo_convite'], 'RACHA-AAA')
        codigos = {Grupo.objects.create(nome=f'G{i}', criado_por=self.ana).codigo_convite for i in range(30)}
        self.assertEqual(len(codigos), 30)

    def test_grupo_nao_tem_update_nem_delete(self):
        self.client.force_authenticate(self.ana)
        gid = self.client.post('/api/grupos/', {'nome': 'Pelada'}, format='json').data['id']
        self.assertEqual(self.client.delete(f'/api/grupos/{gid}/').status_code, 405)
        self.assertEqual(self.client.put(f'/api/grupos/{gid}/', {'nome': 'X'}, format='json').status_code, 405)
