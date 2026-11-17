from rest_framework import serializers

from .models import Gol, Resultado


class GolSerializer(serializers.ModelSerializer):
    nome = serializers.SerializerMethodField()

    class Meta:
        model = Gol
        fields = ['id', 'time', 'jogador', 'nome', 'quantidade']

    def get_nome(self, gol):
        return gol.jogador.usuario.nome if gol.jogador else 'Gol contra / sem autor'


class ResultadoSerializer(serializers.ModelSerializer):
    placar = serializers.SerializerMethodField()
    vencedor = serializers.SerializerMethodField()
    gols = GolSerializer(many=True, read_only=True)

    class Meta:
        model = Resultado
        fields = ['partida', 'placar', 'vencedor', 'gols', 'registrado_em']

    def get_placar(self, resultado):
        return resultado.placar()

    def get_vencedor(self, resultado):
        return resultado.vencedor()


class GolEntradaSerializer(serializers.Serializer):
    time = serializers.IntegerField()
    jogador = serializers.IntegerField(allow_null=True, required=False, default=None)
    quantidade = serializers.IntegerField(min_value=1, max_value=50, default=1)


class LancarResultadoSerializer(serializers.Serializer):
    """
    PUT /api/partidas/{id}/resultado/
    {"gols": [{"time": 3, "jogador": 12, "quantidade": 2}, {"time": 4, "jogador": null}]}
    O placar e a soma dos gols de cada time. Lista vazia = 0 x 0.
    """

    gols = GolEntradaSerializer(many=True)

    def validate_gols(self, gols):
        partida = self.context['partida']
        times = {t.id: {m.id for m in t.jogadores.all()} for t in partida.times.prefetch_related('jogadores')}
        vistos = set()
        for gol in gols:
            if gol['time'] not in times:
                raise serializers.ValidationError('Um dos gols é de um time que não está nesta partida.')
            jogador = gol['jogador']
            if jogador is not None:
                if jogador not in times[gol['time']]:
                    raise serializers.ValidationError('Um dos goleadores não joga no time indicado.')
                if jogador in vistos:
                    raise serializers.ValidationError('Some os gols do mesmo jogador numa linha só.')
                vistos.add(jogador)
        return gols
