from django.utils import timezone
from rest_framework import serializers

from .models import Partida


def _resultado(partida):
    # OneToOne reverso: sem resultado o Django levanta uma excecao que tambem e AttributeError
    return getattr(partida, 'resultado', None)


def jogador_json(membro, mostrar_nota):
    dados = {'membro_id': membro.id, 'nome': membro.usuario.nome, 'posicao': membro.posicao}
    if mostrar_nota:
        dados['nota'] = membro.nota
    return dados


class PartidaSerializer(serializers.ModelSerializer):
    """Resumo da partida (lista do grupo). O contexto precisa de `membro` (quem esta vendo)."""

    sorteio_em = serializers.DateTimeField(read_only=True)
    vagas = serializers.IntegerField(read_only=True)
    total_confirmados = serializers.SerializerMethodField()
    minha_presenca = serializers.SerializerMethodField()
    placar = serializers.SerializerMethodField()

    class Meta:
        model = Partida
        fields = [
            'id', 'grupo', 'data_hora', 'local', 'num_times', 'jogadores_por_time',
            'antecedencia_horas', 'sorteio_em', 'vagas', 'status', 'total_confirmados',
            'minha_presenca', 'placar',
        ]
        read_only_fields = ['id', 'grupo', 'status']

    def validate_data_hora(self, valor):
        if valor <= timezone.now():
            raise serializers.ValidationError('Escolha uma data e hora no futuro.')
        return valor

    def validate_local(self, valor):
        valor = valor.strip()
        if len(valor) < 2:
            raise serializers.ValidationError('Informe o local do jogo.')
        return valor

    def get_total_confirmados(self, partida):
        anotado = getattr(partida, 'total_confirmados', None)
        return anotado if anotado is not None else partida.confirmados().count()

    def get_minha_presenca(self, partida):
        membro = self.context.get('membro')
        presenca = partida.presencas.filter(membro=membro).first() if membro else None
        return presenca.status if presenca else None

    def get_placar(self, partida):
        resultado = _resultado(partida)
        return resultado.placar() if resultado else None


class PartidaDetalheSerializer(PartidaSerializer):
    """Tudo que as telas da partida e do sorteio precisam."""

    grupo_nome = serializers.CharField(source='grupo.nome', read_only=True)
    minimo_para_sortear = serializers.IntegerField(read_only=True)
    eh_organizador = serializers.SerializerMethodField()
    confirmados = serializers.SerializerMethodField()
    lista_espera = serializers.SerializerMethodField()
    nao_vao = serializers.SerializerMethodField()
    times = serializers.SerializerMethodField()
    diferenca_forca = serializers.SerializerMethodField()
    explicacao_ia = serializers.SerializerMethodField()
    resultado = serializers.SerializerMethodField()

    class Meta(PartidaSerializer.Meta):
        fields = PartidaSerializer.Meta.fields + [
            'grupo_nome', 'minimo_para_sortear', 'eh_organizador', 'confirmados', 'lista_espera',
            'nao_vao', 'times', 'diferenca_forca', 'explicacao_ia', 'origem_times', 'ajustado_pelo_organizador',
            'times_montados_em', 'times_publicados_em', 'resultado',
        ]
        read_only_fields = fields

    # --- helpers ---
    def _organizador(self):
        membro = self.context.get('membro')
        return bool(membro and membro.eh_organizador)

    def _times_visiveis(self, partida):
        if partida.status in (Partida.Status.PUBLICADA, Partida.Status.ENCERRADA):
            return True
        return partida.status == Partida.Status.RASCUNHO and self._organizador()

    def _confirmados(self, partida):
        if not hasattr(self, '_cache_confirmados'):
            self._cache_confirmados = list(partida.confirmados())
        return self._cache_confirmados

    # --- campos ---
    def get_eh_organizador(self, partida):
        return self._organizador()

    def get_total_confirmados(self, partida):
        return len(self._confirmados(partida))

    def get_confirmados(self, partida):
        return [jogador_json(p.membro, False) for p in self._confirmados(partida)[: partida.vagas]]

    def get_lista_espera(self, partida):
        return [jogador_json(p.membro, False) for p in self._confirmados(partida)[partida.vagas :]]

    def get_nao_vao(self, partida):
        return [
            jogador_json(p.membro, False)
            for p in partida.presencas.filter(status='nao_vou').select_related('membro__usuario')
        ]

    def get_times(self, partida):
        if not self._times_visiveis(partida):
            return []
        mostrar_nota = self._organizador()
        return [
            {
                'id': t.id,
                'nome': t.nome,
                'cor': t.cor,
                'forca': t.forca,
                'jogadores': [jogador_json(m, mostrar_nota) for m in t.jogadores.select_related('usuario')],
            }
            for t in partida.times.all()
        ]

    def get_diferenca_forca(self, partida):
        forcas = [t.forca for t in partida.times.all()]
        return round(max(forcas) - min(forcas), 2) if forcas and self._times_visiveis(partida) else None

    def get_explicacao_ia(self, partida):
        return partida.explicacao_ia if self._times_visiveis(partida) else ''

    def get_resultado(self, partida):
        from resultados.serializers import ResultadoSerializer

        resultado = _resultado(partida)
        return ResultadoSerializer(resultado).data if resultado else None


class PresencaSerializer(serializers.Serializer):
    vou = serializers.BooleanField()


class TrocaSerializer(serializers.Serializer):
    """Troca dois jogadores (ids de Membro) de times diferentes."""

    jogador_a = serializers.IntegerField()
    jogador_b = serializers.IntegerField()

    def validate(self, dados):
        partida = self.context['partida']
        time_de = {}
        for time in partida.times.prefetch_related('jogadores'):
            for membro in time.jogadores.all():
                time_de[membro.id] = time
        a, b = dados['jogador_a'], dados['jogador_b']
        if a not in time_de or b not in time_de:
            raise serializers.ValidationError('Os dois jogadores precisam estar nos times desta partida.')
        if time_de[a] == time_de[b]:
            raise serializers.ValidationError('Escolha jogadores de times diferentes.')
        dados['time_a'], dados['time_b'] = time_de[a], time_de[b]
        return dados
