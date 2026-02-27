"""
Testes automatizados para o app accounts.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status

User = get_user_model()


class UserModelTest(TestCase):
    """Testes para o model CustomUser."""

    def test_create_user(self):
        """Testa criação de usuário comum."""
        user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
            name="Test User"
        )
        self.assertEqual(user.email, "user@test.com")
        self.assertEqual(user.name, "Test User")
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(user.role, "cliente")

    def test_create_superuser(self):
        """Testa criação de superusuário."""
        admin = User.objects.create_superuser(
            email="admin@test.com",
            password="adminpass123",
            name="Admin User"
        )
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertEqual(admin.role, "admin")

    def test_user_string_representation(self):
        """Testa representação em string do usuário."""
        user = User.objects.create_user(
            email="user@test.com",
            password="pass",
            name="John Doe"
        )
        self.assertEqual(str(user), "John Doe (user@test.com)")

    def test_email_normalization(self):
        """Testa normalização de email."""
        user = User.objects.create_user(
            email="Test@EXAMPLE.COM",
            password="pass",
            name="Test"
        )
        self.assertEqual(user.email, "test@example.com")


class UserAPITest(APITestCase):
    """Testes para endpoints da API de usuários."""

    def setUp(self):
        self.admin = User.objects.create_superuser(
            email="admin@test.com",
            password="testpass123",
            name="Admin"
        )
        self.regular_user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
            name="Regular User"
        )

    def get_admin_token(self):
        """Helper para obter token de admin."""
        response = self.client.post("/api/v1/accounts/login", {
            "email": "admin@test.com",
            "password": "testpass123"
        })
        return response.data["access"]

    def test_user_registration(self):
        """Testa criação de usuário via API (admin only)."""
        token = self.get_admin_token()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        data = {
            "email": "newuser@test.com",
            "password": "newpass123",
            "password_confirm": "newpass123",
            "name": "New User",
            "role": "atendente"
        }

        response = self.client.post("/api/v1/accounts/usuarios", data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.filter(email="newuser@test.com").count(), 1)

    def test_user_me_endpoint(self):
        """Testa endpoint de dados do usuário logado."""
        response = self.client.post("/api/v1/accounts/login", {
            "email": "user@test.com",
            "password": "testpass123"
        })
        token = response.data["access"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        response = self.client.get("/api/v1/accounts/me")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "user@test.com")
        self.assertEqual(response.data["name"], "Regular User")

    def test_change_password(self):
        """Testa mudança de senha."""
        response = self.client.post("/api/v1/accounts/login", {
            "email": "user@test.com",
            "password": "testpass123"
        })
        token = response.data["access"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        response = self.client.post("/api/v1/accounts/change-password", {
            "old_password": "testpass123",
            "new_password": "newpass456"
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class PasswordResetAPITest(APITestCase):
    """Testes para endpoints de recuperação de senha."""

    def setUp(self):
        """Configura dados de teste."""
        self.user = User.objects.create_user(
            email="user@test.com",
            password="oldpass123",
            name="Test User"
        )
        self.inactive_user = User.objects.create_user(
            email="inactive@test.com",
            password="pass123",
            name="Inactive User",
            is_active=False
        )

    def test_password_reset_request_valid_email(self):
        """Testa solicitação de reset com email válido."""
        response = self.client.post("/api/v1/accounts/password-reset/request", {
            "email": "user@test.com"
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertIn("Se o e-mail estiver cadastrado", response.data["message"])

        # Verificar se token foi criado
        from accounts.models import PasswordResetToken
        self.assertTrue(
            PasswordResetToken.objects.filter(
                user=self.user,
                is_used=False
            ).exists()
        )

    def test_password_reset_request_invalid_email(self):
        """Testa solicitação com email não existente (deve retornar success por segurança)."""
        response = self.client.post("/api/v1/accounts/password-reset/request", {
            "email": "nonexistent@test.com"
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertIn("Se o e-mail estiver cadastrado", response.data["message"])

        # Não deve criar token
        from accounts.models import PasswordResetToken
        self.assertEqual(PasswordResetToken.objects.count(), 0)

    def test_password_reset_request_inactive_user(self):
        """Testa solicitação para usuário inativo (deve retornar success por segurança)."""
        response = self.client.post("/api/v1/accounts/password-reset/request", {
            "email": "inactive@test.com"
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])

        # Não deve criar token para usuário inativo
        from accounts.models import PasswordResetToken
        self.assertEqual(PasswordResetToken.objects.count(), 0)

    def test_password_reset_request_missing_email(self):
        """Testa solicitação sem email."""
        response = self.client.post("/api/v1/accounts/password-reset/request", {})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_password_reset_validate_valid_token(self):
        """Testa validação de token válido."""
        from accounts.models import PasswordResetToken
        reset_token = PasswordResetToken.create_for_user(self.user)

        response = self.client.post("/api/v1/accounts/password-reset/validate", {
            "token": reset_token.token
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["email"], self.user.email)

    def test_password_reset_validate_invalid_token(self):
        """Testa validação de token inválido."""
        response = self.client.post("/api/v1/accounts/password-reset/validate", {
            "token": "invalid-token-xyz"
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
        self.assertIn("inválido", response.data["message"].lower())

    def test_password_reset_validate_expired_token(self):
        """Testa validação de token expirado."""
        from accounts.models import PasswordResetToken
        from django.utils import timezone
        from datetime import timedelta

        # Criar token expirado
        reset_token = PasswordResetToken.create_for_user(self.user)
        reset_token.expires_at = timezone.now() - timedelta(hours=1)
        reset_token.save()

        response = self.client.post("/api/v1/accounts/password-reset/validate", {
            "token": reset_token.token
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
        self.assertIn("expirado", response.data["message"].lower())

    def test_password_reset_validate_used_token(self):
        """Testa validação de token já utilizado."""
        from accounts.models import PasswordResetToken

        reset_token = PasswordResetToken.create_for_user(self.user)
        reset_token.is_used = True
        reset_token.save()

        response = self.client.post("/api/v1/accounts/password-reset/validate", {
            "token": reset_token.token
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
        self.assertIn("já foi utilizado", response.data["message"])

    def test_password_reset_confirm_success(self):
        """Testa confirmação de reset com sucesso."""
        from accounts.models import PasswordResetToken

        reset_token = PasswordResetToken.create_for_user(self.user)

        response = self.client.post("/api/v1/accounts/password-reset/confirm", {
            "token": reset_token.token,
            "new_password": "newsecurepass123",
            "new_password_confirm": "newsecurepass123"
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])

        # Verificar se senha foi alterada
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("newsecurepass123"))

        # Verificar se token foi marcado como usado
        reset_token.refresh_from_db()
        self.assertTrue(reset_token.is_used)

    def test_password_reset_confirm_password_mismatch(self):
        """Testa confirmação com senhas que não coincidem."""
        from accounts.models import PasswordResetToken

        reset_token = PasswordResetToken.create_for_user(self.user)

        response = self.client.post("/api/v1/accounts/password-reset/confirm", {
            "token": reset_token.token,
            "new_password": "newsecurepass123",
            "new_password_confirm": "differentpass456"
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("new_password_confirm", response.data)

        # Verificar que senha não foi alterada
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("oldpass123"))

    def test_password_reset_confirm_short_password(self):
        """Testa confirmação com senha muito curta."""
        from accounts.models import PasswordResetToken

        reset_token = PasswordResetToken.create_for_user(self.user)

        response = self.client.post("/api/v1/accounts/password-reset/confirm", {
            "token": reset_token.token,
            "new_password": "123",
            "new_password_confirm": "123"
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_reset_token_invalidation(self):
        """Testa que tokens anteriores são invalidados ao criar novo."""
        from accounts.models import PasswordResetToken

        # Criar primeiro token
        token1 = PasswordResetToken.create_for_user(self.user)
        token1_value = token1.token

        # Criar segundo token
        token2 = PasswordResetToken.create_for_user(self.user)

        # Verificar que primeiro token foi invalidado
        token1.refresh_from_db()
        self.assertTrue(token1.is_used)

        # Verificar que segundo token está ativo
        self.assertFalse(token2.is_used)

    def test_password_reset_throttling(self):
        """Testa limitação de rate (3 requests por hora)."""
        # Fazer 3 requests válidos
        for _ in range(3):
            response = self.client.post("/api/v1/accounts/password-reset/request", {
                "email": "user@test.com"
            })
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        # O 4º deve ser bloqueado pelo throttle
        response = self.client.post("/api/v1/accounts/password-reset/request", {
            "email": "user@test.com"
        })
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)


class PermissionAPITest(APITestCase):
    """Testes para controle de permissões baseado em roles."""

    def setUp(self):
        """Configura dados de teste com diferentes roles."""
        self.admin = User.objects.create_user(
            email="admin@test.com",
            password="testpass123",
            name="Admin User",
            role="admin"
        )

        self.atendente = User.objects.create_user(
            email="atendente@test.com",
            password="testpass123",
            name="Atendente User",
            role="atendente"
        )

        self.cliente = User.objects.create_user(
            email="cliente@test.com",
            password="testpass123",
            name="Cliente User",
            role="cliente"
        )

        self.outro_cliente = User.objects.create_user(
            email="outro@test.com",
            password="testpass123",
            name="Outro Cliente",
            role="cliente"
        )

    def get_token(self, email, password="testpass123"):
        """Helper para obter token JWT."""
        response = self.client.post("/api/v1/accounts/login", {
            "email": email,
            "password": password
        })
        return response.data["access"]

    # ========================================
    # Testes de Listagem de Usuários
    # ========================================

    def test_admin_sees_all_users(self):
        """Admin deve ver todos os usuários com dados completos."""
        token = self.get_token("admin@test.com")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = self.client.get("/api/v1/accounts/usuarios/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 4)  # 4 usuários

        # Verificar que vê dados completos (email, cpf, etc.)
        first_user = response.data["results"][0]
        self.assertIn("email", first_user)
        self.assertIn("cpf", first_user)
        self.assertIn("phone", first_user)

    def test_regular_user_sees_limited_data(self):
        """Usuário comum vê apenas usuários ativos com dados limitados."""
        token = self.get_token("cliente@test.com")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = self.client.get("/api/v1/accounts/usuarios/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verificar que vê dados limitados (sem email completo, cpf, phone)
        first_user = response.data["results"][0]
        self.assertNotIn("email", first_user)  # UserPublicSerializer não tem email
        self.assertIn("email_domain", first_user)  # Tem email mascarado
        self.assertNotIn("cpf", first_user)
        self.assertNotIn("phone", first_user)

    def test_email_domain_masking(self):
        """Verifica se email é mascarado como ***@domain.com."""
        token = self.get_token("cliente@test.com")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = self.client.get("/api/v1/accounts/usuarios/")

        for user_data in response.data["results"]:
            if "email_domain" in user_data and user_data["email_domain"]:
                self.assertTrue(user_data["email_domain"].startswith("***@"))

    def test_user_sees_own_profile_completely(self):
        """Usuário vê próprio perfil com dados completos."""
        token = self.get_token("cliente@test.com")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = self.client.get(f"/api/v1/accounts/usuarios/{self.cliente.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Deve ter dados completos do próprio perfil
        self.assertEqual(response.data["email"], "cliente@test.com")
        self.assertEqual(response.data["name"], "Cliente User")

    def test_user_sees_other_profile_limited(self):
        """Usuário vê perfil de outros com dados limitados."""
        token = self.get_token("cliente@test.com")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = self.client.get(f"/api/v1/accounts/usuarios/{self.outro_cliente.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Dados limitados de outro usuário
        self.assertNotIn("email", response.data)
        self.assertIn("email_domain", response.data)

    # ========================================
    # Testes de CRUD de Usuários
    # ========================================

    def test_admin_can_create_user(self):
        """Admin pode criar novos usuários."""
        token = self.get_token("admin@test.com")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = self.client.post("/api/v1/accounts/usuarios/", {
            "email": "newuser@test.com",
            "password": "securepass123",
            "password_confirm": "securepass123",
            "name": "New User",
            "role": "atendente"
        })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email="newuser@test.com").exists())

    def test_regular_user_cannot_create_user(self):
        """Usuário comum não pode criar novos usuários."""
        token = self.get_token("cliente@test.com")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = self.client.post("/api/v1/accounts/usuarios/", {
            "email": "hacker@test.com",
            "password": "pass123",
            "password_confirm": "pass123",
            "name": "Hacker",
            "role": "admin"
        })

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_update_any_user(self):
        """Admin pode atualizar qualquer usuário."""
        token = self.get_token("admin@test.com")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = self.client.patch(f"/api/v1/accounts/usuarios/{self.cliente.id}/", {
            "name": "Cliente Updated"
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.name, "Cliente Updated")

    def test_user_can_update_own_profile(self):
        """Usuário pode atualizar próprio perfil."""
        token = self.get_token("cliente@test.com")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = self.client.patch(f"/api/v1/accounts/usuarios/{self.cliente.id}/", {
            "name": "My New Name"
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.name, "My New Name")

    def test_user_cannot_update_other_profile(self):
        """Usuário não pode atualizar perfil de outros."""
        token = self.get_token("cliente@test.com")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = self.client.patch(f"/api/v1/accounts/usuarios/{self.outro_cliente.id}/", {
            "name": "Hacked Name"
        })

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_delete_user(self):
        """Admin pode excluir usuários."""
        token = self.get_token("admin@test.com")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = self.client.delete(f"/api/v1/accounts/usuarios/{self.cliente.id}/")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(User.objects.filter(id=self.cliente.id).exists())

    def test_user_cannot_delete_user(self):
        """Usuário comum não pode excluir usuários."""
        token = self.get_token("cliente@test.com")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = self.client.delete(f"/api/v1/accounts/usuarios/{self.outro_cliente.id}/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_cannot_delete_self(self):
        """Ninguém pode excluir própria conta (mesmo admin)."""
        token = self.get_token("admin@test.com")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = self.client.delete(f"/api/v1/accounts/usuarios/{self.admin.id}/")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("não pode excluir sua própria conta", response.data["detail"])

    # ========================================
    # Testes de Actions Especiais
    # ========================================

    def test_admin_can_toggle_active(self):
        """Admin pode ativar/desativar usuários."""
        token = self.get_token("admin@test.com")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = self.client.post(f"/api/v1/accounts/usuarios/{self.cliente.id}/toggle_active/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.cliente.refresh_from_db()
        self.assertFalse(self.cliente.is_active)

    def test_user_cannot_toggle_active(self):
        """Usuário comum não pode ativar/desativar usuários."""
        token = self.get_token("cliente@test.com")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = self.client.post(f"/api/v1/accounts/usuarios/{self.outro_cliente.id}/toggle_active/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_reset_password(self):
        """Admin pode resetar senha de usuários."""
        token = self.get_token("admin@test.com")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = self.client.post(f"/api/v1/accounts/usuarios/{self.cliente.id}/reset_password/", {
            "new_password": "adminchangedpass123"
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.cliente.refresh_from_db()
        self.assertTrue(self.cliente.check_password("adminchangedpass123"))

    def test_user_cannot_reset_other_password(self):
        """Usuário comum não pode resetar senha de outros."""
        token = self.get_token("cliente@test.com")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = self.client.post(f"/api/v1/accounts/usuarios/{self.outro_cliente.id}/reset_password/", {
            "new_password": "hackedpass123"
        })

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
