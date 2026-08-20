from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from core.cache_decorators import cache_response
from .models import Cliente
from .serializers import ClienteSerializer


class ClienteViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gerenciamento de clientes.

    Endpoints:
    - GET /api/clientes/ - Lista todos os clientes
    - POST /api/clientes/ - Cria um novo cliente
    - GET /api/clientes/{id}/ - Detalha um cliente específico
    - PUT /api/clientes/{id}/ - Atualiza um cliente
    - PATCH /api/clientes/{id}/ - Atualiza parcialmente um cliente
    - DELETE /api/clientes/{id}/ - Remove um cliente
    """

    # Otimização N+1: carregar usuários que criaram/atualizaram
    queryset = Cliente.objects.select_related('created_by', 'updated_by').all()
    serializer_class = ClienteSerializer
    permission_classes = [IsAuthenticated]

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter
    ]

    filterset_fields = ['ativo']
    search_fields = ['nome', 'nome_fantasia', 'cnpj', 'email', 'nome_responsavel']
    ordering_fields = ['nome', 'created_at', 'updated_at']
    ordering = ['nome']

    def perform_create(self, serializer):
        """
        Define o usuário que criou o cliente.
        """
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        """
        Define o usuário que atualizou o cliente.
        """
        serializer.save(updated_by=self.request.user)

    @action(detail=True, methods=['post'])
    def toggle_ativo(self, request, pk=None):
        """
        Ativa/desativa um cliente.
        """
        cliente = self.get_object()
        cliente.ativo = not cliente.ativo
        cliente.updated_by = request.user
        cliente.save()

        serializer = self.get_serializer(cliente)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    @cache_response(timeout=600, key_prefix='clientes_ativos')  # Cache por 10 minutos
    def ativos(self, request):
        """
        Retorna apenas clientes ativos.
        """
        clientes = self.queryset.filter(ativo=True)
        page = self.paginate_queryset(clientes)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(clientes, many=True)
        return Response(serializer.data)


class ClientePublicoListView(APIView):
    """
    View pública para listar clientes ativos (sem autenticação).
    Usado no formulário de abertura de chamados.
    """
    permission_classes = [AllowAny]

    @cache_response(timeout=900, key_prefix='clientes_publico')  # Cache por 15 minutos
    def get(self, request):
        """
        Retorna lista simplificada de clientes ativos.
        """
        clientes = Cliente.objects.filter(ativo=True).order_by('nome')

        # Retorna apenas id, nome e nome_fantasia
        data = [
            {
                'id': cliente.id,
                'nome': cliente.nome,
                'nome_fantasia': cliente.nome_fantasia,
                'cnpj': cliente.cnpj,
            }
            for cliente in clientes
        ]

        return Response(data)
