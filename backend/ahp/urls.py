from rest_framework.routers import SimpleRouter

from .views import (
    ComparacaoViewSet,
    CriterioViewSet,
    FaixaTempoEsperaViewSet,
    IntensidadeViewSet,
    TermoViewSet,
    VersaoAHPViewSet,
)

# SimpleRouter (nao DefaultRouter): DefaultRouter registra um URL converter
# global ('drf_format_suffix') que so pode ser registrado uma vez por processo;
# o app `chamados` ja usa DefaultRouter, entao os demais apps seguem o mesmo
# padrao de `accounts`/`clientes` e usam SimpleRouter para evitar a colisao.
router = SimpleRouter(trailing_slash=False)
router.register(r"criterios", CriterioViewSet, basename="criterio")
router.register(r"termos", TermoViewSet, basename="termo")
router.register(r"intensidades", IntensidadeViewSet, basename="intensidade")
router.register(r"faixas-tempo-espera", FaixaTempoEsperaViewSet, basename="faixa-tempo-espera")
router.register(r"comparacoes", ComparacaoViewSet, basename="comparacao")
router.register(r"versoes-ahp", VersaoAHPViewSet, basename="versao-ahp")

urlpatterns = router.urls
