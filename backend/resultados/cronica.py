"""
Liga o placar salvo (Resultado/Gol) a cronica escrita pela IA (ia.cronica), #40.

O PUT do resultado so salva o placar. A tela chama depois
POST /api/partidas/{id}/resultado/cronica/, que usa gerar_e_salvar() abaixo.
Se a IA falhar, o placar ja esta salvo e a cronica fica com status 'erro' e o
artilheiro como craque.
"""

import logging

from django.utils import timezone

from ia import cronica as ia_cronica
from ia import gemini

from .models import Cronica

log = logging.getLogger(__name__)

MSG_IA_FORA = 'A IA não respondeu agora. Tente gerar a crônica de novo daqui a alguns minutos.'
MSG_RESPOSTA_INVALIDA = 'A IA respondeu num formato inesperado. Tente gerar a crônica de novo.'
MSG_DADOS = 'Não foi possível montar a crônica com os dados desta partida.'


class CronicaMantida(Exception):
    """A IA falhou, mas ja havia uma cronica boa e atualizada, que foi mantida."""

    def __init__(self, mensagem, cronica):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.cronica = cronica


def dados_da_partida(resultado):
    """Monta o dict que ia.cronica espera a partir do placar salvo."""
    partida = resultado.partida
    gols_por_time = {}
    gols_por_jogador = {}
    for gol in resultado.gols.all():
        gols_por_time[gol.time_id] = gols_por_time.get(gol.time_id, 0) + gol.quantidade
        if gol.jogador_id:
            gols_por_jogador[gol.jogador_id] = gols_por_jogador.get(gol.jogador_id, 0) + gol.quantidade

    times = []
    for time in partida.times.prefetch_related('jogadores__usuario'):
        times.append({
            'nome': time.nome,
            'gols': gols_por_time.get(time.id, 0),
            'jogadores': [
                {
                    'id': membro.id,
                    'nome': membro.usuario.nome,
                    'posicao': membro.posicao,
                    'gols': gols_por_jogador.get(membro.id, 0),
                }
                for membro in time.jogadores.all()
            ],
        })

    return {
        'grupo': partida.grupo.nome,
        'data': timezone.localtime(partida.data_hora).strftime('%Y-%m-%dT%H:%M'),  # com a hora (manha/tarde/noite)
        'local': partida.local,
        'times': times,
    }


def _craque_padrao_seguro(dados):
    try:
        return ia_cronica.craque_padrao(dados)
    except (KeyError, TypeError, ValueError):
        return None


def gerar_e_salvar(resultado):
    """
    Pede a cronica a IA e salva. Devolve a Cronica (status 'ok' ou 'erro').

    Se a IA falhar e ja existir uma cronica boa e atualizada, ela e mantida e
    levanta CronicaMantida (a tela avisa, sem perder o texto que ja tinha).
    """
    baseada_em = resultado.registrado_em
    dados = dados_da_partida(resultado)

    try:
        gerada = ia_cronica.gerar_cronica(dados)
    except (gemini.IAIndisponivel, gemini.RespostaInvalida, ValueError) as erro:
        if isinstance(erro, gemini.IAIndisponivel):
            mensagem = MSG_IA_FORA
        elif isinstance(erro, gemini.RespostaInvalida):
            mensagem = MSG_RESPOSTA_INVALIDA
        else:  # dados que nao passam em ia.cronica.validar_dados (ex.: time sem jogador)
            mensagem = MSG_DADOS
        log.warning('Crônica da partida %s falhou: %s', resultado.partida_id, erro)

        anterior = Cronica.objects.filter(resultado=resultado).first()
        if anterior and anterior.status == Cronica.Status.OK and not anterior.desatualizada:
            raise CronicaMantida(mensagem, anterior) from erro

        craque = _craque_padrao_seguro(dados)
        valores = {
            'status': Cronica.Status.ERRO,
            'titulo': '',
            'texto': '',
            'craque_id': craque['id'] if craque else None,
            'motivo_craque': craque['motivo'] if craque else '',
            'origem_craque': Cronica.OrigemCraque.ARTILHEIRO if craque else '',
            'erro': mensagem,
        }
    else:
        craque = gerada['craque']
        valores = {
            'status': Cronica.Status.OK,
            'titulo': gerada['titulo'],
            'texto': gerada['texto'],
            'craque_id': craque['id'] if craque else None,
            'motivo_craque': craque['motivo'] if craque else '',
            'origem_craque': gerada['origem_craque'] if craque else '',
            'erro': '',
        }

    cronica, _ = Cronica.objects.update_or_create(
        resultado=resultado,
        defaults={**valores, 'gerada_em': timezone.now(), 'baseada_em': baseada_em},
    )
    return cronica
