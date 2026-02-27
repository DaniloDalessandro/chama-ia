from django.urls import path, include
from rest_framework.routers import SimpleRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    CustomTokenObtainPairView,
    UserMeView,
    UpdateProfileView,
    ChangePasswordView,
    LogoutView,
    AtendentesListView,
    PasswordResetView,
    PasswordResetConfirmView,
    UserViewSet,
    PasswordResetRequestView,
    PasswordResetValidateView,
)

router = SimpleRouter()
router.register(r'usuarios', UserViewSet, basename='usuario')

urlpatterns = [
    # Com barra final
    path("token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("me/", UserMeView.as_view(), name="user_me"),
    path("update-profile/", UpdateProfileView.as_view(), name="update_profile"),
    path("change-password/", ChangePasswordView.as_view(), name="change_password"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("atendentes/", AtendentesListView.as_view(), name="atendentes_list"),
    path("atendentes", AtendentesListView.as_view(), name="atendentes_list_no_slash"),

    # Recuperação de senha (novo fluxo completo)
    path("password-reset/request/", PasswordResetRequestView.as_view(), name="password_reset_request"),
    path("password-reset/validate/", PasswordResetValidateView.as_view(), name="password_reset_validate"),
    path("password-reset/confirm/", PasswordResetConfirmView.as_view(), name="password_reset_confirm_new"),

    # Sem barra final
    path("token", CustomTokenObtainPairView.as_view()),
    path("token/refresh", TokenRefreshView.as_view()),
    path("me", UserMeView.as_view()),
    path("update-profile", UpdateProfileView.as_view()),
    path("change-password", ChangePasswordView.as_view()),
    path("logout", LogoutView.as_view()),
    path("password-reset/request", PasswordResetRequestView.as_view()),
    path("password-reset/validate", PasswordResetValidateView.as_view()),
    path("password-reset/confirm", PasswordResetConfirmView.as_view()),

    # ViewSet de usuários (CRUD completo)
    path("", include(router.urls)),
]
