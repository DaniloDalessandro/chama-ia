from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import ClienteViewSet, ClientePublicoListView

router = SimpleRouter()
router.register(r'', ClienteViewSet, basename='cliente')

urlpatterns = [
    # Endpoint público (sem autenticação)
    path('publico/', ClientePublicoListView.as_view(), name='cliente-publico-list'),
    path('publico', ClientePublicoListView.as_view(), name='cliente-publico-list-no-slash'),

    # Endpoints autenticados
    path('', include(router.urls)),
]
