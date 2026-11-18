from rest_framework import serializers, status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from grupos.models import Membro
from partidas.models import Partida
from partidas.views import exigir_organizador

from .cronica import CronicaMantida, gerar_e_salvar
from .models import Cronica, Resultado


class CronicaSerializer(serializers.ModelSerializer):
    craque = serializers.SerializerMethodField()
    desatualizada = serializers.BooleanField(read_only=True)

    class Meta:
        model = Cronica
        fields = ['status', 'titulo', 'texto', 'craque', 'origem_craque', 'erro', 'gerada_em', 'desatualizada']

    def get_craque(self, cronica):
        if not cronica.craque:
            return None
        return {'membro': cronica.craque_id, 'nome': cronica.craque.usuario.nome, 'motivo': cronica.motivo_craque}


class CronicaView(APIView):
    """
    GET  /api/partidas/{partida_id}/resultado/cronica/   cronica e craque (membros do grupo)
    POST /api/partidas/{partida_id}/resultado/cronica/   gera ou gera de novo com a IA (organizador)

    O POST espera a IA (alguns segundos). Se ela falhar, responde 200 com status 'erro'
    e o artilheiro como craque; se ja havia uma cronica boa e atualizada, ela e mantida
    e a resposta e 503 com {detail, cronica}.
    """

    def membro_e_resultado(self, partida_id):
        partida = Partida.objects.filter(pk=partida_id, grupo__membros__usuario=self.request.user).first()
        if not partida:
            raise NotFound('Partida não encontrada.')
        membro = Membro.objects.get(grupo=partida.grupo_id, usuario=self.request.user)
        resultado = Resultado.objects.filter(partida=partida).first()
        if not resultado:
            raise NotFound('O resultado ainda não foi lançado.')
        return membro, resultado

    def get(self, request, partida_id):
        _, resultado = self.membro_e_resultado(partida_id)
        cronica = Cronica.objects.filter(resultado=resultado).select_related('craque__usuario', 'resultado').first()
        if not cronica:
            raise NotFound('A crônica ainda não foi gerada.')
        return Response(CronicaSerializer(cronica).data)

    def post(self, request, partida_id):
        membro, resultado = self.membro_e_resultado(partida_id)
        exigir_organizador(membro, 'gerar a crônica')
        try:
            cronica = gerar_e_salvar(resultado)
        except CronicaMantida as mantida:
            return Response(
                {'detail': mantida.mensagem, 'cronica': CronicaSerializer(mantida.cronica).data},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(CronicaSerializer(cronica).data)
