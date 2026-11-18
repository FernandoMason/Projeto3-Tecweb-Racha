"""
Ranking do grupo (#42): artilharia, vitorias e craques, somando todas as partidas com resultado.

As tres listas seguem a tela 14 do fluxo (abas Artilharia, Vitorias e Craques):
cada item tem colocacao, membro, nome e o numero da aba. So entra quem tem numero > 0.
"""

from django.db.models import F

from .models import Cronica, Resultado


def _ordenar_com_colocacao(itens, chave):
    """
    Ordena por `chave` (maior primeiro; no empate, menos jogos e depois o nome)
    e numera com colocacao compartilhada: 12, 9, 9, 5 -> 1, 2, 2, 4.
    """
    itens = [i for i in itens if i[chave] > 0]
    itens.sort(key=lambda i: (-i[chave], i['jogos'], i['nome'].lower()))
    anterior = None
    for indice, item in enumerate(itens, start=1):
        if item[chave] != anterior:
            colocacao = indice
            anterior = item[chave]
        item['colocacao'] = colocacao
    return [{'colocacao': i.pop('colocacao'), **i} for i in itens]


def calcular_ranking(grupo):
    resultados = (
        Resultado.objects.filter(partida__grupo=grupo)
        .select_related('partida')
        .prefetch_related('gols', 'partida__times__jogadores__usuario')
    )

    stats = {}  # membro_id -> contadores

    def de(membro):
        if membro.id not in stats:
            stats[membro.id] = {
                'membro': membro.id, 'nome': membro.usuario.nome,
                'jogos': 0, 'gols': 0, 'vitorias': 0, 'empates': 0, 'derrotas': 0, 'craque': 0,
            }
        return stats[membro.id]

    total_jogos = 0
    for resultado in resultados:
        total_jogos += 1
        vencedor = resultado.vencedor()
        gols_por_time = {p['time_id']: p['gols'] for p in resultado.placar()}
        maior = max(gols_por_time.values(), default=0)
        gols_por_jogador = {}
        for gol in resultado.gols.all():
            if gol.jogador_id:
                gols_por_jogador[gol.jogador_id] = gols_por_jogador.get(gol.jogador_id, 0) + gol.quantidade

        for time in resultado.partida.times.all():
            for membro in time.jogadores.all():
                s = de(membro)
                s['jogos'] += 1
                s['gols'] += gols_por_jogador.get(membro.id, 0)
                if vencedor and vencedor['time_id'] == time.id:
                    s['vitorias'] += 1
                elif vencedor is None and gols_por_time.get(time.id, 0) == maior:
                    s['empates'] += 1  # empatou no topo
                else:
                    s['derrotas'] += 1

    # So conta a cronica que ainda vale para o placar atual (nao desatualizada)
    craques = Cronica.objects.filter(
        resultado__partida__grupo=grupo,
        craque__isnull=False,
        baseada_em=F('resultado__registrado_em'),
    ).select_related('craque__usuario')
    for cronica in craques:
        de(cronica.craque)['craque'] += 1

    todos = list(stats.values())
    return {
        'jogos': total_jogos,
        'artilharia': _ordenar_com_colocacao(
            [{'membro': s['membro'], 'nome': s['nome'], 'gols': s['gols'], 'jogos': s['jogos']} for s in todos],
            'gols',
        ),
        'vitorias': _ordenar_com_colocacao(
            [
                {
                    'membro': s['membro'], 'nome': s['nome'], 'vitorias': s['vitorias'],
                    'empates': s['empates'], 'derrotas': s['derrotas'], 'jogos': s['jogos'],
                }
                for s in todos
            ],
            'vitorias',
        ),
        'craques': _ordenar_com_colocacao(
            [{'membro': s['membro'], 'nome': s['nome'], 'vezes': s['craque'], 'jogos': s['jogos']} for s in todos],
            'vezes',
        ),
    }
