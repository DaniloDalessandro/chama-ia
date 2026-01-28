from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    CustomTokenObtainPairView,
    UserMeView,
    UpdateProfileView,
    ChangePasswordView,
    LogoutView,
    PasswordResetView,
    PasswordResetConfirmView,
)

urlpatterns = [
    path("token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("me/", UserMeView.as_view(), name="user_me"),
    path("update-profile/", UpdateProfileView.as_view(), name="update_profile"),
    path("change-password/", ChangePasswordView.as_view(), name="change_password"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("password-reset/", PasswordResetView.as_view(), name="password_reset"),
    path("password-reset-confirm/", PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
]
