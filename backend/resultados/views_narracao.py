import logging

from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from grupos.models import Membro
from ia import gemini
from ia.narracao import LIMITE_LANCE, NarracaoRecusada, gerar_narracao
from partidas.models import Partida

from .models import Narracao, Resultado
from .narracao import (
    LIMITE_POR_MEMBRO,
    MSG_IA_FORA,
    MSG_RECUSADA,
    MSG_RESPOSTA_INVALIDA,
    dados_do_lance,
    time_de,
)

log = logging.getLogger(__name__)


def _pessoa(membro):
    return {'membro': membro.id, 'nome': membro.usuario.nome}


class NarracaoSerializer(serializers.ModelSerializer):
    autor = serializers.SerializerMethodField()
    protagonista = serializers.SerializerMethodField()
    pode_apagar = serializers.SerializerMethodField()

    class Meta:
        model = Narracao
        fields = [
            'id', 'lance', 'grito', 'narracao', 'autor', 'protagonista',
            'publicada', 'criada_em', 'publicada_em', 'pode_apagar',
        ]

    def get_autor(self, n):
        return _pessoa(n.autor)

    def get_protagonista(self, n):
        return _pessoa(n.protagonista)

    def get_pode_apagar(self, n):
        membro = self.context.get('membro')
        return bool(membro and (membro.id == n.autor_id or membro.eh_organizador))


class NovaNarracaoSerializer(serializers.Serializer):
    lance = serializers.CharField(min_length=5, max_length=LIMITE_LANCE, trim_whitespace=True)
    protagonista = serializers.IntegerField(required=False, allow_null=True, default=None)


class NarracoesDaPartidaView(APIView):
    """
    GET  /api/partidas/{partida_id}/narracoes/   mural: narracoes publicadas (membros)
    POST /api/partidas/{partida_id}/narracoes/   {lance, protagonista?} -> a IA narra; cria um rascunho (membros)

    O POST espera a IA (alguns segundos). Sem plano B: se a IA falhar, 503 e nada e salvo.
    """

    def contexto(self, partida_id):
        partida = (
            Partida.objects.filter(pk=partida_id, grupo__membros__usuario=self.request.user)
            .prefetch_related('times__jogadores__usuario')
            .first()
        )
        if not partida:
            raise NotFound('Partida não encontrada.')
        membro = Membro.objects.select_related('usuario').get(grupo=partida.grupo_id, usuario=self.request.user)
        resultado = Resultado.objects.filter(partida=partida).prefetch_related('gols').first()
        if not resultado:
            raise NotFound('O resultado ainda não foi lançado.')
        return partida, membro, resultado

    def get(self, request, partida_id):
        partida, membro, _ = self.contexto(partida_id)
        mural = partida.narracoes.filter(publicada=True).select_related('autor__usuario', 'protagonista__usuario')
        return Response(NarracaoSerializer(mural, many=True, context={'membro': membro}).data)

    def post(self, request, partida_id):
        partida, membro, resultado = self.contexto(partida_id)
        entrada = NovaNarracaoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)

        protagonista_id = entrada.validated_data['protagonista'] or membro.id
        if not time_de(partida, protagonista_id):
            if entrada.validated_data['protagonista'] is None:
                raise ValidationError({'protagonista': 'Você não jogou esta partida: escolha quem fez o lance.'})
            raise ValidationError({'protagonista': 'Esse jogador não jogou esta partida.'})
        protagonista = next(j for t in partida.times.all() for j in t.jogadores.all() if j.id == protagonista_id)

        if partida.narracoes.filter(autor=membro).count() >= LIMITE_POR_MEMBRO:
            return Response(
                {'detail': f'Você já gerou {LIMITE_POR_MEMBRO} narrações nesta partida.'},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        try:
            gerada = gerar_narracao(dados_do_lance(resultado, entrada.validated_data['lance'], protagonista))
        except NarracaoRecusada:
            return Response({'detail': MSG_RECUSADA}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        except (gemini.IAIndisponivel, gemini.RespostaInvalida) as erro:
            log.warning('Narração da partida %s falhou: %s', partida.id, erro)
            mensagem = MSG_IA_FORA if isinstance(erro, gemini.IAIndisponivel) else MSG_RESPOSTA_INVALIDA
            return Response({'detail': mensagem}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        narracao = Narracao.objects.create(
            partida=partida,
            autor=membro,
            protagonista=protagonista,
            lance=entrada.validated_data['lance'],
            grito=gerada['grito'],
            narracao=gerada['narracao'],
        )
        return Response(NarracaoSerializer(narracao, context={'membro': membro}).data, status=status.HTTP_201_CREATED)


class NarracaoBase(APIView):
    def narracao_e_membro(self, narracao_id):
        narracao = (
            Narracao.objects.filter(pk=narracao_id, partida__grupo__membros__usuario=self.request.user)
            .select_related('autor__usuario', 'protagonista__usuario', 'partida')
            .first()
        )
        if not narracao:
            raise NotFound('Narração não encontrada.')
        membro = Membro.objects.get(grupo=narracao.partida.grupo_id, usuario=self.request.user)
        # rascunho e so do autor: para os outros, nem existe
        if not narracao.publicada and narracao.autor_id != membro.id and not membro.eh_organizador:
            raise NotFound('Narração não encontrada.')
        return narracao, membro


class NarracaoView(NarracaoBase):
    """DELETE /api/narracoes/{id}/   apaga (autor ou organizador)"""

    def delete(self, request, narracao_id):
        narracao, membro = self.narracao_e_membro(narracao_id)
        if narracao.autor_id != membro.id and not membro.eh_organizador:
            raise PermissionDenied('Só quem narrou ou o organizador pode apagar.')
        narracao.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PublicarNarracaoView(NarracaoBase):
    """POST /api/narracoes/{id}/publicar/   leva o rascunho para o mural (so o autor)"""

    def post(self, request, narracao_id):
        narracao, membro = self.narracao_e_membro(narracao_id)
        if narracao.autor_id != membro.id:
            raise PermissionDenied('Só quem narrou pode publicar.')
        if not narracao.publicada:
            narracao.publicada = True
            narracao.publicada_em = timezone.now()
            narracao.save(update_fields=['publicada', 'publicada_em'])
        return Response(NarracaoSerializer(narracao, context={'membro': membro}).data)
