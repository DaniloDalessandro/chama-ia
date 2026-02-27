from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from accounts.permissions import CanViewOwnTicketsOnly
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
from core.cache_decorators import cache_response
import logging

from .models import Chamado, AnexoChamado, ComentarioChamado, HistoricoChamado, Notification, WebhookConfig
from .serializers import (
    ChamadoPublicoCreateSerializer,
    ChamadoPublicoCreateResponseSerializer,
    ChamadoPublicoResponseSerializer,
    ChamadoListSerializer,
    ChamadoDetailSerializer,
    ChamadoUpdateStatusSerializer,
    ChamadoUpdateStatusKanbanSerializer,
    ChamadoAtribuirAtendenteSerializer,
    ChamadoUpdatePrioridadeSerializer,
    ChamadoConsultaPublicaSerializer,
    ChamadoConsultaProtocoloDetailSerializer,
    ChamadoListaPorEmailSerializer,
    ComentarioCreateSerializer,
    ComentarioChamadoSerializer,
    AnexoChamadoSerializer,
    AnexoUploadSerializer,
    NotificationSerializer,
    WebhookConfigSerializer,
)
from .throttling import ChamadoPublicoRateThrottle, ChamadoPublicoProcessarIARateThrottle

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

            logger.info(
                f"Chamado criado: {chamado.protocolo} - "
                f"Email: {chamado.email} - "
                f"IP: {chamado.ip_address}"
            )

            # Enviar e-mail de confirmacao via Celery (async)
            try:
                from chamados.tasks import enviar_email_confirmacao_task
                enviar_email_confirmacao_task.delay(chamado.id)
            except Exception as email_error:
                logger.warning(f"Falha ao despachar task de e-mail: {email_error}")
                # Fallback sincrono
                try:
                    from chamados.services.email_service import enviar_email_confirmacao_chamado
                    enviar_email_confirmacao_chamado(chamado)
                except Exception:
                    pass

            response_serializer = ChamadoPublicoCreateResponseSerializer(chamado)
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


class ChamadoConsultaProtocoloView(generics.RetrieveAPIView):
    """
    Endpoint publico para consulta detalhada de chamado por protocolo.

    GET /api/v1/chamados/publico/consulta-protocolo/?protocolo=0001/2026

    Retorna dados completos do chamado incluindo historico e anexos.
    """

    serializer_class = ChamadoConsultaProtocoloDetailSerializer
    permission_classes = [AllowAny]
    throttle_classes = [ChamadoPublicoRateThrottle]

    def get_object(self):
        protocolo = self.request.query_params.get("protocolo", "").strip().upper()

        if not protocolo:
            return None

        try:
            return Chamado.objects.prefetch_related(
                "comentarios", "anexos", "historico"
            ).get(protocolo=protocolo)
        except Chamado.DoesNotExist:
            return None

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()

        if not instance:
            return Response(
                {
                    "success": False,
                    "message": "Chamado nao encontrado. Verifique o numero do protocolo."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = self.get_serializer(instance)
        return Response({
            "success": True,
            "data": serializer.data
        })


class ChamadoListarPorEmailView(generics.ListAPIView):
    """
    Endpoint publico para listar chamados por e-mail.

    GET /api/v1/chamados/publico/consulta-email/?email=usuario@email.com

    Retorna lista resumida de todos os chamados do e-mail informado.
    """

    serializer_class = ChamadoListaPorEmailSerializer
    permission_classes = [AllowAny]
    throttle_classes = [ChamadoPublicoRateThrottle]

    def get_queryset(self):
        email = self.request.query_params.get("email", "").strip().lower()
        if not email:
            return Chamado.objects.none()
        return Chamado.objects.filter(email=email).order_by("-created_at")

    def list(self, request, *args, **kwargs):
        email = request.query_params.get("email", "").strip().lower()

        if not email:
            return Response(
                {
                    "success": False,
                    "message": "Informe o e-mail para consulta."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        queryset = self.get_queryset()

        if not queryset.exists():
            return Response(
                {
                    "success": False,
                    "message": "Nenhum chamado encontrado para este e-mail."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "success": True,
            "total": queryset.count(),
            "data": serializer.data
        })


class ChamadoPublicoProcessarIAView(generics.GenericAPIView):
    """
    Endpoint publico para processar chamado com IA (segunda fase).

    POST /api/v1/chamados/publico/<int:chamado_id>/processar-ia/

    Chamado ja foi salvo; agora processa classificacao + busca similar.
    """

    permission_classes = [AllowAny]
    throttle_classes = [ChamadoPublicoProcessarIARateThrottle]

    def post(self, request, chamado_id):
        logger.info(f"Processar IA chamado_id={chamado_id} - inicio")

        try:
            chamado = Chamado.objects.get(id=chamado_id)
        except Chamado.DoesNotExist:
            logger.warning(f"Processar IA chamado_id={chamado_id} - nao encontrado")
            return Response(
                {"success": False, "message": "Chamado nao encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Se ja processado, retornar resultado existente
        if chamado.ia_processed:
            logger.info(f"Chamado {chamado.protocolo} ja processado, retornando cache")
            return self._build_response(chamado)

        # Tentar despachar via Celery (async)
        try:
            from chamados.tasks import processar_chamado_ia_async_task

            logger.info(f"Despachando processamento IA async para chamado {chamado.protocolo}")
            processar_chamado_ia_async_task.delay(chamado.id)

            return Response(
                {
                    "success": True,
                    "message": "Processamento IA iniciado. Consulte o status em breve.",
                    "data": {
                        "id": chamado.id,
                        "protocolo": chamado.protocolo,
                        "status": chamado.status,
                        "ia_processed": False,
                    },
                },
                status=status.HTTP_202_ACCEPTED,
            )

        except Exception as e:
            logger.warning(f"Celery indisponivel, processando sincronamente: {e}")
            # Fallback sincrono se Celery nao disponivel
            try:
                from chamados.services.ia_classifier import processar_chamado_completo

                resultado = processar_chamado_completo(chamado.id)

                if not resultado["success"]:
                    return Response(
                        {"success": False, "message": "Erro no processamento IA."},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )

                chamado.refresh_from_db()

                if not chamado.is_recorrente:
                    chamado.status = Chamado.Status.EM_ANALISE
                    chamado.save()

                return self._build_response(chamado)

            except Exception as sync_error:
                logger.error(f"Erro ao processar IA para chamado {chamado.protocolo}: {sync_error}")
                return Response(
                    {"success": False, "message": "Servico de IA indisponivel no momento."},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )

    def _build_response(self, chamado):
        data = {
            "id": chamado.id,
            "protocolo": chamado.protocolo,
            "status": chamado.status,
            "ia_processed": chamado.ia_processed,
            "ia_categoria": chamado.ia_categoria,
            "ia_prioridade_sugerida": chamado.ia_prioridade_sugerida,
            "ia_resumo": chamado.ia_resumo,
            "ia_confianca": chamado.ia_confianca,
            "is_recorrente": chamado.is_recorrente,
            "similaridade_score": chamado.similaridade_score,
            "solucao_similar": None,
        }

        # Se encontrou chamado similar resolvido, incluir dados da solucao
        if chamado.is_recorrente and chamado.chamado_similar_ref_id:
            try:
                similar = Chamado.objects.get(id=chamado.chamado_similar_ref_id)
                comentarios_publicos = list(
                    similar.comentarios.filter(
                        tipo=ComentarioChamado.TipoComentario.PUBLICO
                    ).values("id", "conteudo", "autor_nome", "created_at")
                )
                data["solucao_similar"] = {
                    "id": similar.id,
                    "protocolo": similar.protocolo,
                    "assunto": similar.assunto,
                    "status": similar.status,
                    "ia_resumo": similar.ia_resumo,
                    "resolved_at": similar.resolved_at.isoformat() if similar.resolved_at else None,
                    "comentarios_publicos": comentarios_publicos,
                }
            except Chamado.DoesNotExist:
                pass

        return Response({"success": True, "data": data})


class ChamadoPublicoStatusIAView(generics.GenericAPIView):
    """
    Endpoint publico para consultar status do processamento IA.

    GET /api/v1/chamados/publico/<int:chamado_id>/status-ia/

    Usado pelo frontend para polling apos despacho async.
    Retorna ia_processed=true quando o processamento concluiu.
    """

    permission_classes = [AllowAny]
    throttle_classes = [ChamadoPublicoRateThrottle]

    def get(self, request, chamado_id):
        try:
            chamado = Chamado.objects.get(id=chamado_id)
        except Chamado.DoesNotExist:
            return Response(
                {"success": False, "message": "Chamado nao encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not chamado.ia_processed:
            return Response({
                "success": True,
                "data": {
                    "id": chamado.id,
                    "protocolo": chamado.protocolo,
                    "status": chamado.status,
                    "ia_processed": False,
                },
            })

        # Ja processado — retornar dados completos (reutiliza logica do _build_response)
        data = {
            "id": chamado.id,
            "protocolo": chamado.protocolo,
            "status": chamado.status,
            "ia_processed": chamado.ia_processed,
            "ia_categoria": chamado.ia_categoria,
            "ia_prioridade_sugerida": chamado.ia_prioridade_sugerida,
            "ia_resumo": chamado.ia_resumo,
            "ia_confianca": chamado.ia_confianca,
            "is_recorrente": chamado.is_recorrente,
            "similaridade_score": chamado.similaridade_score,
            "solucao_similar": None,
        }

        if chamado.is_recorrente and chamado.chamado_similar_ref_id:
            try:
                similar = Chamado.objects.get(id=chamado.chamado_similar_ref_id)
                comentarios_publicos = list(
                    similar.comentarios.filter(
                        tipo=ComentarioChamado.TipoComentario.PUBLICO
                    ).values("id", "conteudo", "autor_nome", "created_at")
                )
                data["solucao_similar"] = {
                    "id": similar.id,
                    "protocolo": similar.protocolo,
                    "assunto": similar.assunto,
                    "status": similar.status,
                    "ia_resumo": similar.ia_resumo,
                    "resolved_at": similar.resolved_at.isoformat() if similar.resolved_at else None,
                    "comentarios_publicos": comentarios_publicos,
                }
            except Chamado.DoesNotExist:
                pass

        return Response({"success": True, "data": data})


# ============================================
# Views Administrativas (Autenticadas)
# ============================================

class ChamadoAdminViewSet(viewsets.ModelViewSet):
    """
    ViewSet completo para gerenciamento de chamados com controle de permissões.

    Regras de acesso:
    - Admin: Vê todos os chamados
    - Atendente: Vê todos os chamados
    - Cliente: Vê apenas seus próprios chamados (pelo e-mail)

    GET /api/v1/chamados/ - Listar chamados
    GET /api/v1/chamados/{id}/ - Detalhes do chamado
    PATCH /api/v1/chamados/{id}/status/ - Atualizar status
    PATCH /api/v1/chamados/{id}/prioridade/ - Atualizar prioridade
    PATCH /api/v1/chamados/{id}/atribuir/ - Atribuir atendente
    POST /api/v1/chamados/{id}/comentario/ - Adicionar comentario
    POST /api/v1/chamados/{id}/anexo/ - Adicionar anexo
    """

    permission_classes = [IsAuthenticated, CanViewOwnTicketsOnly]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["protocolo", "nome", "email", "assunto", "descricao"]
    ordering_fields = ["created_at", "updated_at", "prioridade", "status"]
    ordering = ["-created_at"]

    def get_queryset(self):
        # Otimização N+1: select_related para ForeignKeys, prefetch_related para Many-to-Many e reverse FKs
        queryset = Chamado.objects.select_related(
            "usuario",
            "atendente",
            "cliente",
            "created_by",
            "updated_by",
            "chamado_similar_ref"
        ).prefetch_related(
            "anexos",
            "comentarios__usuario",
            "historico__usuario"
        )

        # CONTROLE DE ACESSO POR ROLE
        user = self.request.user

        # Admin e Atendente veem todos os chamados
        if user.role in ["admin", "atendente"]:
            pass  # Queryset completo
        # Cliente vê apenas seus próprios chamados
        elif user.role == "cliente":
            queryset = queryset.filter(email=user.email)

        # Filtros
        status_filter = self.request.query_params.get("status")
        status_kanban_filter = self.request.query_params.get("status_kanban")
        prioridade_filter = self.request.query_params.get("prioridade")
        tipo_filter = self.request.query_params.get("tipo")
        atendente_filter = self.request.query_params.get("atendente")
        origem_filter = self.request.query_params.get("origem")

        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if status_kanban_filter:
            queryset = queryset.filter(status_kanban=status_kanban_filter)
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

        # Excluir chamados concluidos ha mais de 30 dias da listagem principal
        if self.action == "list":
            cutoff = timezone.now() - timedelta(days=30)
            queryset = queryset.exclude(
                status_kanban="concluido",
                resolved_at__lt=cutoff,
            )

        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return ChamadoListSerializer
        elif self.action == "retrieve":
            return ChamadoDetailSerializer
        elif self.action == "update_status":
            return ChamadoUpdateStatusSerializer
        elif self.action == "update_status_kanban":
            return ChamadoUpdateStatusKanbanSerializer
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

    @action(detail=True, methods=["patch"], url_path="status-kanban")
    def update_status_kanban(self, request, pk=None):
        """Atualizar status Kanban do chamado (drag and drop)."""
        chamado = self.get_object()
        serializer = self.get_serializer(chamado, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({
            "success": True,
            "message": "Status atualizado com sucesso!",
            "data": ChamadoListSerializer(chamado, context={"request": request}).data
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
    @cache_response(timeout=300, key_prefix='chamados_stats')  # Cache por 5 minutos
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

    @action(detail=True, methods=["post"], url_path="processar-ia")
    def processar_ia(self, request, pk=None):
        """
        Processar/reprocessar chamado com IA.

        POST /api/v1/chamados/{id}/processar-ia/

        Dispara processamento assincrono com GPT-4 para:
        - Classificar categoria
        - Sugerir prioridade
        - Gerar resumo
        - Detectar chamados similares
        """
        chamado = self.get_object()

        try:
            from chamados.tasks import processar_chamado_ia_task

            # Disparar task assincrona
            task = processar_chamado_ia_task.delay(chamado.id)

            return Response({
                "success": True,
                "message": "Processamento IA iniciado",
                "data": {
                    "task_id": task.id,
                    "chamado_id": chamado.id,
                    "protocolo": chamado.protocolo,
                }
            })
        except Exception as e:
            # Se Celery nao estiver disponivel, processar sincronamente
            try:
                from chamados.services.ia_classifier import processar_chamado_completo
                resultado = processar_chamado_completo(chamado.id)

                if resultado["success"]:
                    chamado.refresh_from_db()
                    message = "Processamento IA concluido"
                    if resultado.get("prioridade_auto_aplicada"):
                        message += " - Prioridade URGENTE aplicada automaticamente (chamado financeiro)"
                    return Response({
                        "success": True,
                        "message": message,
                        "data": ChamadoDetailSerializer(chamado, context={"request": request}).data,
                        "prioridade_auto_aplicada": resultado.get("prioridade_auto_aplicada", False),
                    })
                else:
                    return Response({
                        "success": False,
                        "message": resultado.get("error", "Erro ao processar chamado")
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            except Exception as e2:
                logger.error(f"Erro ao processar chamado {chamado.id} com IA: {e2}")
                return Response({
                    "success": False,
                    "message": f"Erro ao processar chamado: {str(e2)}"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=["post"], url_path="aplicar-classificacao-ia")
    def aplicar_classificacao_ia(self, request, pk=None):
        """
        Aplicar a prioridade sugerida pela IA ao chamado.

        POST /api/v1/chamados/{id}/aplicar-classificacao-ia/

        Atualiza a prioridade do chamado para a prioridade sugerida pela IA.
        """
        chamado = self.get_object()

        if not chamado.ia_processed:
            return Response({
                "success": False,
                "message": "Chamado ainda nao foi processado pela IA"
            }, status=status.HTTP_400_BAD_REQUEST)

        if not chamado.ia_prioridade_sugerida:
            return Response({
                "success": False,
                "message": "Nao ha prioridade sugerida pela IA"
            }, status=status.HTTP_400_BAD_REQUEST)

        old_prioridade = chamado.prioridade
        chamado.prioridade = chamado.ia_prioridade_sugerida
        chamado.save()

        # Registrar no historico
        HistoricoChamado.objects.create(
            chamado=chamado,
            tipo_acao=HistoricoChamado.TipoAcao.PRIORIDADE_ALTERADA,
            descricao=f"Prioridade alterada de {dict(Chamado.Prioridade.choices).get(old_prioridade)} para {dict(Chamado.Prioridade.choices).get(chamado.prioridade)} (aplicada da sugestao IA)",
            valor_anterior=old_prioridade,
            valor_novo=chamado.prioridade,
            usuario=request.user if request.user.is_authenticated else None,
        )

        return Response({
            "success": True,
            "message": "Prioridade sugerida pela IA aplicada com sucesso",
            "data": ChamadoDetailSerializer(chamado, context={"request": request}).data
        })

    @action(detail=False, methods=["get"], url_path="historico")
    def historico(self, request):
        """Listar chamados concluidos ha mais de 30 dias (historico)."""
        cutoff = timezone.now() - timedelta(days=30)
        queryset = Chamado.objects.select_related(
            "usuario", "atendente", "created_by", "updated_by"
        ).filter(
            status_kanban="concluido",
            resolved_at__lt=cutoff,
        )

        # Busca
        search = request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                Q(protocolo__icontains=search)
                | Q(nome__icontains=search)
                | Q(email__icontains=search)
                | Q(assunto__icontains=search)
            )

        # Ordenacao
        ordering = request.query_params.get("ordering", "-resolved_at")
        allowed_ordering = ["resolved_at", "-resolved_at", "created_at", "-created_at", "protocolo", "-protocolo"]
        if ordering in allowed_ordering:
            queryset = queryset.order_by(ordering)
        else:
            queryset = queryset.order_by("-resolved_at")

        serializer = ChamadoListSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data)


# ============================================
# Views de Notificacoes
# ============================================

class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para notificacoes em tempo real.

    Endpoints:
    - GET /api/v1/notifications/ - Listar notificacoes do usuario
    - GET /api/v1/notifications/{id}/ - Detalhes de notificacao
    - POST /api/v1/notifications/{id}/mark_read/ - Marcar como lida
    - POST /api/v1/notifications/mark_all_read/ - Marcar todas como lidas
    - GET /api/v1/notifications/unread_count/ - Contador de nao lidas
    """

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Retorna apenas notificacoes do usuario autenticado."""
        return Notification.objects.filter(
            user=self.request.user
        ).select_related("chamado").order_by("-created_at")

    @action(detail=True, methods=["post"], url_path="mark-read")
    def mark_read(self, request, pk=None):
        """Marca uma notificacao como lida."""
        from chamados.services.notification_service import NotificationService

        success = NotificationService.mark_as_read(pk, request.user)

        if success:
            return Response({
                "success": True,
                "message": "Notificacao marcada como lida"
            })
        else:
            return Response({
                "success": False,
                "message": "Notificacao nao encontrada"
            }, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=["post"], url_path="mark-all-read")
    def mark_all_read(self, request):
        """Marca todas as notificacoes do usuario como lidas."""
        from chamados.services.notification_service import NotificationService

        count = NotificationService.mark_all_as_read(request.user)

        return Response({
            "success": True,
            "count": count,
            "message": f"{count} notificacoes marcadas como lidas"
        })

    @action(detail=False, methods=["get"], url_path="unread-count")
    def unread_count(self, request):
        """Retorna a quantidade de notificacoes nao lidas."""
        from chamados.services.notification_service import NotificationService

        count = NotificationService.get_unread_count(request.user)

        return Response({
            "count": count
        })


# ============================================
# Views de Webhooks
# ============================================

class WebhookConfigViewSet(viewsets.ModelViewSet):
    """
    ViewSet para configuracao de webhooks.
    Apenas admins podem gerenciar webhooks.

    Endpoints:
    - GET /api/v1/webhooks/ - Listar webhooks
    - POST /api/v1/webhooks/ - Criar webhook
    - GET /api/v1/webhooks/{id}/ - Detalhes do webhook
    - PUT/PATCH /api/v1/webhooks/{id}/ - Atualizar webhook
    - DELETE /api/v1/webhooks/{id}/ - Deletar webhook
    """

    serializer_class = WebhookConfigSerializer
    permission_classes = [IsAuthenticated]
    queryset = WebhookConfig.objects.all().order_by("name")

    def get_queryset(self):
        """Apenas admins podem ver webhooks."""
        if not self.request.user.is_staff:
            return WebhookConfig.objects.none()
        return super().get_queryset()

    def perform_create(self, serializer):
        """Apenas admins podem criar webhooks."""
        if not self.request.user.is_staff:
            raise PermissionError("Apenas administradores podem criar webhooks")
        serializer.save()

    def perform_update(self, serializer):
        """Apenas admins podem atualizar webhooks."""
        if not self.request.user.is_staff:
            raise PermissionError("Apenas administradores podem atualizar webhooks")
        serializer.save()

    def perform_destroy(self, instance):
        """Apenas admins podem deletar webhooks."""
        if not self.request.user.is_staff:
            raise PermissionError("Apenas administradores podem deletar webhooks")
        instance.delete()
