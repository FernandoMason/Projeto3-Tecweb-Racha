from rest_framework import serializers

from .models import Grupo, Membro


class MembroSerializer(serializers.ModelSerializer):
    usuario_id = serializers.IntegerField(source='usuario.id', read_only=True)
    nome = serializers.CharField(source='usuario.nome', read_only=True)

    class Meta:
        model = Membro
        fields = ['id', 'usuario_id', 'nome', 'papel', 'posicao', 'nota', 'entrou_em']
        read_only_fields = fields


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
            raise serializers.ValidationError('Nenhum grupo com esse codigo.')
