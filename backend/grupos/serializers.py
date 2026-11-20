from rest_framework import serializers

from .models import Grupo, Membro


class MembroSerializer(serializers.ModelSerializer):
    usuario_id = serializers.IntegerField(source='usuario.id', read_only=True)
    nome = serializers.CharField(source='usuario.nome', read_only=True)

    class Meta:
        model = Membro
        fields = ['id', 'usuario_id', 'nome', 'papel', 'posicao', 'nota', 'entrou_em']
        read_only_fields = fields

    def to_representation(self, membro):
        dados = super().to_representation(membro)
        # A nota so serve para o sorteio: so o organizador ve (como nas rotas de partida).
        if not self.context.get('mostrar_nota'):
            dados.pop('nota')
        return dados


class EditarMembroSerializer(serializers.ModelSerializer):
    """PATCH do organizador: so posicao e nota (1 a 10)."""

    class Meta:
        model = Membro
        fields = ['posicao', 'nota']
        extra_kwargs = {
            'nota': {
                'min_value': 1,
                'max_value': 10,
                'error_messages': {
                    'min_value': 'A nota vai de 1 a 10.',
                    'max_value': 'A nota vai de 1 a 10.',
                    'invalid': 'A nota precisa ser um número inteiro de 1 a 10.',
                },
            },
            'posicao': {'error_messages': {'invalid_choice': 'Posição inválida. Use GOL, ZAG, MEI ou ATA.'}},
        }

    def validate(self, dados):
        if not dados:
            raise serializers.ValidationError({'detail': 'Envie a posição e/ou a nota.'})
        return dados


class GrupoSerializer(serializers.ModelSerializer):
    total_membros = serializers.IntegerField(read_only=True)
    meu_papel = serializers.SerializerMethodField()

    class Meta:
        model = Grupo
        fields = ['id', 'nome', 'codigo_convite', 'total_membros', 'meu_papel', 'criado_em']
        read_only_fields = ['id', 'codigo_convite', 'total_membros', 'meu_papel', 'criado_em']

    def validate_nome(self, valor):
        valor = valor.strip()
        if len(valor) < 3:
            raise serializers.ValidationError('O nome precisa de pelo menos 3 letras.')
        return valor

    def get_meu_papel(self, grupo):
        usuario = self.context['request'].user
        membro = grupo.membros.filter(usuario=usuario).first()
        return membro.papel if membro else None


class EntrarGrupoSerializer(serializers.Serializer):
    codigo = serializers.CharField(max_length=12)

    def validate_codigo(self, valor):
        valor = valor.strip().upper()
        if not valor.startswith('RACHA-'):
            valor = 'RACHA-' + valor
        try:
            return Grupo.objects.get(codigo_convite=valor)
        except Grupo.DoesNotExist:
            raise serializers.ValidationError('Nenhum grupo com esse código.')
