"""
Permissões customizadas para controle de acesso baseado em roles.
"""

from rest_framework import permissions


class IsAdmin(permissions.BasePermission):
    """
    Permissão para verificar se o usuário é admin.
    """

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == "admin"
        )


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Permissão para permitir acesso ao próprio recurso ou para admins.

    Usuários comuns podem acessar/editar apenas seus próprios dados.
    Admins podem acessar/editar qualquer dado.
    """

    def has_object_permission(self, request, view, obj):
        # Admins têm acesso total
        if request.user.role == "admin":
            return True

        # Usuário comum só pode acessar seus próprios dados
        # Verifica se o objeto tem um atributo 'user' ou se é o próprio usuário
        if hasattr(obj, "user"):
            return obj.user == request.user
        elif hasattr(obj, "id"):
            return obj.id == request.user.id

        return False


class CanViewUserDetails(permissions.BasePermission):
    """
    Permissão para visualizar detalhes de usuários.

    Regras:
    - Admin: Pode ver tudo de todos
    - Usuário comum: Pode ver dados completos apenas do próprio perfil
    - Usuário comum: Pode ver dados limitados de outros usuários
    """

    def has_object_permission(self, request, view, obj):
        # Métodos seguros (GET, HEAD, OPTIONS)
        if request.method not in permissions.SAFE_METHODS:
            # Apenas admins ou o próprio usuário podem modificar
            if request.user.role == "admin":
                return True
            return obj.id == request.user.id

        # GET: todos podem ver (mas dados filtrados no serializer)
        return True


class CanViewOwnTicketsOnly(permissions.BasePermission):
    """
    Permissão para visualizar chamados.

    Regras:
    - Admin: Pode ver todos os chamados
    - Atendente: Pode ver chamados atribuídos a ele + todos os chamados
    - Cliente: Pode ver apenas seus próprios chamados
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Admins veem tudo
        if request.user.role == "admin":
            return True

        # Atendentes veem todos os chamados
        if request.user.role == "atendente":
            return True

        # Clientes veem apenas seus próprios chamados
        # Verifica pelo e-mail do chamado ou pelo usuário
        if hasattr(obj, "email"):
            return obj.email == request.user.email
        if hasattr(obj, "usuario"):
            return obj.usuario == request.user

        return False
