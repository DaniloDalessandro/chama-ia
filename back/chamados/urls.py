from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ChamadoPublicoCreateView,
    ChamadoConsultaPublicaView,
    ChamadoAdminViewSet,
)

router = DefaultRouter()
router.register(r"", ChamadoAdminViewSet, basename="chamado")

urlpatterns = [
    # Endpoints publicos (sem autenticacao)
    path("publico/", ChamadoPublicoCreateView.as_view(), name="chamado-publico-create"),
    path("publico", ChamadoPublicoCreateView.as_view(), name="chamado-publico-create-no-slash"),
    path("publico/consulta/", ChamadoConsultaPublicaView.as_view(), name="chamado-publico-consulta"),
    path("publico/consulta", ChamadoConsultaPublicaView.as_view(), name="chamado-publico-consulta-no-slash"),

    # Endpoints administrativos (autenticados)
    path("", include(router.urls)),
]
