"""
Cliente do Gemini usado pelo backend do Racha.

A chamada a IA acontece sempre aqui no servidor: a chave fica na variavel de
ambiente GEMINI_API_KEY (arquivo backend/.env) e nunca chega ao React.

Uso:
    from ia.cliente import ErroIA, gerar_json

    try:
        dados = gerar_json(prompt, schema=MEU_SCHEMA, instrucao='Voce e ...')
    except ErroIA as erro:
        # erro.mensagem pode ir direto para a tela; erro.status_http para a resposta da API
        ...
"""

import importlib
import json
import logging
import os

from google import genai
from google.genai import errors, types

logger = logging.getLogger('racha.ia')


def _erros_de_rede():
    """Timeout/sem conexao. O SDK 3.x usa httpx2 (e httpx, se estiver instalado)."""
    encontrados = []
    for modulo, nome in (('httpx2', 'HTTPError'), ('httpx', 'HTTPError'), ('requests', 'RequestException')):
        try:
            encontrados.append(getattr(importlib.import_module(modulo), nome))
        except (ImportError, AttributeError):
            pass
    return tuple(encontrados) or (OSError,)


ERROS_DE_REDE = _erros_de_rede()

# Alias do Google que aponta sempre para o Flash mais novo (tem plano gratuito).
# Para fixar um modelo especifico, defina GEMINI_MODEL no .env.
MODELO_PADRAO = 'gemini-flash-latest'

# Tempo maximo de cada tentativa (ms). A IA demora alguns segundos para escrever a cronica.
TIMEOUT_MS = 30_000

# Repete uma vez so quando o Google esta instavel (5xx). Erro de cota (429) nao e repetido:
# repetir so gastaria mais do limite gratuito e deixaria o usuario esperando.
RETRY = types.HttpRetryOptions(attempts=2, initial_delay=1.0, http_status_codes=[500, 502, 503, 504])

# Motivos de parada que significam "a IA se recusou por seguranca".
PARADAS_BLOQUEIO = {'SAFETY', 'PROHIBITED_CONTENT', 'BLOCKLIST', 'SPII', 'RECITATION'}


class ErroIA(Exception):
    """Falha ao gerar conteudo com a IA. `mensagem` e curta e pode ser mostrada ao usuario."""

    MENSAGENS = {
        'sem_chave': ('A IA não está configurada no servidor.', 503),
        'chave_invalida': ('A chave da IA no servidor é inválida.', 503),
        'cota': ('A IA atingiu o limite de uso gratuito. Tente de novo em alguns minutos.', 429),
        'indisponivel': ('A IA está fora do ar no momento. Tente de novo daqui a pouco.', 503),
        'bloqueado': ('A IA não quis gerar esse conteúdo. Tente escrever de outro jeito.', 422),
        'resposta_invalida': ('A IA respondeu num formato inesperado. Tente de novo.', 502),
        'erro': ('Não foi possível gerar o conteúdo com a IA.', 502),
    }

    def __init__(self, codigo, detalhe=''):
        self.codigo = codigo if codigo in self.MENSAGENS else 'erro'
        self.mensagem, self.status_http = self.MENSAGENS[self.codigo]
        self.detalhe = detalhe  # so para log, nunca vai para a tela
        super().__init__(f'{self.codigo}: {detalhe or self.mensagem}')

    def como_resposta(self):
        """Corpo padrao para a API devolver ao frontend."""
        return {'detail': self.mensagem, 'codigo': self.codigo}


def modelo_configurado():
    return os.getenv('GEMINI_MODEL', '').strip() or MODELO_PADRAO


_cliente = None
_chave_do_cliente = None


def obter_cliente():
    """Cria (uma vez) o cliente do Gemini com a chave do ambiente."""
    global _cliente, _chave_do_cliente
    chave = os.getenv('GEMINI_API_KEY', '').strip()
    if not chave:
        raise ErroIA('sem_chave', 'GEMINI_API_KEY vazia')
    if _cliente is None or chave != _chave_do_cliente:
        _cliente = genai.Client(
            api_key=chave,
            http_options=types.HttpOptions(timeout=TIMEOUT_MS, retry_options=RETRY),
        )
        _chave_do_cliente = chave
    return _cliente


def _traduzir_erro_api(erro):
    """Converte o erro HTTP do Google em um ErroIA com mensagem amigavel."""
    codigo_http = getattr(erro, 'code', None) or 0
    texto = f'{codigo_http} {getattr(erro, "status", "")} {getattr(erro, "message", "")}'
    if codigo_http == 429:
        return ErroIA('cota', texto)
    if codigo_http in (401, 403) or 'API key not valid' in texto or 'API_KEY_INVALID' in texto:
        return ErroIA('chave_invalida', texto)
    if codigo_http >= 500:
        return ErroIA('indisponivel', texto)
    return ErroIA('erro', texto)


def _texto_da_resposta(resposta):
    """Extrai o texto da resposta, tratando bloqueio e corte por tamanho."""
    feedback = getattr(resposta, 'prompt_feedback', None)
    if feedback is not None and getattr(feedback, 'block_reason', None):
        raise ErroIA('bloqueado', f'prompt bloqueado: {feedback.block_reason}')

    candidatos = getattr(resposta, 'candidates', None) or []
    if candidatos:
        motivo = getattr(candidatos[0], 'finish_reason', None)
        nome_motivo = getattr(motivo, 'name', None) or (str(motivo) if motivo else '')
        if nome_motivo in PARADAS_BLOQUEIO:
            raise ErroIA('bloqueado', f'resposta bloqueada: {nome_motivo}')
        if nome_motivo == 'MAX_TOKENS':
            raise ErroIA('resposta_invalida', 'resposta cortada por MAX_TOKENS')

    try:
        texto = resposta.text
    except (ValueError, AttributeError):
        texto = None
    if not texto or not texto.strip():
        raise ErroIA('resposta_invalida', 'resposta vazia')
    return texto


def gerar_json(prompt, *, schema, instrucao=None, temperatura=0.9, modelo=None):
    """
    Pede ao Gemini uma resposta em JSON que siga `schema` (JSON Schema) e devolve o dict.

    Levanta ErroIA em qualquer falha (sem chave, cota, fora do ar, bloqueio, JSON invalido).
    """
    cliente = obter_cliente()
    nome_modelo = modelo or modelo_configurado()
    config = types.GenerateContentConfig(
        system_instruction=instrucao,
        temperature=temperatura,
        response_mime_type='application/json',
        response_json_schema=schema,
    )

    try:
        resposta = cliente.models.generate_content(model=nome_modelo, contents=prompt, config=config)
    except errors.APIError as erro:
        falha = _traduzir_erro_api(erro)
        logger.warning('Gemini (%s) falhou: %s', nome_modelo, falha)
        raise falha from erro
    except ERROS_DE_REDE as erro:  # timeout, sem internet, DNS...
        logger.warning('Gemini (%s) sem resposta: %r', nome_modelo, erro)
        raise ErroIA('indisponivel', repr(erro)) from erro

    texto = _texto_da_resposta(resposta)
    try:
        dados = json.loads(texto)
    except json.JSONDecodeError as erro:
        logger.warning('Gemini (%s) devolveu JSON invalido: %.200s', nome_modelo, texto)
        raise ErroIA('resposta_invalida', 'JSON invalido') from erro
    if not isinstance(dados, dict):
        raise ErroIA('resposta_invalida', f'esperava objeto JSON, veio {type(dados).__name__}')
    return dados
