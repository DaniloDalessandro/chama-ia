from rest_framework import permissions


class IsAdminOrReadOnlyAtendente(permissions.BasePermission):
    """
    Escrita (POST/PUT/PATCH/DELETE): apenas admin.
    Leitura (GET/HEAD/OPTIONS): admin ou atendente.
    """

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in permissions.SAFE_METHODS:
            return request.user.role in ("admin", "atendente")
        return request.user.role == "admin"
