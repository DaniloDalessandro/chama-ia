from django.test import TestCase

from ahp.models import Criterio, Intensidade, Termo
from atendimento.ai.agents.agente7_auditoria import agente7_node
from atendimento.services.audit_service import AuditService


class ChecarConsistenciaTests(TestCase):
    def setUp(self):
        self.criterio = Criterio.objects.create(nome="Urgencia", codigo="URGENCIA")
        self.intensidade = Intensidade.objects.create(criterio=self.criterio, nome="Alta", codigo=Intensidade.Codigo.ALTA)
        self.termo_aprovado = Termo.objects.create(
            criterio=self.criterio, termo="prazo legal", intensidade_base=self.intensidade,
            status_aprovacao=Termo.StatusAprovacao.APROVADO,
        )

    def test_clean_state_has_no_alertas(self):
        state = {
            "agente3_resultado": {"termos_correspondidos": [{"termo_id": self.termo_aprovado.id}]},
            "agente4_resultado": {"avaliacoes": [{"criterio_codigo": "URGENCIA", "evidencia": "cliente relatou", "dados_ausentes": False}]},
            "agente5_resultado": {"regra_critica_confirmada": False},
            "agente6_resultado": {"prioridade": "p2"},
        }
        resultado = AuditService.checar_consistencia(state)
        self.assertEqual(resultado["alertas"], [])
        self.assertEqual(len(resultado["checagens"]), 4)

    def test_flags_termo_not_approved(self):
        termo_pendente = Termo.objects.create(
            criterio=self.criterio, termo="outro termo", intensidade_base=self.intensidade,
            status_aprovacao=Termo.StatusAprovacao.PENDENTE_APROVACAO,
        )
        state = {"agente3_resultado": {"termos_correspondidos": [{"termo_id": termo_pendente.id}]}}
        resultado = AuditService.checar_consistencia(state)
        self.assertTrue(any(str(termo_pendente.id) in a for a in resultado["alertas"]))

    def test_flags_missing_evidencia_without_dados_ausentes(self):
        state = {"agente4_resultado": {"avaliacoes": [{"criterio_codigo": "URGENCIA", "evidencia": "", "dados_ausentes": False}]}}
        resultado = AuditService.checar_consistencia(state)
        self.assertTrue(any("URGENCIA" in a for a in resultado["alertas"]))

    def test_does_not_flag_missing_evidencia_when_dados_ausentes_true(self):
        state = {
            "agente4_resultado": {"avaliacoes": [{"criterio_codigo": "URGENCIA", "evidencia": "", "dados_ausentes": True}]},
            "agente6_resultado": {"prioridade": "revisao_humana"},
        }
        resultado = AuditService.checar_consistencia(state)
        self.assertEqual(resultado["alertas"], [])

    def test_flags_regra_critica_without_justificativa(self):
        state = {"agente5_resultado": {"regra_critica_confirmada": True, "justificativa": ""}}
        resultado = AuditService.checar_consistencia(state)
        self.assertTrue(any("justificativa" in a for a in resultado["alertas"]))

    def test_flags_missing_agente6_resultado(self):
        state = {"agente6_resultado": None}
        resultado = AuditService.checar_consistencia(state)
        self.assertTrue(any("Agente 6" in a for a in resultado["alertas"]))


class Agente7NodeTests(TestCase):
    def test_node_returns_only_declared_keys(self):
        resultado = agente7_node({})
        self.assertEqual(set(resultado.keys()), {"agente7_resultado", "erros"})
        self.assertEqual(resultado["erros"], [])
        self.assertIn("checagens", resultado["agente7_resultado"])
        self.assertIn("alertas", resultado["agente7_resultado"])
