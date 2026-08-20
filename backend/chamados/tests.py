"""
Testes automatizados para o app chamados.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase
from rest_framework import status

from .models import Chamado, AnexoChamado, ComentarioChamado
from clientes.models import Cliente

User = get_user_model()


class ChamadoModelTest(TestCase):
    """Testes para o model Chamado."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="admin@test.com",
            password="testpass123",
            name="Admin Test",
            role="admin"
        )
        self.cliente = Cliente.objects.create(
            nome="Empresa Teste Ltda",
            cnpj="12.345.678/0001-90",
            nome_responsavel="João Silva",
            created_by=self.user
        )

    def test_create_chamado(self):
        """Testa criação de chamado."""
        chamado = Chamado.objects.create(
            nome="Teste Cliente",
            email="cliente@test.com",
            telefone="11999999999",
            cliente=self.cliente,
            tipo="erro-sistema",
            assunto="Teste de chamado",
            descricao="Descrição do teste",
            created_by=self.user
        )

        self.assertIsNotNone(chamado.protocolo)
        self.assertTrue(chamado.protocolo.endswith("/2026"))
        self.assertEqual(chamado.status, Chamado.Status.ABERTO)
        self.assertEqual(chamado.status_kanban, Chamado.StatusKanban.NOVO)

    def test_protocolo_generation(self):
        """Testa geração automática de protocolo."""
        chamado1 = Chamado.objects.create(
            nome="Cliente 1",
            email="cliente1@test.com",
            assunto="Teste 1",
            descricao="Teste",
            created_by=self.user
        )
        chamado2 = Chamado.objects.create(
            nome="Cliente 2",
            email="cliente2@test.com",
            assunto="Teste 2",
            descricao="Teste",
            created_by=self.user
        )

        # Protocolos devem ser sequenciais
        proto1_num = int(chamado1.protocolo.split("/")[0])
        proto2_num = int(chamado2.protocolo.split("/")[0])
        self.assertEqual(proto2_num, proto1_num + 1)

    def test_status_kanban_sync(self):
        """Testa sincronização de status_kanban com status."""
        chamado = Chamado.objects.create(
            nome="Teste",
            email="test@test.com",
            assunto="Teste",
            descricao="Teste",
            status=Chamado.Status.ABERTO,
            created_by=self.user
        )
        self.assertEqual(chamado.status_kanban, Chamado.StatusKanban.NOVO)

        chamado.status = Chamado.Status.EM_ATENDIMENTO
        chamado.save()
        self.assertEqual(chamado.status_kanban, Chamado.StatusKanban.EM_ANDAMENTO)

        chamado.status = Chamado.Status.RESOLVIDO
        chamado.save()
        self.assertEqual(chamado.status_kanban, Chamado.StatusKanban.CONCLUIDO)


class ChamadoAPITest(APITestCase):
    """Testes para os endpoints da API de chamados."""

    def setUp(self):
        self.admin_user = User.objects.create_user(
            email="admin@test.com",
            password="testpass123",
            name="Admin Test",
            role="admin"
        )
        self.atendente_user = User.objects.create_user(
            email="atendente@test.com",
            password="testpass123",
            name="Atendente Test",
            role="atendente"
        )
        self.cliente = Cliente.objects.create(
            nome="Empresa Teste",
            cnpj="12.345.678/0001-90",
            nome_responsavel="João",
            created_by=self.admin_user
        )

    def get_auth_token(self, user):
        """Helper para obter token de autenticação."""
        response = self.client.post("/api/v1/accounts/login", {
            "email": user.email,
            "password": "testpass123"
        })
        return response.data["access"]

    def test_create_chamado_publico(self):
        """Testa criação de chamado via endpoint público."""
        data = {
            "nome": "Cliente Teste",
            "email": "cliente@test.com",
            "telefone": "11999999999",
            "cliente_id": self.cliente.id,
            "tipo": "erro-sistema",
            "assunto": "Erro no sistema",
            "descricao": "Descrição detalhada do erro",
        }

        response = self.client.post("/api/v1/chamados/publico", data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        self.assertIn("protocolo", response.data["data"])

    def test_consulta_chamado_publico(self):
        """Testa consulta pública de chamado."""
        chamado = Chamado.objects.create(
            nome="Cliente Teste",
            email="cliente@test.com",
            assunto="Teste",
            descricao="Teste",
        )

        response = self.client.get(
            f"/api/v1/chamados/publico/consulta?protocolo={chamado.protocolo}&email={chamado.email}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["protocolo"], chamado.protocolo)

    def test_list_chamados_admin(self):
        """Testa listagem de chamados para admin."""
        token = self.get_auth_token(self.admin_user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        # Criar alguns chamados
        for i in range(3):
            Chamado.objects.create(
                nome=f"Cliente {i}",
                email=f"cliente{i}@test.com",
                assunto=f"Teste {i}",
                descricao="Teste",
                created_by=self.admin_user
            )

        response = self.client.get("/api/v1/chamados/admin")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data["results"]), 3)

    def test_update_status_chamado(self):
        """Testa atualização de status de chamado."""
        token = self.get_auth_token(self.admin_user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        chamado = Chamado.objects.create(
            nome="Cliente",
            email="cliente@test.com",
            assunto="Teste",
            descricao="Teste",
            created_by=self.admin_user
        )

        response = self.client.patch(
            f"/api/v1/chamados/admin/{chamado.id}/status",
            {"status": "em_atendimento"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        chamado.refresh_from_db()
        self.assertEqual(chamado.status, Chamado.Status.EM_ATENDIMENTO)

    def test_atribuir_atendente(self):
        """Testa atribuição de atendente a chamado."""
        token = self.get_auth_token(self.admin_user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        chamado = Chamado.objects.create(
            nome="Cliente",
            email="cliente@test.com",
            assunto="Teste",
            descricao="Teste",
        )

        response = self.client.patch(
            f"/api/v1/chamados/admin/{chamado.id}/atribuir-atendente",
            {"atendente_id": self.atendente_user.id}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        chamado.refresh_from_db()
        self.assertEqual(chamado.atendente_id, self.atendente_user.id)


class AuthenticationTest(APITestCase):
    """Testes de autenticação e permissões."""

    def setUp(self):
        self.admin_user = User.objects.create_user(
            email="admin@test.com",
            password="testpass123",
            name="Admin",
            role="admin"
        )
        self.cliente_user = User.objects.create_user(
            email="cliente@test.com",
            password="testpass123",
            name="Cliente",
            role="cliente"
        )

    def test_login_success(self):
        """Testa login bem-sucedido."""
        response = self.client.post("/api/v1/accounts/login", {
            "email": "admin@test.com",
            "password": "testpass123"
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_login_invalid_credentials(self):
        """Testa login com credenciais inválidas."""
        response = self.client.post("/api/v1/accounts/login", {
            "email": "admin@test.com",
            "password": "wrongpassword"
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_protected_endpoint_without_auth(self):
        """Testa acesso a endpoint protegido sem autenticação."""
        response = self.client.get("/api/v1/chamados/admin")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_protected_endpoint_with_auth(self):
        """Testa acesso a endpoint protegido com autenticação."""
        response = self.client.post("/api/v1/accounts/login", {
            "email": "admin@test.com",
            "password": "testpass123"
        })
        token = response.data["access"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        response = self.client.get("/api/v1/chamados/admin")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_only_endpoint_cliente_access(self):
        """Testa que cliente não pode acessar endpoint de admin."""
        response = self.client.post("/api/v1/accounts/login", {
            "email": "cliente@test.com",
            "password": "testpass123"
        })
        token = response.data["access"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        response = self.client.get("/api/v1/accounts/usuarios")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class ChamadoPermissionTest(APITestCase):
    """Testes para permissões de acesso aos chamados baseado em role."""

    def setUp(self):
        """Configura usuários e chamados para testes de permissão."""
        # Criar usuários com diferentes roles
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

        self.cliente1 = User.objects.create_user(
            email="cliente1@test.com",
            password="testpass123",
            name="Cliente 1",
            role="cliente"
        )

        self.cliente2 = User.objects.create_user(
            email="cliente2@test.com",
            password="testpass123",
            name="Cliente 2",
            role="cliente"
        )

        # Criar chamados para diferentes clientes
        self.chamado_cliente1 = Chamado.objects.create(
            nome="Cliente Um",
            email="cliente1@test.com",
            telefone="11999999999",
            assunto="Chamado do Cliente 1",
            descricao="Descrição do chamado do cliente 1",
            created_by=self.admin
        )

        self.chamado_cliente2 = Chamado.objects.create(
            nome="Cliente Dois",
            email="cliente2@test.com",
            telefone="11888888888",
            assunto="Chamado do Cliente 2",
            descricao="Descrição do chamado do cliente 2",
            created_by=self.admin
        )

        self.chamado_outro = Chamado.objects.create(
            nome="Outro Cliente",
            email="outro@test.com",
            telefone="11777777777",
            assunto="Chamado de outro cliente",
            descricao="Descrição de outro chamado",
            created_by=self.admin
        )

    def get_token(self, user):
        """Helper para obter token JWT."""
        response = self.client.post("/api/v1/accounts/login", {
            "email": user.email,
            "password": "testpass123"
        })
        return response.data["access"]

    # ========================================
    # Testes de Listagem de Chamados
    # ========================================

    def test_admin_sees_all_chamados(self):
        """Admin deve ver todos os chamados."""
        token = self.get_token(self.admin)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = self.client.get("/api/v1/chamados/admin/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Admin vê todos os 3 chamados
        self.assertEqual(len(response.data["results"]), 3)

    def test_atendente_sees_all_chamados(self):
        """Atendente deve ver todos os chamados."""
        token = self.get_token(self.atendente)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = self.client.get("/api/v1/chamados/admin/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Atendente também vê todos os 3 chamados
        self.assertEqual(len(response.data["results"]), 3)

    def test_cliente_sees_only_own_chamados(self):
        """Cliente deve ver apenas seus próprios chamados (filtrados por email)."""
        token = self.get_token(self.cliente1)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = self.client.get("/api/v1/chamados/admin/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Cliente 1 vê apenas 1 chamado (o dele)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["email"], "cliente1@test.com")

    def test_cliente_different_user_sees_different_chamados(self):
        """Clientes diferentes veem chamados diferentes."""
        # Cliente 1
        token1 = self.get_token(self.cliente1)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token1}")
        response1 = self.client.get("/api/v1/chamados/admin/")

        # Cliente 2
        token2 = self.get_token(self.cliente2)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token2}")
        response2 = self.client.get("/api/v1/chamados/admin/")

        # Cada um vê apenas seus próprios chamados
        self.assertEqual(len(response1.data["results"]), 1)
        self.assertEqual(len(response2.data["results"]), 1)

        # Verificar que são chamados diferentes
        self.assertNotEqual(
            response1.data["results"][0]["id"],
            response2.data["results"][0]["id"]
        )

    # ========================================
    # Testes de Detalhamento de Chamado
    # ========================================

    def test_admin_can_view_any_chamado(self):
        """Admin pode ver detalhes de qualquer chamado."""
        token = self.get_token(self.admin)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = self.client.get(f"/api/v1/chamados/admin/{self.chamado_cliente1.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.chamado_cliente1.id)

    def test_atendente_can_view_any_chamado(self):
        """Atendente pode ver detalhes de qualquer chamado."""
        token = self.get_token(self.atendente)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = self.client.get(f"/api/v1/chamados/admin/{self.chamado_cliente2.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.chamado_cliente2.id)

    def test_cliente_can_view_own_chamado(self):
        """Cliente pode ver detalhes de seu próprio chamado."""
        token = self.get_token(self.cliente1)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = self.client.get(f"/api/v1/chamados/admin/{self.chamado_cliente1.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.chamado_cliente1.id)

    def test_cliente_cannot_view_other_chamado(self):
        """Cliente não pode ver chamado de outro cliente."""
        token = self.get_token(self.cliente1)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = self.client.get(f"/api/v1/chamados/admin/{self.chamado_cliente2.id}/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # ========================================
    # Testes de Atualização de Chamado
    # ========================================

    def test_admin_can_update_any_chamado(self):
        """Admin pode atualizar qualquer chamado."""
        token = self.get_token(self.admin)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = self.client.patch(
            f"/api/v1/chamados/admin/{self.chamado_cliente1.id}/",
            {"assunto": "Assunto atualizado pelo admin"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.chamado_cliente1.refresh_from_db()
        self.assertEqual(self.chamado_cliente1.assunto, "Assunto atualizado pelo admin")

    def test_atendente_can_update_any_chamado(self):
        """Atendente pode atualizar qualquer chamado."""
        token = self.get_token(self.atendente)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = self.client.patch(
            f"/api/v1/chamados/admin/{self.chamado_cliente2.id}/status/",
            {"status": "em_atendimento"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_cliente_cannot_update_chamado(self):
        """Cliente não pode atualizar chamados (endpoint admin-only)."""
        token = self.get_token(self.cliente1)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = self.client.patch(
            f"/api/v1/chamados/admin/{self.chamado_cliente1.id}/",
            {"assunto": "Tentativa de atualização"}
        )

        # Cliente não tem permissão de atualizar via endpoint admin
        # (pode apenas criar via endpoint público)
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

    # ========================================
    # Testes de Filtros
    # ========================================

    def test_cliente_filter_by_status(self):
        """Cliente pode filtrar seus próprios chamados por status."""
        # Criar mais chamados para cliente1
        Chamado.objects.create(
            nome="Cliente Um",
            email="cliente1@test.com",
            assunto="Chamado resolvido",
            descricao="Descrição",
            status=Chamado.Status.RESOLVIDO,
            created_by=self.admin
        )

        token = self.get_token(self.cliente1)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        # Filtrar por status ABERTO
        response = self.client.get("/api/v1/chamados/admin/?status=aberto")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Deve retornar apenas chamados abertos do cliente1
        for chamado in response.data["results"]:
            self.assertEqual(chamado["status"], "aberto")
            self.assertEqual(chamado["email"], "cliente1@test.com")

    def test_cliente_search_own_chamados(self):
        """Cliente pode buscar em seus próprios chamados."""
        token = self.get_token(self.cliente1)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = self.client.get("/api/v1/chamados/admin/?search=Cliente 1")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Resultados são apenas do cliente1
        for chamado in response.data["results"]:
            self.assertEqual(chamado["email"], "cliente1@test.com")

    # ========================================
    # Testes de Estatísticas
    # ========================================

    def test_admin_stats_all_chamados(self):
        """Admin vê estatísticas de todos os chamados."""
        token = self.get_token(self.admin)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = self.client.get("/api/v1/chamados/admin/stats/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Total deve incluir todos os chamados
        self.assertGreaterEqual(response.data["total"], 3)

    def test_cliente_stats_own_chamados_only(self):
        """Cliente vê estatísticas apenas de seus chamados."""
        token = self.get_token(self.cliente1)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = self.client.get("/api/v1/chamados/admin/stats/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Total deve ser apenas os chamados do cliente1
        self.assertEqual(response.data["total"], 1)
