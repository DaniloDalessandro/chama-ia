from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import (
    AtendimentoPublicoCreateView,
    AtendimentoPublicoDetailView,
    AtendimentoPublicoMensagensView,
    AtendimentoViewSet,
    AuditoriaClassificacaoViewSet,
)

router = SimpleRouter(trailing_slash=False)
router.register(r"atendimentos", AtendimentoViewSet, basename="atendimento")
router.register(r"auditorias", AuditoriaClassificacaoViewSet, basename="auditoria-classificacao")

urlpatterns = [
    path("publico/", AtendimentoPublicoCreateView.as_view(), name="atendimento-publico-create"),
    path("publico", AtendimentoPublicoCreateView.as_view(), name="atendimento-publico-create-no-slash"),
    path("publico/<uuid:session_token>/", AtendimentoPublicoDetailView.as_view(), name="atendimento-publico-detail"),
    path("publico/<uuid:session_token>", AtendimentoPublicoDetailView.as_view(), name="atendimento-publico-detail-no-slash"),
    path(
        "publico/<uuid:session_token>/mensagens/",
        AtendimentoPublicoMensagensView.as_view(),
        name="atendimento-publico-mensagens",
    ),
    path(
        "publico/<uuid:session_token>/mensagens",
        AtendimentoPublicoMensagensView.as_view(),
        name="atendimento-publico-mensagens-no-slash",
    ),
] + router.urls
