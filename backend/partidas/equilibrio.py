"""
Validacao de equilibrio dos times (#28) e algoritmo de reserva.

A IA propoe os times e explica a escolha, mas quem decide se a proposta
vale e este codigo: ele confere se ninguem sumiu ou foi repetido, se os
tamanhos batem, se os goleiros foram separados e se a diferenca de forca
(media das notas) esta dentro do limite.

O mesmo modulo tem um algoritmo simples (zigue-zague + trocas) que serve
para duas coisas:
1. dar a referencia do "quao equilibrado da para ficar" com esses jogadores;
2. ser o plano B quando a IA falha ou erra duas vezes.
"""

import random
from dataclasses import dataclass

# Diferenca maxima aceita entre o time mais forte e o mais fraco (media das notas, 1 a 10).
LIMITE_DIFERENCA = 0.5
GOLEIRO = 'GOL'


@dataclass(frozen=True)
class Jogador:
    id: int  # id do Membro
    nome: str
    posicao: str
    nota: int


def forca(jogadores):
    """Forca de um time = media das notas dos jogadores."""
    if not jogadores:
        return 0.0
    return round(sum(j.nota for j in jogadores) / len(jogadores), 2)


def diferenca(times):
    """Distancia entre o time mais forte e o mais fraco."""
    forcas = [forca(t) for t in times]
    return round(max(forcas) - min(forcas), 2)


def tamanhos_esperados(total, num_times):
    """10 jogadores em 2 times -> [5, 5]; 11 em 2 -> [6, 5]."""
    base, resto = divmod(total, num_times)
    return [base + 1] * resto + [base] * (num_times - resto)


def limite_aceito(referencia):
    """Se nem o algoritmo chega a 0,5 (notas muito diferentes), aceita o que ele conseguiu."""
    return max(LIMITE_DIFERENCA, referencia)


def validar(times_ids, jogadores, num_times, referencia):
    """
    Confere uma proposta de times (lista de listas de ids).

    Devolve a lista de problemas encontrados; lista vazia = proposta aprovada.
    As mensagens voltam para a IA na segunda tentativa, entao sao bem diretas.
    """
    por_id = {j.id: j for j in jogadores}
    erros = []

    if len(times_ids) != num_times:
        return [f'Eram {num_times} times, mas vieram {len(times_ids)}.']

    vistos = set()
    for ids in times_ids:
        for jid in ids:
            if jid not in por_id:
                erros.append(f'O id {jid} nao esta na lista de confirmados.')
            elif jid in vistos:
                erros.append(f'{por_id[jid].nome} (id {jid}) apareceu em mais de um time.')
            vistos.add(jid)

    faltando = [por_id[jid] for jid in por_id if jid not in vistos]
    if faltando:
        erros.append('Ficaram de fora: ' + ', '.join(f'{j.nome} (id {j.id})' for j in faltando) + '.')

    tamanhos = [len(ids) for ids in times_ids]
    if max(tamanhos) - min(tamanhos) > 1:
        erros.append(f'Os times ficaram com {tamanhos} jogadores; a diferenca maxima e de 1 jogador.')

    if erros:  # sem a estrutura certa nao da para medir o resto
        return erros

    times = [[por_id[jid] for jid in ids] for ids in times_ids]

    goleiros = [sum(1 for j in t if j.posicao == GOLEIRO) for t in times]
    if max(goleiros) - min(goleiros) > 1:
        erros.append(f'Os goleiros ficaram concentrados ({goleiros} por time); separe os goleiros.')

    dif = diferenca(times)
    limite = limite_aceito(referencia)
    if dif > limite:
        forcas = ', '.join(f'{forca(t):.2f}' for t in times)
        erros.append(
            f'Times desequilibrados: medias {forcas} (diferenca {dif:.2f}); o maximo aceito e {limite:.2f}.'
        )
    return erros


def _zigue_zague(n):
    """0, 1, ..., n-1, n-1, ..., 0, 0, 1, ... (como escolher time no par ou impar)."""
    while True:
        yield from range(n)
        yield from reversed(range(n))


def montar_por_algoritmo(jogadores, num_times, rng=None):
    """
    Plano B sem IA: distribui em zigue-zague do melhor para o pior (goleiros
    primeiro) e depois testa trocas entre times enquanto alguma diminuir a
    diferenca. Empates de nota sao embaralhados, entao "sortear de novo" muda.
    """
    rng = rng or random.Random()
    tamanhos = tamanhos_esperados(len(jogadores), num_times)
    times = [[] for _ in range(num_times)]

    def ordenar(lista):
        return sorted(lista, key=lambda j: (-j.nota, rng.random()))

    fila = ordenar([j for j in jogadores if j.posicao == GOLEIRO]) + ordenar(
        [j for j in jogadores if j.posicao != GOLEIRO]
    )
    sequencia = _zigue_zague(num_times)
    for jogador in fila:
        while True:
            t = next(sequencia)
            if len(times[t]) < tamanhos[t]:
                times[t].append(jogador)
                break

    # Melhora local: troca dois jogadores (goleiro so com goleiro) se a diferenca cair.
    melhorou = True
    while melhorou:
        melhorou = False
        atual = diferenca(times)
        for a in range(num_times):
            for b in range(a + 1, num_times):
                for i, x in enumerate(times[a]):
                    for k, y in enumerate(times[b]):
                        if (x.posicao == GOLEIRO) != (y.posicao == GOLEIRO) or x.nota == y.nota:
                            continue
                        times[a][i], times[b][k] = y, x
                        nova = diferenca(times)
                        if nova < atual - 1e-9:
                            atual, melhorou = nova, True
                            x, y = y, x  # a troca fica; seguimos a partir dela
                        else:
                            times[a][i], times[b][k] = x, y

    return [[j.id for j in t] for t in times]
