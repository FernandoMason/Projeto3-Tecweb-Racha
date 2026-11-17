from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import generics, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response

from grupos.models import Membro

from . import sorteio
from .models import Partida, Presenca
from .serializers import PartidaDetalheSerializer, PartidaSerializer, PresencaSerializer, TrocaSerializer


def membro_ou_404(grupo_id, usuario):
    membro = Membro.objects.select_related('grupo').filter(grupo_id=grupo_id, usuario=usuario).first()
    if not membro:
        raise NotFound('Grupo não encontrado ou você não faz parte dele.')
    return membro


def exigir_organizador(membro, acao):
    if not membro.eh_organizador:
        raise PermissionDenied(f'Só o organizador pode {acao}.')


class PartidasDoGrupoView(generics.ListCreateAPIView):
    """
    GET  /api/grupos/{grupo_id}/partidas/   partidas do grupo (mais recentes primeiro)
    POST /api/grupos/{grupo_id}/partidas/   cria partida (so organizador)
    """

    serializer_class = PartidaSerializer

    def membro(self):
        if not hasattr(self, '_membro'):
            self._membro = membro_ou_404(self.kwargs['grupo_id'], self.request.user)
        return self._membro

    def get_serializer_context(self):
        return {**super().get_serializer_context(), 'membro': self.membro()}

    def get_queryset(self):
        grupo_id = self.membro().grupo_id
        # Montagem automatica: quem abre a lista ja dispara o sorteio das partidas que passaram da hora.
        for partida in Partida.objects.filter(grupo_id=grupo_id, status=Partida.Status.ABERTA):
            sorteio.montar_se_chegou_a_hora(partida)
        return (
            Partida.objects.filter(grupo_id=grupo_id)
            .annotate(total_confirmados=Count('presencas', filter=Q(presencas__status=Presenca.Status.VOU)))
            .select_related('resultado')
            .prefetch_related('times', 'resultado__gols')
            .order_by('-data_hora')
        )

    def create(self, request, *args, **kwargs):
        membro = self.membro()
        exigir_organizador(membro, 'criar partidas')
        entrada = self.get_serializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        partida = entrada.save(grupo=membro.grupo, criada_por=request.user)
        dados = PartidaDetalheSerializer(partida, context=self.get_serializer_context()).data
        return Response(dados, status=status.HTTP_201_CREATED)


class PartidaViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    GET  /api/partidas/{id}/                 detalhe (presenca, times, resultado)
    POST /api/partidas/{id}/presenca/        {vou: true|false}
    POST /api/partidas/{id}/montar-times/    IA monta (ou refaz) os times -> rascunho   [organizador]
    POST /api/partidas/{id}/confirmar-times/ publica o rascunho para o grupo            [organizador]
    POST /api/partidas/{id}/trocar/          {jogador_a, jogador_b} troca de time       [organizador]
    """

    serializer_class = PartidaDetalheSerializer

    def get_queryset(self):
        return Partida.objects.filter(grupo__membros__usuario=self.request.user).select_related('grupo')

    def get_object(self):
        partida = super().get_object()
        self.membro = Membro.objects.get(grupo=partida.grupo, usuario=self.request.user)
        return partida

    def get_serializer_context(self):
        return {**super().get_serializer_context(), 'membro': getattr(self, 'membro', None)}

    def responder(self, partida):
        partida.refresh_from_db()
        return Response(self.get_serializer(partida).data)

    def retrieve(self, request, *args, **kwargs):
        partida = sorteio.montar_se_chegou_a_hora(self.get_object())
        return self.responder(partida)

    @action(detail=True, methods=['post'])
    def presenca(self, request, pk=None):
        partida = self.get_object()
        entrada = PresencaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        if partida.status != Partida.Status.ABERTA:
            raise ValidationError({'detail': 'Os times já foram montados. Fale com o organizador.'})
        if partida.data_hora <= timezone.now():
            raise ValidationError({'detail': 'Essa partida já começou.'})

        novo = Presenca.Status.VOU if entrada.validated_data['vou'] else Presenca.Status.NAO_VOU
        presenca, _ = Presenca.objects.get_or_create(partida=partida, membro=self.membro, defaults={'status': novo})
        if presenca.status != novo or (novo == Presenca.Status.VOU and not presenca.confirmada_em):
            presenca.status = novo
            presenca.confirmada_em = timezone.now() if novo == Presenca.Status.VOU else None
            presenca.save()
        return self.responder(partida)

    @action(detail=True, methods=['post'], url_path='montar-times')
    def montar_times(self, request, pk=None):
        partida = self.get_object()
        exigir_organizador(self.membro, 'montar os times')
        try:
            sorteio.montar_times(
                partida,
                publicar=False,
                permitidos=(Partida.Status.ABERTA, Partida.Status.RASCUNHO, Partida.Status.PUBLICADA),
            )
        except sorteio.SorteioImpossivel as erro:
            raise ValidationError({'detail': str(erro)})
        return self.responder(partida)

    @action(detail=True, methods=['post'], url_path='confirmar-times')
    def confirmar_times(self, request, pk=None):
        partida = self.get_object()
        exigir_organizador(self.membro, 'confirmar os times')
        if partida.status != Partida.Status.RASCUNHO:
            raise ValidationError({'detail': 'Não há times aguardando confirmação.'})
        partida.status = Partida.Status.PUBLICADA
        partida.times_publicados_em = timezone.now()
        partida.save(update_fields=['status', 'times_publicados_em', 'atualizada_em'])
        return self.responder(partida)

    @action(detail=True, methods=['post'])
    def trocar(self, request, pk=None):
        partida = self.get_object()
        exigir_organizador(self.membro, 'trocar jogadores')
        if partida.status not in (Partida.Status.RASCUNHO, Partida.Status.PUBLICADA):
            raise ValidationError({'detail': 'Só dá para trocar jogadores antes do resultado.'})
        entrada = TrocaSerializer(data=request.data, context={'partida': partida})
        entrada.is_valid(raise_exception=True)
        dados = entrada.validated_data
        with transaction.atomic():
            dados['time_a'].jogadores.remove(dados['jogador_a'])
            dados['time_b'].jogadores.remove(dados['jogador_b'])
            dados['time_a'].jogadores.add(dados['jogador_b'])
            dados['time_b'].jogadores.add(dados['jogador_a'])
            sorteio.recalcular_forcas(partida)
            partida.ajustado_pelo_organizador = True
            partida.save(update_fields=['ajustado_pelo_organizador', 'atualizada_em'])
        return self.responder(partida)
