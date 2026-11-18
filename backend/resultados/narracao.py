"""Liga a partida salva a narracao escrita pela IA (ia.narracao), #44."""

from ia.cronica import _placar_em_texto

MSG_IA_FORA = 'A IA não respondeu agora. Tente gerar a narração de novo daqui a pouco.'
MSG_RESPOSTA_INVALIDA = 'A IA respondeu num formato inesperado. Tente gerar a narração de novo.'
MSG_RECUSADA = 'Não deu para narrar: descreva uma jogada da partida.'
LIMITE_POR_MEMBRO = 10  # narracoes geradas por membro em cada partida (protege a cota da IA)


def time_de(partida, membro_id):
    """Time da partida em que o membro jogou, ou None."""
    return next((t for t in partida.times.all() if any(j.id == membro_id for j in t.jogadores.all())), None)


def dados_do_lance(resultado, lance, protagonista):
    """Monta o dict que ia.narracao espera."""
    partida = resultado.partida
    gols = {}
    for gol in resultado.gols.all():
        gols[gol.time_id] = gols.get(gol.time_id, 0) + gol.quantidade
    times = [
        {
            'nome': t.nome,
            'gols': gols.get(t.id, 0),
            'jogadores': [m.usuario.nome for m in t.jogadores.all()],
        }
        for t in partida.times.all()
    ]
    time = time_de(partida, protagonista.id)
    return {
        'lance': lance,
        'protagonista': {'nome': protagonista.usuario.nome, 'time': time.nome if time else ''},
        'placar': _placar_em_texto({'times': times}),
        'times': [{'nome': t['nome'], 'jogadores': t['jogadores']} for t in times],
    }
