from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from grupos.models import Grupo

from .ranking import calcular_ranking


class RankingView(APIView):
    """
    GET /api/grupos/{grupo_id}/ranking/   artilharia, vitorias e craques do grupo (membros)

    {
      "jogos": 6,
      "artilharia": [{"colocacao": 1, "membro": 1, "nome": "João", "gols": 12, "jogos": 6}],
      "vitorias":   [{"colocacao": 1, "membro": 6, "nome": "Pedro", "vitorias": 4,
                      "empates": 1, "derrotas": 1, "jogos": 6}],
      "craques":    [{"colocacao": 1, "membro": 1, "nome": "João", "vezes": 2, "jogos": 6}]
    }
    """

    def get(self, request, grupo_id):
        grupo = Grupo.objects.filter(pk=grupo_id, membros__usuario=request.user).first()
        if not grupo:
            raise NotFound('Grupo não encontrado.')
        return Response(calcular_ranking(grupo))
