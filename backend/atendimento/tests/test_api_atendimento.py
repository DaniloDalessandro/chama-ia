from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from ahp.models import (
    CODIGO_IMPACTO_NO_CLIENTE,
    CODIGO_SENTIMENTO_DO_CLIENTE,
    CODIGO_TEMPO_DE_ESPERA,
    CODIGO_URGENCIA,
    Criterio,
    FaixaTempoEspera,
    Intensidade,
)
from ahp.services.comparison_service import AHPComparisonService
from ahp.services.version_service import AHPVersionService
from atendimento.models import Atendimento
from chamados.models import Chamado

User = get_user_model()

VALORES_CRITERIOS_CONSISTENTES = {(0, 1): 2.0, (0, 2): 4.0, (0, 3): 8.0, (1, 2): 2.0, (1, 3): 4.0, (2, 3): 2.0}
VALORES_INTENSIDADES_CONSISTENTES = {(0, 1): 0.5, (0, 2): 0.25, (1, 2): 0.5}


class AtendimentoApiTestCase(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(email="admin@test.com", password="x", name="Admin", role="admin")
        self.cliente_user = User.objects.create_user(email="cliente@test.com", password="x", name="Cliente", role="cliente")

        self.criterios = {}
        self.intensidades = {}
        for ordem, codigo in enumerate(
            [CODIGO_URGENCIA, CODIGO_IMPACTO_NO_CLIENTE, CODIGO_SENTIMENTO_DO_CLIENTE, CODIGO_TEMPO_DE_ESPERA], start=1
        ):
            criterio = Criterio.objects.create(nome=codigo.title(), codigo=codigo, ordem=ordem)
            self.criterios[codigo] = criterio
            Intensidade.objects.create(criterio=criterio, nome="Ausente", codigo=Intensidade.Codigo.AUSENTE, ordem=1)
            baixa = Intensidade.objects.create(criterio=criterio, nome="Baixa", codigo=Intensidade.Codigo.BAIXA, ordem=2)
            moderada = Intensidade.objects.create(criterio=criterio, nome="Moderada", codigo=Intensidade.Codigo.MODERADA, ordem=3)
            critica = Intensidade.objects.create(criterio=criterio, nome="Critica", codigo=Intensidade.Codigo.CRITICA, ordem=4)
            Intensidade.objects.create(criterio=criterio, nome="Inconclusiva", codigo=Intensidade.Codigo.INCONCLUSIVA, ordem=5)
            self.intensidades[codigo] = [baixa, moderada, critica]

        criterio_tempo = self.criterios[CODIGO_TEMPO_DE_ESPERA]
        FaixaTempoEspera.objects.create(criterio=criterio_tempo, minutos_min=0, minutos_max=5, intensidade=self.intensidades[CODIGO_TEMPO_DE_ESPERA][0], ordem=1)
        FaixaTempoEspera.objects.create(criterio=criterio_tempo, minutos_min=5, minutos_max=15, intensidade=self.intensidades[CODIGO_TEMPO_DE_ESPERA][1], ordem=2)
        FaixaTempoEspera.objects.create(criterio=criterio_tempo, minutos_min=15, minutos_max=None, intensidade=self.intensidades[CODIGO_TEMPO_DE_ESPERA][2], ordem=3)

        criterios_ordenados = [self.criterios[c] for c in [CODIGO_URGENCIA, CODIGO_IMPACTO_NO_CLIENTE, CODIGO_SENTIMENTO_DO_CLIENTE, CODIGO_TEMPO_DE_ESPERA]]
        self.versao = AHPVersionService.create_rascunho(user=self.admin)
        AHPComparisonService.save_comparacoes_criterios(self.versao, criterios_ordenados, VALORES_CRITERIOS_CONSISTENTES, user=self.admin)
        for codigo, criterio in self.criterios.items():
            AHPComparisonService.save_comparacoes_intensidades(self.versao, criterio, self.intensidades[codigo], VALORES_INTENSIDADES_CONSISTENTES, user=self.admin)
        AHPVersionService.ativar(self.versao, user=self.admin)

    def test_creating_atendimento_sets_defaults(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post("/api/v1/atendimento/atendimentos", {"nome": "Cliente X", "email": "x@test.com"})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status_atendimento"], Atendimento.StatusAtendimento.AGUARDANDO)
        self.assertEqual(response.data["prioridade"], Atendimento.Prioridade.NAO_CLASSIFICADO)
        self.assertEqual(response.data["analise_ia_status"], Atendimento.AnaliseIAStatus.PENDENTE)

    def test_cliente_can_only_see_own_atendimentos(self):
        Atendimento.objects.create(nome="Meu", email="cliente@test.com")
        Atendimento.objects.create(nome="Outro", email="outro@test.com")

        self.client.force_authenticate(self.cliente_user)
        response = self.client.get("/api/v1/atendimento/atendimentos")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["nome"], "Meu")

    def test_full_flow_mensagem_avaliacao_classificar_encaminhar(self):
        self.client.force_authenticate(self.admin)

        response = self.client.post("/api/v1/atendimento/atendimentos", {"nome": "Cliente Y", "email": "y@test.com"})
        atendimento_id = response.data["id"]

        response = self.client.post(
            f"/api/v1/atendimento/atendimentos/{atendimento_id}/mensagens",
            {"remetente_tipo": "cliente", "conteudo": "Meu sistema esta fora do ar, preciso de ajuda urgente"},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        for codigo in self.criterios:
            response = self.client.post(
                f"/api/v1/atendimento/atendimentos/{atendimento_id}/avaliacoes",
                {"criterio": self.criterios[codigo].id, "intensidade": self.intensidades[codigo][2].id},
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        response = self.client.post(f"/api/v1/atendimento/atendimentos/{atendimento_id}/classificar")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["prioridade"], Atendimento.Prioridade.P1)

        response = self.client.post(
            f"/api/v1/atendimento/atendimentos/{atendimento_id}/encaminhar-chamado", {"motivo": "Precisa de suporte tecnico"}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        chamado = Chamado.objects.get(id=response.data["id"])
        self.assertEqual(chamado.atendimento_origem_id, atendimento_id)

    def test_reavaliar_criterio_updates_instead_of_duplicating(self):
        self.client.force_authenticate(self.admin)
        atendimento = Atendimento.objects.create(nome="Z", email="z@test.com")
        criterio = self.criterios[CODIGO_URGENCIA]

        self.client.post(
            f"/api/v1/atendimento/atendimentos/{atendimento.id}/avaliacoes",
            {"criterio": criterio.id, "intensidade": self.intensidades[CODIGO_URGENCIA][0].id},
        )
        response = self.client.post(
            f"/api/v1/atendimento/atendimentos/{atendimento.id}/avaliacoes",
            {"criterio": criterio.id, "intensidade": self.intensidades[CODIGO_URGENCIA][2].id},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(atendimento.avaliacoes.count(), 1)
        self.assertEqual(atendimento.avaliacoes.first().intensidade, self.intensidades[CODIGO_URGENCIA][2])

    def test_cliente_cannot_trigger_classificar(self):
        atendimento = Atendimento.objects.create(nome="Meu", email="cliente@test.com")
        self.client.force_authenticate(self.cliente_user)
        response = self.client.post(f"/api/v1/atendimento/atendimentos/{atendimento.id}/classificar")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
