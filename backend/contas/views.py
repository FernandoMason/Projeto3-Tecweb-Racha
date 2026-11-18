from rest_framework import generics, permissions
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import CadastroSerializer, UsuarioSerializer


class CadastroView(generics.CreateAPIView):
    """POST /api/auth/cadastro/ -> cria a conta e devolve usuario + tokens."""

    serializer_class = CadastroSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []


class LoginSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        attrs[self.username_field] = attrs.get(self.username_field, '').lower()
        dados = super().validate(attrs)
        dados['usuario'] = UsuarioSerializer(self.user).data
        return dados


class LoginView(TokenObtainPairView):
    """POST /api/auth/login/ {email, password} -> {access, refresh, usuario}."""

    serializer_class = LoginSerializer


class MeView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/auth/me/ -> dados do usuario logado."""

    serializer_class = UsuarioSerializer

    def get_object(self):
        return self.request.user
