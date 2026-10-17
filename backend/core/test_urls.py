"""URL conf minimo para testes (sem health_check incompativel com Django 6)."""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    re_path(r"^api/v1/accounts/?", include("accounts.urls")),
    re_path(r"^api/v1/chamados/?", include("chamados.urls")),
    re_path(r"^api/v1/clientes/?", include("clientes.urls")),
    re_path(r"^api/v1/ahp/?", include("ahp.urls")),
    re_path(r"^api/v1/atendimento/?", include("atendimento.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
