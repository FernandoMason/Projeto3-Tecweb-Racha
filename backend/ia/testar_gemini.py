"""
Teste manual da IA real, sem Django (tarefa #34).

    cd backend
    python -m ia.testar_gemini              # confere a chave e lista os modelos Flash
    python -m ia.testar_gemini --cronica    # gera a cronica das partidas de exemplo

Le GEMINI_API_KEY (e GEMINI_MODEL, opcional) do backend/.env. A chave nunca e impressa.
Cada --cronica gasta 3 chamadas do plano gratuito.
"""

import argparse
import json
import sys
import time
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # sem python-dotenv: usa so as variaveis ja exportadas
    load_dotenv = None

if load_dotenv:
    load_dotenv(Path(__file__).resolve().parent.parent / '.env')

from .cliente import ErroIA, gerar_json, modelo_configurado, obter_cliente  # noqa: E402
from .cronica import craque_padrao, gerar_cronica  # noqa: E402
from .exemplos import TODOS  # noqa: E402


def conferir_chave():
    print(f'Modelo configurado: {modelo_configurado()}')
    inicio = time.perf_counter()
    resposta = gerar_json(
        'Responda {"ok": true, "frase": "<uma frase curta de narrador de futebol>"}',
        schema={
            'type': 'object',
            'properties': {'ok': {'type': 'boolean'}, 'frase': {'type': 'string'}},
            'required': ['ok', 'frase'],
        },
    )
    print(f'Chave OK em {time.perf_counter() - inicio:.1f}s: {resposta}')

    modelos = [m.name for m in obter_cliente().models.list() if 'flash' in (m.name or '')]
    print('Modelos Flash disponíveis para esta chave:')
    for nome in sorted(modelos):
        print(f'  {nome}')


def testar_cronicas():
    for nome, dados in TODOS.items():
        print(f'\n=== {nome} ===')
        inicio = time.perf_counter()
        try:
            cronica = gerar_cronica(dados)
        except ErroIA as erro:
            print(f'IA falhou ({erro.codigo}): {erro.mensagem}  [{erro.detalhe}]')
            print(f'Craque padrão: {craque_padrao(dados)}')
            continue
        print(f'({time.perf_counter() - inicio:.1f}s)')
        print(json.dumps(cronica, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description='Testa a chave e os prompts do Gemini.')
    parser.add_argument('--cronica', action='store_true', help='gera a crônica das partidas de exemplo')
    args = parser.parse_args()
    try:
        if args.cronica:
            testar_cronicas()
        else:
            conferir_chave()
    except ErroIA as erro:
        print(f'Falhou ({erro.codigo}): {erro.mensagem}\n  detalhe: {erro.detalhe}')
        sys.exit(1)


if __name__ == '__main__':
    main()
