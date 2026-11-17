"""
Cliente do Gemini (#34 e #35), usado pelo sorteio de times e pela cronica.

Toda conversa com a IA passa por aqui. Assim:
- chave e modelo sao lidos de um lugar so (settings, que le o .env);
- qualquer falha (sem chave, sem internet, cota estourada, resposta vazia)
  vira `IAIndisponivel`, e quem chama decide o plano B;
- nos testes basta trocar `gerar_json`/`gerar_texto` por um mock, sem rede.
"""

import json
import logging

from django.conf import settings

log = logging.getLogger(__name__)


class IAIndisponivel(Exception):
    """A IA nao respondeu: sem chave, sem internet, cota estourada etc."""


class RespostaInvalida(Exception):
    """A IA respondeu, mas o texto nao e o JSON que pedimos."""


_cliente = None


def _cliente_gemini():
    global _cliente
    if not settings.GEMINI_API_KEY:
        raise IAIndisponivel('GEMINI_API_KEY nao configurada no .env.')
    if _cliente is None:
        # import aqui dentro: o backend sobe (e os testes rodam) mesmo sem o pacote
        from google import genai
        from google.genai import types

        _cliente = genai.Client(
            api_key=settings.GEMINI_API_KEY,
            http_options=types.HttpOptions(timeout=settings.GEMINI_TIMEOUT_MS),
        )
    return _cliente


def gerar_texto(prompt, *, instrucoes='', temperatura=0.8, json_schema=None):
    """Manda o prompt e devolve o texto da resposta."""
    from google.genai import types

    cliente = _cliente_gemini()
    config = types.GenerateContentConfig(
        system_instruction=instrucoes or None,
        temperature=temperatura,
    )
    if json_schema:
        # "modo JSON": o Gemini e obrigado a responder no formato do schema
        config.response_mime_type = 'application/json'
        config.response_json_schema = json_schema

    try:
        resposta = cliente.models.generate_content(
            model=settings.GEMINI_MODEL, contents=prompt, config=config
        )
    except Exception as erro:  # rede, cota (429), chave invalida...
        log.warning('Gemini falhou: %s', erro)
        raise IAIndisponivel(f'Falha ao chamar o Gemini: {erro}') from erro

    texto = (resposta.text or '').strip()
    if not texto:
        raise IAIndisponivel('O Gemini devolveu uma resposta vazia.')
    return texto


def gerar_json(prompt, *, json_schema, instrucoes='', temperatura=0.8):
    """Igual a `gerar_texto`, mas ja devolve o JSON convertido em dict."""
    texto = gerar_texto(prompt, instrucoes=instrucoes, temperatura=temperatura, json_schema=json_schema)
    try:
        return json.loads(texto)
    except json.JSONDecodeError as erro:
        log.warning('Gemini devolveu JSON invalido: %r', texto[:300])
        raise RespostaInvalida('A IA devolveu um JSON invalido.') from erro
