from django.db import transaction
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from grupos.models import Membro
from partidas.models import Partida
from partidas.views import exigir_organizador

from .models import Gol, Resultado
from .serializers import LancarResultadoSerializer, ResultadoSerializer


class ResultadoView(APIView):
    """
    GET /api/partidas/{partida_id}/resultado/   placar e gols (membros do grupo)
    PUT /api/partidas/{partida_id}/resultado/   lanca ou corrige o placar (organizador)
    """

    def partida_e_membro(self, partida_id):
        partida = Partida.objects.filter(pk=partida_id, grupo__membros__usuario=self.request.user).first()
        if not partida:
            raise NotFound('Partida não encontrada.')
        return partida, Membro.objects.get(grupo=partida.grupo_id, usuario=self.request.user)

    def get(self, request, partida_id):
        partida, _ = self.partida_e_membro(partida_id)
        resultado = Resultado.objects.filter(partida=partida).first()
        if not resultado:
            raise NotFound('O resultado ainda não foi lançado.')
        return Response(ResultadoSerializer(resultado).data)

    def put(self, request, partida_id):
        partida, membro = self.partida_e_membro(partida_id)
        exigir_organizador(membro, 'lançar o resultado')
        if partida.status not in (Partida.Status.PUBLICADA, Partida.Status.ENCERRADA):
            raise ValidationError({'detail': 'Publique os times antes de lançar o resultado.'})

        entrada = LancarResultadoSerializer(data=request.data, context={'partida': partida})
        entrada.is_valid(raise_exception=True)

        with transaction.atomic():
            resultado, _ = Resultado.objects.update_or_create(
                partida=partida, defaults={'registrado_por': request.user}
            )
            resultado.gols.all().delete()
            Gol.objects.bulk_create(
                Gol(resultado=resultado, time_id=g['time'], jogador_id=g['jogador'], quantidade=g['quantidade'])
                for g in entrada.validated_data['gols']
            )
            partida.status = Partida.Status.ENCERRADA
            partida.save(update_fields=['status', 'atualizada_em'])

        return Response(ResultadoSerializer(resultado).data)
