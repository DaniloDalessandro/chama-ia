from rest_framework import status, viewsets, filters
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from .permissions import IsAdmin, CanViewUserDetails
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample, OpenApiResponse
from core.cache_decorators import cache_response
from .serializers import (
    CustomTokenObtainPairSerializer,
    UserSerializer,
    ChangePasswordSerializer,
    UserListSerializer,
    UserPublicSerializer,
    UserCreateSerializer,
    UserUpdateSerializer,
    UserResetPasswordSerializer,
    PasswordResetRequestSerializer,
    PasswordResetValidateSerializer,
    PasswordResetConfirmNewSerializer,
)
from .throttling import (
    LoginRateThrottle,
    PasswordResetRateThrottle,
    AuthenticatedUserRateThrottle,
)

User = get_user_model()


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Login endpoint com proteção contra brute-force.
    Limite: 5 tentativas por minuto por IP
    """
    serializer_class = CustomTokenObtainPairSerializer
    throttle_classes = [LoginRateThrottle]


class UserMeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


class UpdateProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            if not user.check_password(serializer.validated_data["old_password"]):
                return Response(
                    {"detail": "Senha atual incorreta"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            user.set_password(serializer.validated_data["new_password"])
            user.save()
            return Response({"detail": "Senha alterada com sucesso"})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            return Response({"detail": "Logout realizado com sucesso"})
        except Exception:
            return Response({"detail": "Logout realizado"})


class AtendentesListView(APIView):
    """Lista usuarios com role admin ou atendente (para filtros/atribuicao)."""
    permission_classes = [IsAuthenticated]

    @cache_response(timeout=600, key_prefix='atendentes_list')  # Cache por 10 minutos
    def get(self, request):
        atendentes = User.objects.filter(
            role__in=["admin", "atendente"],
            is_active=True,
        ).order_by("name").values("id", "name", "email", "role")
        return Response(list(atendentes))


class PasswordResetView(APIView):
    """
    Reset de senha com proteção contra spam.
    Limite: 3 tentativas por hora por IP
    """
    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetRateThrottle]

    def post(self, request):
        email = request.data.get("email")
        if not email:
            return Response(
                {"detail": "Email é obrigatório"},
                status=status.HTTP_400_BAD_REQUEST
            )
        # Em produção, enviar email com link de reset
        return Response({"detail": "Se o email existir, você receberá instruções de reset"})


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        # Em produção, validar token e alterar senha
        return Response({"detail": "Senha alterada com sucesso"})


@extend_schema(tags=["Gestão de Usuários"])
class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestão de usuários com controle de permissões por role.

    Regras de acesso:
    - Admin: Vê todos os usuários com dados completos, pode fazer CRUD completo
    - Usuário comum: Vê lista limitada de outros usuários, pode editar apenas próprio perfil

    Endpoints:
    - GET /api/v1/accounts/usuarios/ - Lista usuários
    - POST /api/v1/accounts/usuarios/ - Cria usuário (apenas admin)
    - GET /api/v1/accounts/usuarios/{id}/ - Detalha usuário
    - PUT/PATCH /api/v1/accounts/usuarios/{id}/ - Atualiza usuário
    - DELETE /api/v1/accounts/usuarios/{id}/ - Remove usuário (apenas admin)
    - POST /api/v1/accounts/usuarios/{id}/toggle_active/ - Ativa/Desativa usuário (apenas admin)
    - POST /api/v1/accounts/usuarios/{id}/reset_password/ - Reseta senha (apenas admin)
    """

    # Otimização N+1: carregar ForeignKeys relacionados
    queryset = User.objects.select_related(
        'direction',
        'management',
        'coordination'
    ).all().order_by('-created_at')
    permission_classes = [IsAuthenticated, CanViewUserDetails]

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter
    ]

    filterset_fields = ['role', 'is_active', 'is_staff']
    search_fields = ['email', 'name', 'cpf']
    ordering_fields = ['name', 'email', 'created_at', 'updated_at']
    ordering = ['-created_at']

    def get_queryset(self):
        """
        Filtra queryset baseado no role do usuário.

        - Admin: Vê todos os usuários
        - Usuário comum: Vê apenas usuários ativos (dados limitados no serializer)
        """
        queryset = super().get_queryset()

        # Admin vê tudo
        if self.request.user.role == "admin":
            return queryset

        # Usuário comum vê apenas usuários ativos
        return queryset.filter(is_active=True)

    def get_serializer_class(self):
        """
        Retorna serializer apropriado baseado na action e role do usuário.

        - Admin: Sempre vê dados completos
        - Usuário comum:
          - Ao listar outros usuários: UserPublicSerializer (dados limitados)
          - Ao ver próprio perfil: UserSerializer (dados completos)
        """
        # Admin sempre usa serializers completos
        if self.request.user.role == "admin":
            if self.action == 'list':
                return UserListSerializer
            elif self.action == 'create':
                return UserCreateSerializer
            elif self.action in ['update', 'partial_update']:
                return UserUpdateSerializer
            elif self.action == 'reset_password':
                return UserResetPasswordSerializer
            return UserSerializer

        # Usuário comum
        if self.action == 'list':
            # Lista limitada de outros usuários
            return UserPublicSerializer
        elif self.action == 'retrieve':
            # Se estiver vendo próprio perfil, retorna dados completos
            # Caso contrário, dados limitados
            try:
                obj = self.get_object()
                if obj.id == self.request.user.id:
                    return UserSerializer
            except:
                pass
            return UserPublicSerializer
        elif self.action in ['update', 'partial_update']:
            # Só pode editar próprio perfil
            return UserUpdateSerializer

        return UserPublicSerializer

    def get_permissions(self):
        """
        Define permissões específicas por action.

        - create, destroy, toggle_active, reset_password: Apenas admin
        - update, partial_update: Admin ou próprio usuário
        - list, retrieve: Qualquer usuário autenticado
        """
        if self.action in ['create', 'destroy', 'toggle_active', 'reset_password']:
            return [IsAuthenticated(), IsAdmin()]
        return super().get_permissions()

    def destroy(self, request, *args, **kwargs):
        """Impede exclusão do próprio usuário."""
        instance = self.get_object()

        if instance.id == request.user.id:
            return Response(
                {"detail": "Você não pode excluir sua própria conta"},
                status=status.HTTP_400_BAD_REQUEST
            )

        return super().destroy(request, *args, **kwargs)

    @extend_schema(
        summary="Ativar/Desativar usuário",
        description="""
        Alterna o status ativo/inativo de um usuário.

        **Permissão:** Apenas Admin

        **Regras:**
        - Não é possível desativar a própria conta
        - Usuário inativo não consegue fazer login
        - Chamados do usuário permanecem intactos
        """,
        request=None,
        responses={
            200: OpenApiResponse(
                description="Status alterado com sucesso",
                response=UserListSerializer
            ),
            400: OpenApiResponse(
                description="Tentativa de desativar própria conta"
            ),
            403: OpenApiResponse(
                description="Sem permissão (não é admin)"
            )
        }
    )
    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """Ativa/desativa um usuário."""
        user = self.get_object()

        if user.id == request.user.id:
            return Response(
                {"detail": "Você não pode desativar sua própria conta"},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.is_active = not user.is_active
        user.save()

        serializer = UserListSerializer(user)
        return Response(serializer.data)

    @extend_schema(
        summary="Resetar senha de usuário (Admin)",
        description="""
        Permite que um administrador redefina a senha de qualquer usuário.

        **Permissão:** Apenas Admin

        **Casos de uso:**
        - Usuário esqueceu a senha e não tem acesso ao e-mail
        - Resetar senha de usuário suspenso/bloqueado
        - Criar senha temporária para novo usuário

        **Diferença do Password Reset:**
        - Este endpoint requer autenticação de admin
        - Password Reset público usa token por e-mail
        """,
        request=UserResetPasswordSerializer,
        responses={
            200: OpenApiResponse(
                description="Senha alterada com sucesso",
                examples=[
                    OpenApiExample(
                        "Success",
                        value={
                            "detail": "Senha do usuário João Silva alterada com sucesso"
                        }
                    )
                ]
            ),
            400: OpenApiResponse(
                description="Senha muito curta ou inválida"
            ),
            403: OpenApiResponse(
                description="Sem permissão (não é admin)"
            )
        },
        examples=[
            OpenApiExample(
                "Request Example",
                value={"new_password": "NovaSenhaSegura123"},
                request_only=True
            )
        ]
    )
    @action(detail=True, methods=['post'])
    def reset_password(self, request, pk=None):
        """Reseta a senha de um usuário (admin)."""
        user = self.get_object()
        serializer = UserResetPasswordSerializer(data=request.data)

        if serializer.is_valid():
            user.set_password(serializer.validated_data['new_password'])
            user.save()

            return Response({
                "detail": f"Senha do usuário {user.name} alterada com sucesso"
            })

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Estatísticas de usuários",
        description="""
        Retorna estatísticas gerais sobre os usuários do sistema.

        **Dados retornados:**
        - Total de usuários cadastrados
        - Usuários ativos vs inativos
        - Distribuição por role (Admin, Atendente, Cliente)

        **Casos de uso:**
        - Dashboard administrativo
        - Relatórios gerenciais
        - Monitoramento de crescimento de usuários
        """,
        responses={
            200: OpenApiResponse(
                description="Estatísticas dos usuários",
                examples=[
                    OpenApiExample(
                        "Stats Response",
                        value={
                            "total": 150,
                            "ativos": 142,
                            "inativos": 8,
                            "por_role": {
                                "admin": {
                                    "label": "Administrador",
                                    "count": 5
                                },
                                "atendente": {
                                    "label": "Atendente",
                                    "count": 15
                                },
                                "cliente": {
                                    "label": "Cliente",
                                    "count": 130
                                }
                            }
                        }
                    )
                ]
            )
        }
    )
    @action(detail=False, methods=['get'])
    @cache_response(timeout=300, key_prefix='users_stats')  # Cache por 5 minutos
    def stats(self, request):
        """Estatísticas de usuários."""
        total = User.objects.count()
        ativos = User.objects.filter(is_active=True).count()
        inativos = total - ativos

        por_role = {}
        for role_code, role_name in User.Role.choices:
            count = User.objects.filter(role=role_code).count()
            por_role[role_code] = {
                'label': role_name,
                'count': count
            }

        return Response({
            'total': total,
            'ativos': ativos,
            'inativos': inativos,
            'por_role': por_role
        })


# ============================================
# Views de Recuperação de Senha
# ============================================

@extend_schema(
    tags=["Autenticação - Recuperação de Senha"],
    summary="Solicitar recuperação de senha",
    description="""
    Envia um e-mail com link de recuperação de senha para o endereço fornecido.

    **Segurança:**
    - Sempre retorna sucesso (mesmo se e-mail não existir) para prevenir enumeração de usuários
    - Token válido por 1 hora
    - Tokens anteriores são automaticamente invalidados
    - Rate limit: 3 tentativas por hora por IP

    **Fluxo:**
    1. Usuário solicita reset → recebe e-mail com link
    2. Usuário clica no link → valida token com endpoint /validate
    3. Usuário define nova senha → confirma com endpoint /confirm
    """,
    request=PasswordResetRequestSerializer,
    responses={
        200: OpenApiResponse(
            description="E-mail enviado com sucesso (ou usuário não existe)",
            examples=[
                OpenApiExample(
                    "Success Response",
                    value={
                        "success": True,
                        "message": "Se o e-mail estiver cadastrado, você receberá instruções de recuperação."
                    }
                )
            ]
        ),
        400: OpenApiResponse(
            description="Email não fornecido ou inválido"
        ),
        429: OpenApiResponse(
            description="Rate limit excedido (3 tentativas por hora)"
        )
    },
    examples=[
        OpenApiExample(
            "Request Example",
            value={"email": "usuario@example.com"},
            request_only=True
        )
    ]
)
class PasswordResetRequestView(APIView):
    """
    Solicita recuperação de senha via e-mail.

    POST /api/v1/auth/password-reset/request
    Body: {"email": "usuario@example.com"}

    Proteção contra brute-force: 3 tentativas por hora
    """
    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetRateThrottle]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        # Obter IP do cliente
        ip_address = self.get_client_ip(request)

        # Processar solicitação
        from accounts.services.password_reset_service import PasswordResetService
        result = PasswordResetService.request_password_reset(
            email=serializer.validated_data['email'],
            ip_address=ip_address
        )

        # SEMPRE retorna success=True (por segurança)
        return Response({
            "success": True,
            "message": result['message']
        }, status=status.HTTP_200_OK)

    def get_client_ip(self, request):
        """Obtém o IP real do cliente (considerando proxies)."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


@extend_schema(
    tags=["Autenticação - Recuperação de Senha"],
    summary="Validar token de recuperação",
    description="""
    Verifica se um token de recuperação de senha é válido e ainda não expirou.

    **Validações:**
    - Token existe no banco de dados
    - Token não foi utilizado anteriormente
    - Token não expirou (válido por 1 hora)

    **Casos de uso:**
    - Frontend valida token antes de exibir formulário de nova senha
    - Usuário clicou no link do e-mail e precisa verificar se ainda é válido
    """,
    request=PasswordResetValidateSerializer,
    responses={
        200: OpenApiResponse(
            description="Token válido",
            examples=[
                OpenApiExample(
                    "Valid Token Response",
                    value={
                        "success": True,
                        "message": "Token válido",
                        "email": "usuario@example.com"
                    }
                )
            ]
        ),
        400: OpenApiResponse(
            description="Token inválido, expirado ou já utilizado",
            examples=[
                OpenApiExample(
                    "Invalid Token",
                    value={
                        "success": False,
                        "message": "Token inválido ou expirado"
                    }
                ),
                OpenApiExample(
                    "Expired Token",
                    value={
                        "success": False,
                        "message": "Este token expirou. Solicite um novo."
                    }
                ),
                OpenApiExample(
                    "Used Token",
                    value={
                        "success": False,
                        "message": "Este token já foi utilizado."
                    }
                )
            ]
        )
    },
    examples=[
        OpenApiExample(
            "Request Example",
            value={"token": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"},
            request_only=True
        )
    ]
)
class PasswordResetValidateView(APIView):
    """
    Valida se um token de recuperação é válido.

    POST /api/v1/auth/password-reset/validate
    Body: {"token": "abc123..."}
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetValidateSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        from accounts.services.password_reset_service import PasswordResetService
        result = PasswordResetService.validate_token(
            token=serializer.validated_data['token']
        )

        if result['success']:
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=["Autenticação - Recuperação de Senha"],
    summary="Confirmar nova senha",
    description="""
    Redefine a senha do usuário usando um token válido de recuperação.

    **Validações:**
    - Token deve ser válido e não expirado
    - Senha deve ter no mínimo 6 caracteres
    - Senhas devem coincidir (new_password == new_password_confirm)

    **Segurança:**
    - Token é marcado como utilizado após sucesso
    - Senha é criptografada com bcrypt/argon2
    - Token se torna inválido após uso

    **Resultado:**
    - Usuário pode fazer login com a nova senha imediatamente
    - E-mail de confirmação pode ser enviado (configurável)
    """,
    request=PasswordResetConfirmNewSerializer,
    responses={
        200: OpenApiResponse(
            description="Senha alterada com sucesso",
            examples=[
                OpenApiExample(
                    "Success Response",
                    value={
                        "success": True,
                        "message": "Senha alterada com sucesso. Você já pode fazer login."
                    }
                )
            ]
        ),
        400: OpenApiResponse(
            description="Token inválido ou senhas não coincidem",
            examples=[
                OpenApiExample(
                    "Invalid Token",
                    value={
                        "success": False,
                        "message": "Token inválido ou expirado"
                    }
                ),
                OpenApiExample(
                    "Password Mismatch",
                    value={
                        "new_password_confirm": ["As senhas não coincidem."]
                    }
                ),
                OpenApiExample(
                    "Short Password",
                    value={
                        "new_password": ["Ensure this field has at least 6 characters."]
                    }
                )
            ]
        )
    },
    examples=[
        OpenApiExample(
            "Request Example",
            value={
                "token": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
                "new_password": "MinhaNovaSenh@123",
                "new_password_confirm": "MinhaNovaSenh@123"
            },
            request_only=True
        )
    ]
)
class PasswordResetConfirmView(APIView):
    """
    Confirma a redefinição de senha com novo valor.

    POST /api/v1/auth/password-reset/confirm
    Body: {
        "token": "abc123...",
        "new_password": "nova_senha",
        "new_password_confirm": "nova_senha"
    }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmNewSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        from accounts.services.password_reset_service import PasswordResetService
        result = PasswordResetService.reset_password(
            token=serializer.validated_data['token'],
            new_password=serializer.validated_data['new_password']
        )

        if result['success']:
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
