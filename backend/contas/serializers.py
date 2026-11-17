from django.contrib.auth import password_validation
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Usuario


class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ['id', 'nome', 'email', 'posicao']
        read_only_fields = ['id', 'email']


class CadastroSerializer(serializers.ModelSerializer):
    senha = serializers.CharField(write_only=True, min_length=8, style={'input_type': 'password'})

    class Meta:
        model = Usuario
        fields = ['id', 'nome', 'email', 'senha', 'posicao']

    def validate_email(self, valor):
        valor = valor.lower()
        if Usuario.objects.filter(email=valor).exists():
            raise serializers.ValidationError('Ja existe uma conta com esse e-mail.')
        return valor

    def validate(self, dados):
        provisorio = Usuario(email=dados.get('email'), nome=dados.get('nome'))
        password_validation.validate_password(dados['senha'], provisorio)
        return dados

    def create(self, dados):
        senha = dados.pop('senha')
        return Usuario.objects.create_user(password=senha, **dados)

    def to_representation(self, usuario):
        """Ja devolve os tokens para o frontend logar direto apos o cadastro."""
        refresh = RefreshToken.for_user(usuario)
        return {
            'usuario': UsuarioSerializer(usuario).data,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }
