from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Q
import logging

from .models import Chamado, AnexoChamado, ComentarioChamado, HistoricoChamado
from .serializers import (
    ChamadoPublicoCreateSerializer,
    ChamadoPublicoResponseSerializer,
    ChamadoListSerializer,
    ChamadoDetailSerializer,
    ChamadoUpdateStatusSerializer,
    ChamadoAtribuirAtendenteSerializer,
    ChamadoUpdatePrioridadeSerializer,
    ChamadoConsultaPublicaSerializer,
    ComentarioCreateSerializer,
    ComentarioChamadoSerializer,
    AnexoChamadoSerializer,
    AnexoUploadSerializer,
)
from .throttling import ChamadoPublicoRateThrottle

logger = logging.getLogger(__name__)


# ============================================
# Views Publicas (Landing Page)
# ============================================

class ChamadoPublicoCreateView(generics.CreateAPIView):
    """
    Endpoint publico para criacao de chamados via Landing Page.

    POST /api/v1/chamados/publico/

    Aceita multipart/form-data para upload de anexos.
    Rate limited para evitar spam.
    """

    serializer_class = ChamadoPublicoCreateSerializer
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    throttle_classes = [ChamadoPublicoRateThrottle]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
            chamado = serializer.save()

            # Log de sucesso
            logger.info(
                f"Chamado criado: {chamado.protocolo} - "
                f"Email: {chamado.email} - "
                f"IP: {chamado.ip_address}"
            )

            # Retornar dados minimos
            response_serializer = ChamadoPublicoResponseSerializer(chamado)
            return Response(
                {
                    "success": True,
                    "message": "Chamado criado com sucesso!",
                    "data": response_serializer.data
                },
                status=status.HTTP_201_CREATED
            )

        except Exception as e:
            logger.error(f"Erro ao criar chamado: {str(e)}")
            return Response(
                {
                    "success": False,
                    "message": "Erro ao criar chamado. Tente novamente.",
                    "errors": serializer.errors if hasattr(serializer, 'errors') else str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )


class ChamadoConsultaPublicaView(generics.RetrieveAPIView):
    """
    Endpoint publico para consulta de chamado por protocolo.

    GET /api/v1/chamados/publico/consulta/?protocolo=XXXXXXXX-XXXXX&email=xxx@xxx.com

    Requer protocolo E email para validacao.
    """

    serializer_class = ChamadoConsultaPublicaSerializer
    permission_classes = [AllowAny]
    throttle_classes = [ChamadoPublicoRateThrottle]

    def get_object(self):
        protocolo = self.request.query_params.get("protocolo", "").strip().upper()
        email = self.request.query_params.get("email", "").strip().lower()

        if not protocolo or not email:
            return None

        try:
            return Chamado.objects.get(protocolo=protocolo, email=email)
        except Chamado.DoesNotExist:
            return None

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()

        if not instance:
            return Response(
                {
                    "success": False,
                    "message": "Chamado nao encontrado. Verifique o protocolo e email."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = self.get_serializer(instance)
        return Response({
            "success": True,
            "data": serializer.data
        })


# ============================================
# Views Administrativas (Autenticadas)
# ============================================

class ChamadoAdminViewSet(viewsets.ModelViewSet):
    """
    ViewSet completo para gerenciamento de chamados (admin).

    GET /api/v1/chamados/ - Listar chamados
    GET /api/v1/chamados/{id}/ - Detalhes do chamado
    PATCH /api/v1/chamados/{id}/status/ - Atualizar status
    PATCH /api/v1/chamados/{id}/prioridade/ - Atualizar prioridade
    PATCH /api/v1/chamados/{id}/atribuir/ - Atribuir atendente
    POST /api/v1/chamados/{id}/comentario/ - Adicionar comentario
    POST /api/v1/chamados/{id}/anexo/ - Adicionar anexo
    """

    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["protocolo", "nome", "email", "assunto", "descricao"]
    ordering_fields = ["created_at", "updated_at", "prioridade", "status"]
    ordering = ["-created_at"]

    def get_queryset(self):
        queryset = Chamado.objects.select_related("usuario", "atendente")

        # Filtros
        status_filter = self.request.query_params.get("status")
        prioridade_filter = self.request.query_params.get("prioridade")
        tipo_filter = self.request.query_params.get("tipo")
        atendente_filter = self.request.query_params.get("atendente")
        origem_filter = self.request.query_params.get("origem")

        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if prioridade_filter:
            queryset = queryset.filter(prioridade=prioridade_filter)
        if tipo_filter:
            queryset = queryset.filter(tipo=tipo_filter)
        if atendente_filter:
            if atendente_filter == "null":
                queryset = queryset.filter(atendente__isnull=True)
            else:
                queryset = queryset.filter(atendente_id=atendente_filter)
        if origem_filter:
            queryset = queryset.filter(origem=origem_filter)

        # Filtro por periodo
        data_inicio = self.request.query_params.get("data_inicio")
        data_fim = self.request.query_params.get("data_fim")

        if data_inicio:
            queryset = queryset.filter(created_at__date__gte=data_inicio)
        if data_fim:
            queryset = queryset.filter(created_at__date__lte=data_fim)

        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return ChamadoListSerializer
        elif self.action == "retrieve":
            return ChamadoDetailSerializer
        elif self.action == "update_status":
            return ChamadoUpdateStatusSerializer
        elif self.action == "update_prioridade":
            return ChamadoUpdatePrioridadeSerializer
        elif self.action == "atribuir_atendente":
            return ChamadoAtribuirAtendenteSerializer
        elif self.action == "add_comentario":
            return ComentarioCreateSerializer
        elif self.action == "add_anexo":
            return AnexoUploadSerializer
        return ChamadoDetailSerializer

    @action(detail=True, methods=["patch"], url_path="status")
    def update_status(self, request, pk=None):
        """Atualizar status do chamado."""
        chamado = self.get_object()
        serializer = self.get_serializer(chamado, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({
            "success": True,
            "message": "Status atualizado com sucesso!",
            "data": ChamadoDetailSerializer(chamado, context={"request": request}).data
        })

    @action(detail=True, methods=["patch"], url_path="prioridade")
    def update_prioridade(self, request, pk=None):
        """Atualizar prioridade do chamado."""
        chamado = self.get_object()
        serializer = self.get_serializer(chamado, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({
            "success": True,
            "message": "Prioridade atualizada com sucesso!",
            "data": ChamadoDetailSerializer(chamado, context={"request": request}).data
        })

    @action(detail=True, methods=["patch"], url_path="atribuir")
    def atribuir_atendente(self, request, pk=None):
        """Atribuir atendente ao chamado."""
        chamado = self.get_object()
        serializer = self.get_serializer(chamado, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({
            "success": True,
            "message": "Atendente atribuido com sucesso!",
            "data": ChamadoDetailSerializer(chamado, context={"request": request}).data
        })

    @action(detail=True, methods=["post"], url_path="comentario")
    def add_comentario(self, request, pk=None):
        """Adicionar comentario ao chamado."""
        chamado = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        comentario = ComentarioChamado.objects.create(
            chamado=chamado,
            tipo=serializer.validated_data.get("tipo", ComentarioChamado.TipoComentario.PUBLICO),
            conteudo=serializer.validated_data["conteudo"],
            autor=request.user,
            autor_nome=request.user.name,
        )

        # Registrar no historico
        HistoricoChamado.objects.create(
            chamado=chamado,
            tipo_acao=HistoricoChamado.TipoAcao.COMENTARIO,
            descricao=f"Comentario adicionado por {request.user.name}",
            usuario=request.user,
        )

        return Response({
            "success": True,
            "message": "Comentario adicionado com sucesso!",
            "data": ComentarioChamadoSerializer(comentario).data
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="anexo", parser_classes=[MultiPartParser, FormParser])
    def add_anexo(self, request, pk=None):
        """Adicionar anexo ao chamado."""
        chamado = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        arquivo = serializer.validated_data["arquivo"]

        # Determinar tipo
        if arquivo.content_type == "application/pdf":
            tipo = AnexoChamado.TipoArquivo.PDF
        elif arquivo.content_type.startswith("image/"):
            tipo = AnexoChamado.TipoArquivo.IMAGEM
        else:
            tipo = AnexoChamado.TipoArquivo.OUTRO

        anexo = AnexoChamado.objects.create(
            chamado=chamado,
            arquivo=arquivo,
            nome_original=arquivo.name,
            tipo=tipo,
            tamanho=arquivo.size,
            mime_type=arquivo.content_type,
        )

        # Registrar no historico
        HistoricoChamado.objects.create(
            chamado=chamado,
            tipo_acao=HistoricoChamado.TipoAcao.ANEXO_ADICIONADO,
            descricao=f"Anexo adicionado: {arquivo.name}",
            usuario=request.user,
        )

        return Response({
            "success": True,
            "message": "Anexo adicionado com sucesso!",
            "data": AnexoChamadoSerializer(anexo, context={"request": request}).data
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"], url_path="estatisticas")
    def estatisticas(self, request):
        """Retornar estatisticas dos chamados."""
        from django.db.models import Count
        from django.utils import timezone
        from datetime import timedelta

        hoje = timezone.now().date()
        inicio_semana = hoje - timedelta(days=hoje.weekday())
        inicio_mes = hoje.replace(day=1)

        stats = {
            "total": Chamado.objects.count(),
            "abertos": Chamado.objects.filter(status=Chamado.Status.ABERTO).count(),
            "em_atendimento": Chamado.objects.filter(
                status__in=[Chamado.Status.EM_ANALISE, Chamado.Status.EM_ATENDIMENTO]
            ).count(),
            "resolvidos_hoje": Chamado.objects.filter(
                resolved_at__date=hoje
            ).count(),
            "criados_hoje": Chamado.objects.filter(
                created_at__date=hoje
            ).count(),
            "criados_semana": Chamado.objects.filter(
                created_at__date__gte=inicio_semana
            ).count(),
            "criados_mes": Chamado.objects.filter(
                created_at__date__gte=inicio_mes
            ).count(),
            "por_status": list(
                Chamado.objects.values("status")
                .annotate(count=Count("id"))
                .order_by("status")
            ),
            "por_prioridade": list(
                Chamado.objects.values("prioridade")
                .annotate(count=Count("id"))
                .order_by("prioridade")
            ),
            "por_tipo": list(
                Chamado.objects.values("tipo")
                .annotate(count=Count("id"))
                .order_by("tipo")
            ),
        }

        return Response({
            "success": True,
            "data": stats
        })
