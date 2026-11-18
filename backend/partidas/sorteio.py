"""
Sorteio de times com IA (#27) e montagem automatica (#29).

Fluxo de `montar_times`:
1. pega os titulares (primeiros confirmados ate encher as vagas);
2. roda o algoritmo de reserva para saber o "quao equilibrado da para ficar";
3. pede ao Gemini os times + uma explicacao curta, em JSON;
4. valida a resposta (equilibrio.validar). Se tiver erro, devolve os erros
   para a IA e pede de novo (1 nova tentativa);
5. se a IA falhar ou errar de novo, usa o algoritmo de reserva e avisa isso
   na explicacao. O sorteio nunca trava por causa da IA.
"""

import json
import logging
from datetime import timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from ia import gemini

from . import equilibrio
from .models import TIMES_PADRAO, Partida, Time

log = logging.getLogger(__name__)

TENTATIVAS_IA = 2

INSTRUCOES = """Você é o "Racha", assistente que monta times de futebol amador (pelada) entre amigos.
Seu trabalho: dividir os jogadores confirmados em times EQUILIBRADOS e explicar a escolha.

Regras obrigatórias:
- Use exatamente os ids recebidos. Cada jogador entra em exatamente UM time. Ninguém fica de fora.
- Os times têm o mesmo tamanho (diferença máxima de 1 jogador).
- Separe os goleiros (GOL): no máximo 1 goleiro de diferença entre os times.
- A força de um time é a MÉDIA das notas (1 a 10). A diferença entre o time mais forte
  e o mais fraco deve ser a menor possível e nunca maior que o limite informado.
- Misture as posições: cada time deve ter defesa (ZAG), meio (MEI) e ataque (ATA) quando der.

Explicação (campo "explicacao"):
- Português do Brasil, tom de resenha de pelada, 2 ou 3 frases, até 280 caracteres.
- Cite os jogadores pelo nome e use os nomes dos times (ex.: "o Verde", "o Preto").
- NUNCA revele a nota individual de ninguém (a explicação aparece para todo o grupo).
"""

SCHEMA = {
    'type': 'object',
    'properties': {
        'times': {
            'type': 'array',
            'description': 'Um item por time, na mesma ordem dos nomes de time informados.',
            'items': {
                'type': 'object',
                'properties': {
                    'nome': {'type': 'string'},
                    'jogadores': {'type': 'array', 'items': {'type': 'integer'}},
                },
                'required': ['nome', 'jogadores'],
            },
        },
        'explicacao': {'type': 'string'},
    },
    'required': ['times', 'explicacao'],
}


class SorteioImpossivel(Exception):
    """Faltam jogadores ou a partida nao esta num estado que permite sortear."""


def jogadores_da_partida(partida):
    return [
        equilibrio.Jogador(
            id=p.membro_id, nome=p.membro.usuario.nome, posicao=p.membro.posicao, nota=p.membro.nota
        )
        for p in partida.titulares()
    ]


def montar_prompt(jogadores, nomes_times, referencia, erros_anteriores=None, times_anteriores=None):
    linhas = [f'- id {j.id} | {j.nome} | {j.posicao} | nota {j.nota}' for j in jogadores]
    tamanhos = equilibrio.tamanhos_esperados(len(jogadores), len(nomes_times))
    partes = [
        f'Monte {len(nomes_times)} times ({", ".join(nomes_times)}) com {len(jogadores)} jogadores '
        f'(tamanhos: {tamanhos}).',
        f'Diferenca maxima de forca (media) aceita: {equilibrio.limite_aceito(referencia):.2f}.',
        '',
        'Jogadores confirmados:',
        *linhas,
    ]
    if times_anteriores:
        # "Sortear de novo": pede uma divisao diferente da que o organizador ja viu.
        partes += [
            '',
            'O organizador pediu um NOVO sorteio. Monte uma divisao diferente desta:',
            json.dumps(times_anteriores, ensure_ascii=False),
        ]
    if erros_anteriores:
        partes += [
            '',
            'Sua resposta anterior foi recusada pela validacao do sistema por estes motivos:',
            *[f'- {e}' for e in erros_anteriores],
            'Corrija e responda de novo.',
        ]
    return '\n'.join(partes)


def pedir_times_para_ia(jogadores, nomes_times, referencia, times_anteriores=None):
    """
    Devolve (times_ids, explicacao) ou None se a IA nao conseguir uma proposta valida.
    """
    erros = None
    for tentativa in range(1, TENTATIVAS_IA + 1):
        prompt = montar_prompt(jogadores, nomes_times, referencia, erros, times_anteriores)
        try:
            resposta = gemini.gerar_json(prompt, json_schema=SCHEMA, instrucoes=INSTRUCOES, temperatura=0.9)
            times_ids = [[int(i) for i in t['jogadores']] for t in resposta['times']]
            explicacao = str(resposta['explicacao']).strip()
        except gemini.IAIndisponivel as erro:
            log.warning('Sorteio sem IA: %s', erro)
            return None
        except (gemini.RespostaInvalida, KeyError, TypeError, ValueError) as erro:
            erros = [f'A resposta nao veio no formato JSON pedido ({erro}).']
            continue

        erros = equilibrio.validar(times_ids, jogadores, len(nomes_times), referencia)
        if not erros and explicacao:
            return times_ids, explicacao
        if not explicacao:
            erros.append('Faltou a explicacao.')
        log.info('Tentativa %s da IA recusada: %s', tentativa, erros)
    return None


def explicacao_de_reserva(times_ids, jogadores):
    por_id = {j.id: j for j in jogadores}
    times = [[por_id[i] for i in ids] for ids in times_ids]
    goleiros = [j.nome for t in times for j in t if j.posicao == equilibrio.GOLEIRO]
    como = 'distribuí as notas em zigue-zague, do melhor para o pior'
    if len(goleiros) > 1:
        como = f'separei os goleiros ({", ".join(goleiros)}) e ' + como
    dif = f'{equilibrio.diferenca(times):.1f}'.replace('.', ',')
    return f'A IA não respondeu, então montei os times pelo plano B: {como}. Diferença de força: {dif}.'


def _reservar(partida, permitidos):
    """
    Marca a partida como SORTEANDO so se ela ainda estiver num dos status permitidos.
    O UPDATE condicional evita duas montagens ao mesmo tempo (dois cliques, duas abas).
    Uma montagem "presa" ha mais de 2 min (servidor caiu no meio) pode ser refeita.
    """
    agora = timezone.now()
    livre = Q(status__in=permitidos) | Q(
        status=Partida.Status.SORTEANDO, atualizada_em__lt=agora - timedelta(minutes=2)
    )
    return bool(
        Partida.objects.filter(livre, pk=partida.pk).update(status=Partida.Status.SORTEANDO, atualizada_em=agora)
    )


def montar_times(partida, *, publicar, permitidos=(Partida.Status.ABERTA,)):
    """
    Monta os times da partida (IA com validacao, ou algoritmo de reserva).

    publicar=True  -> todos veem na hora (montagem automatica).
    publicar=False -> fica como rascunho para o organizador conferir/trocar/confirmar.
    """
    status_antes = partida.status
    jogadores = jogadores_da_partida(partida)
    if len(jogadores) < partida.minimo_para_sortear:
        raise SorteioImpossivel(
            f'Precisa de pelo menos {partida.minimo_para_sortear} confirmados para montar '
            f'{partida.num_times} times (hoje: {len(jogadores)}).'
        )
    if not _reservar(partida, permitidos):
        raise SorteioImpossivel('Os times já estão sendo montados. Aguarde alguns segundos.')

    try:
        nomes = [nome for nome, _ in TIMES_PADRAO[: partida.num_times]]
        referencia_ids = equilibrio.montar_por_algoritmo(jogadores, partida.num_times)
        por_id = {j.id: j for j in jogadores}
        referencia = equilibrio.diferenca([[por_id[i] for i in t] for t in referencia_ids])

        anteriores = None
        if status_antes in (Partida.Status.RASCUNHO, Partida.Status.PUBLICADA):
            anteriores = {t.nome: [m.usuario.nome for m in t.jogadores.all()] for t in partida.times.all()}

        proposta = pedir_times_para_ia(jogadores, nomes, referencia, anteriores)
        if proposta:
            times_ids, explicacao = proposta
            origem = Partida.Origem.IA
        else:
            times_ids = referencia_ids
            explicacao = explicacao_de_reserva(times_ids, jogadores)
            origem = Partida.Origem.RESERVA

        salvar_times(partida, times_ids, jogadores, explicacao, origem, publicar)
    except Exception:
        Partida.objects.filter(pk=partida.pk).update(status=status_antes)
        raise
    partida.refresh_from_db()
    return partida


@transaction.atomic
def salvar_times(partida, times_ids, jogadores, explicacao, origem, publicar):
    por_id = {j.id: j for j in jogadores}
    partida.times.all().delete()
    for ordem, ids in enumerate(times_ids):
        nome, cor = TIMES_PADRAO[ordem]
        time = Time.objects.create(
            partida=partida,
            nome=nome,
            cor=cor,
            ordem=ordem,
            forca=equilibrio.forca([por_id[i] for i in ids]),
        )
        time.jogadores.set(ids)

    agora = timezone.now()
    partida.explicacao_ia = explicacao
    partida.origem_times = origem
    partida.ajustado_pelo_organizador = False
    partida.times_montados_em = agora
    partida.status = Partida.Status.PUBLICADA if publicar else Partida.Status.RASCUNHO
    partida.times_publicados_em = agora if publicar else None
    partida.save()


def montar_se_chegou_a_hora(partida):
    """
    Montagem automatica (#29): se ja passou do horario do sorteio e a presenca
    ainda esta aberta, a IA monta e publica os times.

    E chamada quando alguem abre a partida (nao precisa de servidor de tarefas)
    e tambem pelo comando `python manage.py montar_times_agendados` (cron do deploy).
    """
    agora = timezone.now()
    if partida.status != Partida.Status.ABERTA or agora < partida.sorteio_em:
        return partida
    if partida.confirmados().count() < partida.minimo_para_sortear:
        return partida
    try:
        return montar_times(partida, publicar=True)
    except SorteioImpossivel:
        partida.refresh_from_db()
        return partida


def recalcular_forcas(partida):
    for time in partida.times.all():
        notas = [m.nota for m in time.jogadores.all()]
        time.forca = round(sum(notas) / len(notas), 2) if notas else 0
        time.save(update_fields=['forca'])
