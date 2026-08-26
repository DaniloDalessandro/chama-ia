from rest_framework import permissions


class IsAdminOrAtendente(permissions.BasePermission):
    """Apenas admin ou atendente podem operar sobre a classificacao/fila de atendimentos."""

    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and request.user.role in ("admin", "atendente")
        )
