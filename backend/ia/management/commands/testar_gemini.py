"""
Teste manual da IA real (#34): usa a GEMINI_API_KEY do backend/.env.

    python manage.py testar_gemini              # confere a chave e lista os modelos Flash
    python manage.py testar_gemini --cronica    # gera a cronica das partidas de exemplo

A chave nunca e impressa. Cada --cronica gasta 3 chamadas do plano gratuito.
Os testes automaticos (manage.py test) nunca chamam a IA de verdade; este comando sim.
"""

import json
import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from ia import gemini
from ia.cronica import craque_padrao, gerar_cronica
from ia.exemplos import TODOS


class Command(BaseCommand):
    help = 'Testa a chave do Gemini e o prompt da crônica com a IA real.'

    def add_arguments(self, parser):
        parser.add_argument('--cronica', action='store_true', help='gera a crônica das partidas de exemplo')

    def handle(self, *args, **opcoes):
        try:
            if opcoes['cronica']:
                self.testar_cronicas()
            else:
                self.conferir_chave()
        except gemini.IAIndisponivel as erro:
            raise CommandError(f'IA indisponível: {erro}') from erro

    def conferir_chave(self):
        self.stdout.write(f'Modelo configurado: {settings.GEMINI_MODEL}')
        inicio = time.perf_counter()
        resposta = gemini.gerar_json(
            'Responda {"ok": true, "frase": "<uma frase curta de narrador de futebol>"}',
            json_schema={
                'type': 'object',
                'properties': {'ok': {'type': 'boolean'}, 'frase': {'type': 'string'}},
                'required': ['ok', 'frase'],
            },
        )
        self.stdout.write(self.style.SUCCESS(f'Chave OK em {time.perf_counter() - inicio:.1f}s: {resposta}'))

        modelos = [m.name for m in gemini._cliente_gemini().models.list() if 'flash' in (m.name or '')]
        self.stdout.write('Modelos Flash disponíveis para esta chave:')
        for nome in sorted(modelos):
            self.stdout.write(f'  {nome}')

    def testar_cronicas(self):
        for nome, dados in TODOS.items():
            self.stdout.write(f'\n=== {nome} ===')
            inicio = time.perf_counter()
            try:
                cronica = gerar_cronica(dados)
            except (gemini.IAIndisponivel, gemini.RespostaInvalida) as erro:
                self.stdout.write(self.style.WARNING(f'IA falhou: {erro}'))
                self.stdout.write(f'Craque padrão: {craque_padrao(dados)}')
                continue
            self.stdout.write(f'({time.perf_counter() - inicio:.1f}s)')
            self.stdout.write(json.dumps(cronica, ensure_ascii=False, indent=2))
