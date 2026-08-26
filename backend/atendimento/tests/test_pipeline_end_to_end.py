"""
Teste de integracao ponta a ponta da Fase 1: seed dos criterios reais ->
versao AHP ativada -> atendimento criado -> avaliacoes manuais -> classificacao
-> auditoria persistida, tudo consistente, sem NENHUMA chamada de IA/LLM.
"""

from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from ahp.models import CODIGO_TEMPO_DE_ESPERA, Intensidade, VersaoAHP
from ahp.services.comparison_service import AHPComparisonService
from ahp.services.hierarchy_service import AHPHierarchyService
from ahp.services.intensity_service import AHPIntensityService
from ahp.services.version_service import AHPVersionService
from atendimento.models import Atendimento, AuditoriaClassificacao, AvaliacaoCriterioAtendimento
from atendimento.services.classification_service import ServicePriorityClassificationService
from atendimento.services.persistence_service import ServicePersistenceService
from atendimento.services.ticket_creation_service import TicketCreationService

User = get_user_model()


def _valores_por_distancia_de_ordem(n, inverter=False):
    """Constroi uma matriz n x n razoavelmente consistente (CR baixo) a partir
    da distancia de ordem entre os itens -- ver verificacao numerica no plano."""
    valores = {}
    for i in range(n):
        for j in range(i + 1, n):
            v = float(1 + (j - i))
            if inverter:
                v = 1.0 / v
            valores[(i, j)] = v
    return valores


class PipelineEndToEndTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(email="admin@test.com", password="x", name="Admin", role="admin")

    def test_full_pipeline_seed_to_audit(self):
        # 1. Seed dos 4 criterios obrigatorios + intensidades + faixas de tempo.
        out = StringIO()
        call_command("ahp_seed_criterios", "--user-email=admin@test.com", stdout=out)
        self.assertIn("Seed concluido", out.getvalue())

        criterios = list(AHPHierarchyService.get_criterios_ativos())
        self.assertEqual(len(criterios), 4)

        # 2. Cria e ativa uma VersaoAHP consistente.
        versao = AHPVersionService.create_rascunho(descricao="v1", user=self.admin)
        AHPComparisonService.save_comparacoes_criterios(
            versao, criterios, _valores_por_distancia_de_ordem(len(criterios), inverter=False), user=self.admin
        )
        for criterio in criterios:
            comparaveis = list(AHPIntensityService.get_comparable_intensidades(criterio))
            self.assertEqual(len(comparaveis), 5)  # muito_baixa, baixa, moderada, alta, critica
            AHPComparisonService.save_comparacoes_intensidades(
                versao, criterio, comparaveis, _valores_por_distancia_de_ordem(len(comparaveis), inverter=True), user=self.admin
            )

        resultado_ativacao = AHPVersionService.ativar(versao, user=self.admin)
        self.assertEqual(resultado_ativacao.estado, VersaoAHP.Estado.ATIVA)

        # 3. Cria o atendimento (defaults corretos, sem nenhuma IA envolvida).
        atendimento = Atendimento.objects.create(nome="Cliente Final", email="final@test.com")
        self.assertEqual(atendimento.status_atendimento, Atendimento.StatusAtendimento.AGUARDANDO)
        self.assertEqual(atendimento.prioridade, Atendimento.Prioridade.NAO_CLASSIFICADO)
        self.assertEqual(atendimento.analise_ia_status, Atendimento.AnaliseIAStatus.PENDENTE)

        # 4. Avaliacoes manuais: CRITICA em todos os criterios -> deve dar indice maximo.
        for criterio in criterios:
            intensidade_critica = Intensidade.objects.get(criterio=criterio, codigo=Intensidade.Codigo.CRITICA)
            AvaliacaoCriterioAtendimento.objects.create(
                atendimento=atendimento, criterio=criterio, intensidade=intensidade_critica, origem="manual",
            )

        # 5. Classifica e persiste.
        resultado = ServicePriorityClassificationService.classify(atendimento)
        self.assertFalse(resultado.revisao_humana)
        auditoria = ServicePersistenceService.persist(atendimento, resultado, versao, user=self.admin)

        # 6. Consistencia interna do resultado persistido.
        atendimento.refresh_from_db()
        self.assertEqual(atendimento.prioridade, Atendimento.Prioridade.P1)
        self.assertAlmostEqual(atendimento.indice_ahp, 100.0, places=3)
        self.assertEqual(auditoria.versao_hierarquia, versao.numero_versao)
        soma_contribuicoes = sum(auditoria.contribuicoes.values())
        p_max = auditoria.versao_ahp.p_max
        self.assertAlmostEqual(soma_contribuicoes, (auditoria.indice / 100.0) * p_max, places=6)
        self.assertEqual(AuditoriaClassificacao.objects.filter(atendimento=atendimento).count(), 1)

    def test_old_low_urgency_vs_new_high_urgency_ahp_determines_order(self):
        """Atendimento antigo de baixa urgencia + atendimento recente de alta urgencia -> AHP determina a ordem."""
        call_command("ahp_seed_criterios", "--user-email=admin@test.com", stdout=StringIO())
        criterios = list(AHPHierarchyService.get_criterios_ativos())

        versao = AHPVersionService.create_rascunho(user=self.admin)
        AHPComparisonService.save_comparacoes_criterios(
            versao, criterios, _valores_por_distancia_de_ordem(len(criterios)), user=self.admin
        )
        for criterio in criterios:
            comparaveis = list(AHPIntensityService.get_comparable_intensidades(criterio))
            AHPComparisonService.save_comparacoes_intensidades(
                versao, criterio, comparaveis, _valores_por_distancia_de_ordem(len(comparaveis), inverter=True), user=self.admin
            )
        AHPVersionService.ativar(versao, user=self.admin)

        antigo = Atendimento.objects.create(nome="Antigo", email="antigo@test.com")
        recente = Atendimento.objects.create(nome="Recente", email="recente@test.com")

        for criterio in criterios:
            baixa = Intensidade.objects.get(criterio=criterio, codigo=Intensidade.Codigo.BAIXA)
            AvaliacaoCriterioAtendimento.objects.create(atendimento=antigo, criterio=criterio, intensidade=baixa)
            critica = Intensidade.objects.get(criterio=criterio, codigo=Intensidade.Codigo.CRITICA)
            AvaliacaoCriterioAtendimento.objects.create(atendimento=recente, criterio=criterio, intensidade=critica)

        resultado_antigo = ServicePriorityClassificationService.classify(antigo)
        resultado_recente = ServicePriorityClassificationService.classify(recente)

        self.assertLess(resultado_antigo.indice, resultado_recente.indice)
        self.assertEqual(resultado_recente.prioridade, Atendimento.Prioridade.P1)

    def test_unresolved_atendimento_generates_chamado_resolved_does_not(self):
        atendimento_resolvido = Atendimento.objects.create(
            nome="Resolvido", email="r@test.com", status_atendimento=Atendimento.StatusAtendimento.RESOLVIDO
        )
        # Nenhum servico cria Chamado automaticamente so por causa do status.
        self.assertEqual(atendimento_resolvido.chamados_gerados.count(), 0)

        atendimento_nao_resolvido = Atendimento.objects.create(nome="Nao Resolvido", email="nr@test.com")
        chamado = TicketCreationService.create_from_atendimento(atendimento_nao_resolvido, motivo="precisa de equipe tecnica", user=self.admin)

        self.assertEqual(chamado.atendimento_origem_id, atendimento_nao_resolvido.id)
        self.assertEqual(atendimento_nao_resolvido.chamados_gerados.count(), 1)
        atendimento_nao_resolvido.refresh_from_db()
        self.assertEqual(atendimento_nao_resolvido.status_atendimento, Atendimento.StatusAtendimento.ENCAMINHADO_PARA_CHAMADO)
