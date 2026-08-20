from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ChamadoPublicoCreateView,
    ChamadoConsultaPublicaView,
    ChamadoConsultaProtocoloView,
    ChamadoListarPorEmailView,
    ChamadoPublicoProcessarIAView,
    ChamadoPublicoStatusIAView,
    ChamadoAdminViewSet,
    NotificationViewSet,
    WebhookConfigViewSet,
)

router = DefaultRouter(trailing_slash=False)
# Specific prefixes MUST be registered before the empty-prefix viewset,
# otherwise ChamadoAdminViewSet's detail pattern ^(?P<pk>[^/.]+)$ would
# shadow "notifications" and "webhooks" by matching them as pk values.
router.register(r"notifications", NotificationViewSet, basename="notification")
router.register(r"webhooks", WebhookConfigViewSet, basename="webhook")
router.register(r"", ChamadoAdminViewSet, basename="chamado")

urlpatterns = [
    # Endpoints publicos (sem autenticacao)
    path("publico/", ChamadoPublicoCreateView.as_view(), name="chamado-publico-create"),
    path("publico", ChamadoPublicoCreateView.as_view(), name="chamado-publico-create-no-slash"),
    path("publico/consulta/", ChamadoConsultaPublicaView.as_view(), name="chamado-publico-consulta"),
    path("publico/consulta", ChamadoConsultaPublicaView.as_view(), name="chamado-publico-consulta-no-slash"),
    path("publico/consulta-protocolo/", ChamadoConsultaProtocoloView.as_view(), name="chamado-consulta-protocolo"),
    path("publico/consulta-protocolo", ChamadoConsultaProtocoloView.as_view(), name="chamado-consulta-protocolo-no-slash"),
    path("publico/consulta-email/", ChamadoListarPorEmailView.as_view(), name="chamado-consulta-email"),
    path("publico/consulta-email", ChamadoListarPorEmailView.as_view(), name="chamado-consulta-email-no-slash"),
    path("publico/<int:chamado_id>/processar-ia/", ChamadoPublicoProcessarIAView.as_view(), name="chamado-publico-processar-ia"),
    path("publico/<int:chamado_id>/processar-ia", ChamadoPublicoProcessarIAView.as_view(), name="chamado-publico-processar-ia-no-slash"),
    path("publico/<int:chamado_id>/status-ia/", ChamadoPublicoStatusIAView.as_view(), name="chamado-publico-status-ia"),
    path("publico/<int:chamado_id>/status-ia", ChamadoPublicoStatusIAView.as_view(), name="chamado-publico-status-ia-no-slash"),

    # Endpoints administrativos (autenticados)
    path("", include(router.urls)),
]
