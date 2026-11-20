from django.db import transaction
from django.db.models import Count
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from .models import Grupo, Membro
from .serializers import EditarMembroSerializer, EntrarGrupoSerializer, GrupoSerializer, MembroSerializer


class GrupoViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    GET  /api/grupos/               meus grupos
    POST /api/grupos/               criar grupo (quem cria vira organizador)
    GET  /api/grupos/{id}/          detalhe (so membros)
    GET  /api/grupos/{id}/membros/  membros do grupo (a nota so aparece para o organizador)
    PATCH /api/grupos/{id}/membros/{membro_id}/  organizador edita {posicao, nota}
    POST /api/grupos/entrar/        entrar com {codigo}
    """

    serializer_class = GrupoSerializer

    def get_queryset(self):
        # So aparecem grupos dos quais o usuario participa: quem nao e membro recebe 404.
        return (
            # filtro via subquery para o Count contar TODOS os membros, nao so o usuario
            Grupo.objects.filter(pk__in=Membro.objects.filter(usuario=self.request.user).values('grupo'))
            .annotate(total_membros=Count('membros', distinct=True))
            .order_by('-criado_em')
        )

    @transaction.atomic
    def perform_create(self, serializer):
        usuario = self.request.user
        grupo = serializer.save(criado_por=usuario)
        Membro.objects.create(
            grupo=grupo, usuario=usuario, papel=Membro.Papel.ORGANIZADOR, posicao=usuario.posicao
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        grupo = self.get_queryset().get(pk=serializer.instance.pk)
        return Response(self.get_serializer(grupo).data, status=status.HTTP_201_CREATED)

    def _sou_organizador(self, grupo):
        return grupo.membros.filter(usuario=self.request.user, papel=Membro.Papel.ORGANIZADOR).exists()

    @action(detail=True)
    def membros(self, request, pk=None):
        grupo = self.get_object()
        membros = grupo.membros.select_related('usuario')
        contexto = {'mostrar_nota': self._sou_organizador(grupo)}
        return Response(MembroSerializer(membros, many=True, context=contexto).data)

    @action(detail=True, methods=['patch'], url_path=r'membros/(?P<membro_id>\d+)')
    def editar_membro(self, request, pk=None, membro_id=None):
        grupo = self.get_object()  # 404 para quem nao e do grupo
        if not self._sou_organizador(grupo):
            raise PermissionDenied('Só o organizador pode editar os jogadores.')
        membro = get_object_or_404(grupo.membros.select_related('usuario'), pk=membro_id)
        edicao = EditarMembroSerializer(membro, data=request.data, partial=True)
        edicao.is_valid(raise_exception=True)
        edicao.save()
        return Response(MembroSerializer(membro, context={'mostrar_nota': True}).data)

    @action(detail=False, methods=['post'])
    def entrar(self, request):
        entrada = EntrarGrupoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        grupo = entrada.validated_data['codigo']
        _, criado = Membro.objects.get_or_create(
            grupo=grupo, usuario=request.user, defaults={'posicao': request.user.posicao}
        )
        dados = self.get_serializer(self.get_queryset().get(pk=grupo.pk)).data
        return Response(dados, status=status.HTTP_201_CREATED if criado else status.HTTP_200_OK)
