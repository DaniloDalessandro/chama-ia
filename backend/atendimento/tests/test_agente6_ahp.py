from django.contrib.auth import get_user_model
from django.test import TestCase

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
from atendimento.ai.agents import agente6_ahp
from atendimento.ai.agents.agente6_ahp import agente6_node
from atendimento.models import Atendimento

User = get_user_model()

VALORES_CRITERIOS = {(0, 1): 2.0, (0, 2): 4.0, (0, 3): 8.0, (1, 2): 2.0, (1, 3): 4.0, (2, 3): 2.0}
VALORES_INTENSIDADES = {(0, 1): 0.5, (0, 2): 0.25, (1, 2): 0.5}


class Agente6NodeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="admin@test.com", password="x", name="Admin", role="admin")
        self.criterios = {}
        self.intensidades = {}
        for ordem, codigo in enumerate([CODIGO_URGENCIA, CODIGO_IMPACTO_NO_CLIENTE, CODIGO_SENTIMENTO_DO_CLIENTE, CODIGO_TEMPO_DE_ESPERA], start=1):
            criterio = Criterio.objects.create(nome=codigo.title(), codigo=codigo, ordem=ordem)
            self.criterios[codigo] = criterio
            Intensidade.objects.create(criterio=criterio, nome="Ausente", codigo=Intensidade.Codigo.AUSENTE, ordem=1)
            baixa = Intensidade.objects.create(criterio=criterio, nome="Baixa", codigo=Intensidade.Codigo.BAIXA, ordem=2)
            moderada = Intensidade.objects.create(criterio=criterio, nome="Moderada", codigo=Intensidade.Codigo.MODERADA, ordem=3)
            critica = Intensidade.objects.create(criterio=criterio, nome="Critica", codigo=Intensidade.Codigo.CRITICA, ordem=4)
            Intensidade.objects.create(criterio=criterio, nome="Inconclusiva", codigo=Intensidade.Codigo.INCONCLUSIVA, ordem=5)
            self.intensidades[codigo] = [baixa, moderada, critica]

        ct = self.criterios[CODIGO_TEMPO_DE_ESPERA]
        FaixaTempoEspera.objects.create(criterio=ct, minutos_min=0, minutos_max=5, intensidade=self.intensidades[CODIGO_TEMPO_DE_ESPERA][0], ordem=1)
        FaixaTempoEspera.objects.create(criterio=ct, minutos_min=5, minutos_max=15, intensidade=self.intensidades[CODIGO_TEMPO_DE_ESPERA][1], ordem=2)
        FaixaTempoEspera.objects.create(criterio=ct, minutos_min=15, minutos_max=None, intensidade=self.intensidades[CODIGO_TEMPO_DE_ESPERA][2], ordem=3)

        criterios_ordenados = [self.criterios[c] for c in [CODIGO_URGENCIA, CODIGO_IMPACTO_NO_CLIENTE, CODIGO_SENTIMENTO_DO_CLIENTE, CODIGO_TEMPO_DE_ESPERA]]
        self.versao = AHPVersionService.create_rascunho(user=self.user)
        AHPComparisonService.save_comparacoes_criterios(self.versao, criterios_ordenados, VALORES_CRITERIOS, user=self.user)
        for codigo, criterio in self.criterios.items():
            AHPComparisonService.save_comparacoes_intensidades(self.versao, criterio, self.intensidades[codigo], VALORES_INTENSIDADES, user=self.user)
        AHPVersionService.ativar(self.versao, user=self.user)

        self.atendimento = Atendimento.objects.create(nome="Cliente", email="c@test.com")

    def test_module_has_zero_llm_imports(self):
        self.assertFalse(hasattr(agente6_ahp, "build_deepseek_llm"))
        self.assertFalse(hasattr(agente6_ahp, "build_chain"))

    def test_no_active_version_returns_error_not_crash(self):
        self.versao.estado = "arquivada"
        self.versao.save()
        state = {"atendimento_id": self.atendimento.id, "agente4_resultado": {"avaliacoes": []}}

        resultado = agente6_node(state)

        self.assertIsNone(resultado["agente6_resultado"])
        self.assertEqual(len(resultado["erros"]), 1)

    def test_unknown_atendimento_returns_error_not_crash(self):
        state = {"atendimento_id": 999999, "agente4_resultado": {"avaliacoes": []}}
        resultado = agente6_node(state)
        self.assertIsNone(resultado["agente6_resultado"])
        self.assertEqual(len(resultado["erros"]), 1)

    def test_full_critica_yields_p1(self):
        avaliacoes = [
            {"criterio_codigo": codigo, "intensidade_codigo": "critica"}
            for codigo in [CODIGO_URGENCIA, CODIGO_IMPACTO_NO_CLIENTE, CODIGO_SENTIMENTO_DO_CLIENTE]
        ]
        state = {"atendimento_id": self.atendimento.id, "agente4_resultado": {"avaliacoes": avaliacoes}}

        resultado = agente6_node(state)

        self.assertEqual(resultado["erros"], [])
        self.assertEqual(resultado["versao_ahp_id"], self.versao.id)
        # TEMPO_DE_ESPERA e calculado deterministicamente por WaitingTimeService a partir
        # do criado_em real do atendimento (recem-criado -> faixa "baixa", nao "critica"),
        # entao o indice fica alto mas nao necessariamente 100.
        self.assertGreaterEqual(resultado["agente6_resultado"]["indice"], 80.0)
        self.assertEqual(resultado["agente6_resultado"]["prioridade"], "p1")

    def test_inconclusiva_from_agent4_forces_revisao_humana(self):
        avaliacoes = [
            {"criterio_codigo": CODIGO_URGENCIA, "intensidade_codigo": "inconclusiva"},
            {"criterio_codigo": CODIGO_IMPACTO_NO_CLIENTE, "intensidade_codigo": "moderada"},
            {"criterio_codigo": CODIGO_SENTIMENTO_DO_CLIENTE, "intensidade_codigo": "moderada"},
        ]
        state = {"atendimento_id": self.atendimento.id, "agente4_resultado": {"avaliacoes": avaliacoes}}

        resultado = agente6_node(state)

        self.assertTrue(resultado["agente6_resultado"]["revisao_humana"])
        self.assertEqual(resultado["agente6_resultado"]["prioridade"], "revisao_humana")
