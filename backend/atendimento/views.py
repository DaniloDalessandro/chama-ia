from accounts.permissions import CanViewOwnTicketsOnly
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import AuditoriaClassificacao, Atendimento, AvaliacaoCriterioAtendimento, MensagemAtendimento
from .permissions import IsAdminOrAtendente
from .serializers import (
    AnexoAtendimentoSerializer,
    AtendimentoDetailPublicSerializer,
    AtendimentoFilaSerializer,
    AtendimentoPublicoCreateSerializer,
    AtendimentoSerializer,
    AuditoriaClassificacaoSerializer,
    AvaliacaoCriterioAtendimentoSerializer,
    EncaminharChamadoInputSerializer,
    MensagemAtendimentoSerializer,
    RegraCriticaAtendimentoSerializer,
    RevisaoHumanaAtendimentoSerializer,
)
from .services.classification_service import NenhumaVersaoAtivaError, ServicePriorityClassificationService
from .services.fila_service import FilaService
from .services.persistence_service import ServicePersistenceService
from .services.ticket_creation_service import TicketCreationService
from .throttling import AtendimentoPublicoConsultaRateThrottle, AtendimentoPublicoRateThrottle


class AtendimentoViewSet(viewsets.ModelViewSet):
    serializer_class = AtendimentoSerializer
    permission_classes = [IsAuthenticated, CanViewOwnTicketsOnly]

    def get_queryset(self):
        user = self.request.user
        qs = Atendimento.objects.all()
        if user.role in ("admin", "atendente"):
            return qs
        return qs.filter(email=user.email)

    def perform_create(self, serializer):
        atendimento = serializer.save(criado_por=self.request.user, atualizado_por=self.request.user)

        from .tasks import analisar_atendimento_ia_task

        analisar_atendimento_ia_task.delay(atendimento.id)

    def perform_update(self, serializer):
        serializer.save(atualizado_por=self.request.user)

    @action(detail=True, methods=["get", "post"])
    def mensagens(self, request, pk=None):
        atendimento = self.get_object()
        if request.method == "GET":
            mensagens = atendimento.mensagens.all()
            return Response(MensagemAtendimentoSerializer(mensagens, many=True).data)

        serializer = MensagemAtendimentoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        mensagem = serializer.save(atendimento=atendimento)

        # Fase 3: mesma regra do consumer WS -- so mensagem de cliente
        # reprocessa a analise (paridade entre o fallback REST e o WS).
        if mensagem.remetente_tipo == MensagemAtendimento.RemetenteTipo.CLIENTE:
            from .tasks import analisar_atendimento_ia_task

            analisar_atendimento_ia_task.delay(atendimento.id, mensagem_id=mensagem.id)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get", "post"], permission_classes=[IsAuthenticated, IsAdminOrAtendente])
    def avaliacoes(self, request, pk=None):
        atendimento = self.get_object()
        if request.method == "GET":
            avaliacoes = atendimento.avaliacoes.all()
            return Response(AvaliacaoCriterioAtendimentoSerializer(avaliacoes, many=True).data)

        criterio_id = request.data.get("criterio")
        existente = AvaliacaoCriterioAtendimento.objects.filter(atendimento=atendimento, criterio_id=criterio_id).first()
        serializer = AvaliacaoCriterioAtendimentoSerializer(instance=existente, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(atendimento=atendimento, atualizado_por=request.user, criado_por=existente.criado_por if existente else request.user)
        return Response(serializer.data, status=status.HTTP_200_OK if existente else status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsAdminOrAtendente])
    def classificar(self, request, pk=None):
        atendimento = self.get_object()
        try:
            resultado = ServicePriorityClassificationService.classify(atendimento)
        except NenhumaVersaoAtivaError as exc:
            raise ValidationError(str(exc)) from exc

        from ahp.services.version_service import AHPVersionService

        versao_ahp = AHPVersionService.get_versao_ativa()
        auditoria = ServicePersistenceService.persist(atendimento, resultado, versao_ahp, user=request.user)
        return Response(AuditoriaClassificacaoSerializer(auditoria).data)

    @action(detail=True, methods=["post"], url_path="revisao-humana", permission_classes=[IsAuthenticated, IsAdminOrAtendente])
    def revisao_humana(self, request, pk=None):
        atendimento = self.get_object()
        serializer = RevisaoHumanaAtendimentoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        prioridade_anterior = atendimento.prioridade
        revisao = serializer.save(atendimento=atendimento, prioridade_anterior=prioridade_anterior, responsavel=request.user)

        atendimento.prioridade = revisao.nova_prioridade
        atendimento.atualizado_por = request.user
        atendimento.save(update_fields=["prioridade", "atualizado_por", "atualizado_em"])

        return Response(RevisaoHumanaAtendimentoSerializer(revisao).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="encaminhar-chamado", permission_classes=[IsAuthenticated, IsAdminOrAtendente])
    def encaminhar_chamado(self, request, pk=None):
        atendimento = self.get_object()
        serializer = EncaminharChamadoInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from chamados.serializers import ChamadoDetailSerializer

        chamado = TicketCreationService.create_from_atendimento(
            atendimento, motivo=serializer.validated_data["motivo"], user=request.user
        )
        return Response(ChamadoDetailSerializer(chamado).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="resolver", permission_classes=[IsAuthenticated, IsAdminOrAtendente])
    def resolver(self, request, pk=None):
        from django.db import transaction

        atendimento = self.get_object()

        status_bloqueados = [
            Atendimento.StatusAtendimento.RESOLVIDO,
            Atendimento.StatusAtendimento.CANCELADO,
        ]
        if atendimento.status_atendimento in status_bloqueados:
            raise ValidationError(
                f"Atendimento ja esta '{atendimento.get_status_atendimento_display()}' e nao pode ser resolvido."
            )

        solucao = (request.data.get("solucao") or "").strip()
        nome_responsavel = getattr(request.user, "name", None) or request.user.email

        with transaction.atomic():
            atendimento.status_atendimento = Atendimento.StatusAtendimento.RESOLVIDO
            atendimento.atualizado_por = request.user
            atendimento.save(update_fields=["status_atendimento", "atualizado_por", "atualizado_em"])

            conteudo_msg = f"Atendimento resolvido por {nome_responsavel}."
            if solucao:
                conteudo_msg += f"\n\nSolucao: {solucao}"

            MensagemAtendimento.objects.create(
                atendimento=atendimento,
                remetente_tipo=MensagemAtendimento.RemetenteTipo.SISTEMA,
                conteudo=conteudo_msg,
            )

        return Response(AtendimentoSerializer(atendimento).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated, IsAdminOrAtendente])
    def fila(self, request):
        fila = FilaService.get_fila_ordenada()
        return Response(AtendimentoFilaSerializer(fila, many=True).data)

    @action(detail=True, methods=["get"], url_path="detalhe", permission_classes=[IsAuthenticated, IsAdminOrAtendente])
    def detalhe(self, request, pk=None):
        from chamados.serializers import ChamadoListSerializer

        atendimento = self.get_object()
        ultima_auditoria = atendimento.auditorias.order_by("-criado_em").first()
        chamado_relacionado = atendimento.chamados_gerados.order_by("-created_at").first()
        regra_critica = getattr(atendimento, "regra_critica", None)

        return Response({
            "atendimento": AtendimentoSerializer(atendimento).data,
            "conversa": MensagemAtendimentoSerializer(atendimento.mensagens.all(), many=True).data,
            "anexos": AnexoAtendimentoSerializer(atendimento.anexos.all(), many=True).data,
            "avaliacoes_criterios": AvaliacaoCriterioAtendimentoSerializer(atendimento.avaliacoes.all(), many=True).data,
            "auditoria_mais_recente": AuditoriaClassificacaoSerializer(ultima_auditoria).data if ultima_auditoria else None,
            "regra_critica": RegraCriticaAtendimentoSerializer(regra_critica).data if regra_critica else None,
            "revisoes_humanas": RevisaoHumanaAtendimentoSerializer(atendimento.revisoes.all(), many=True).data,
            "chamado_relacionado": ChamadoListSerializer(chamado_relacionado).data if chamado_relacionado else None,
        })


class AuditoriaClassificacaoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditoriaClassificacao.objects.all()
    serializer_class = AuditoriaClassificacaoSerializer
    permission_classes = [IsAuthenticated, IsAdminOrAtendente]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["atendimento"]


class AtendimentoPublicoCreateView(generics.CreateAPIView):
    """
    Criacao anonima de atendimento (chat publico) -- POST /publico/.
    Nunca aceita `origem` do cliente; devolve `session_token`, a unica prova
    de propriedade que o cliente anonimo tera dai em diante (nunca o pk).
    """

    serializer_class = AtendimentoPublicoCreateSerializer
    permission_classes = [AllowAny]
    throttle_classes = [AtendimentoPublicoRateThrottle]

    def perform_create(self, serializer):
        serializer.save(origem=Atendimento.Origem.CHAT)
        atendimento = serializer.instance

        mensagem_inicial = serializer.validated_data.get("mensagem_inicial", "")
        if mensagem_inicial:
            MensagemAtendimento.objects.create(
                atendimento=atendimento,
                remetente_tipo=MensagemAtendimento.RemetenteTipo.CLIENTE,
                conteudo=mensagem_inicial,
            )

        from .tasks import analisar_atendimento_ia_task

        analisar_atendimento_ia_task.delay(atendimento.id)


class AtendimentoPublicoDetailView(generics.RetrieveAPIView):
    """GET /publico/<session_token>/ -- lookup so por token, nunca por pk."""

    serializer_class = AtendimentoDetailPublicSerializer
    permission_classes = [AllowAny]
    throttle_classes = [AtendimentoPublicoConsultaRateThrottle]
    lookup_field = "session_token"
    lookup_url_kwarg = "session_token"
    queryset = Atendimento.objects.all()


class AtendimentoPublicoMensagensView(generics.ListAPIView):
    """GET /publico/<session_token>/mensagens/ -- fallback de polling se o WS cair."""

    serializer_class = MensagemAtendimentoSerializer
    permission_classes = [AllowAny]
    throttle_classes = [AtendimentoPublicoConsultaRateThrottle]

    def get_queryset(self):
        atendimento = get_object_or_404(Atendimento, session_token=self.kwargs["session_token"])
        return atendimento.mensagens.all()
