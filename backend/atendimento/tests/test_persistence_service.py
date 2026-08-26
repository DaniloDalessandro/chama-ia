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
from atendimento.models import Atendimento, AuditoriaClassificacao, AvaliacaoCriterioAtendimento
from atendimento.services.classification_service import ServicePriorityClassificationService
from atendimento.services.persistence_service import ServicePersistenceService

User = get_user_model()

VALORES_CRITERIOS_CONSISTENTES = {(0, 1): 2.0, (0, 2): 4.0, (0, 3): 8.0, (1, 2): 2.0, (1, 3): 4.0, (2, 3): 2.0}
VALORES_INTENSIDADES_CONSISTENTES = {(0, 1): 0.5, (0, 2): 0.25, (1, 2): 0.5}


class PersistenceServiceTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="admin@test.com", password="x", name="Admin", role="admin")
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
        self.versao = AHPVersionService.create_rascunho(user=self.user)
        AHPComparisonService.save_comparacoes_criterios(self.versao, criterios_ordenados, VALORES_CRITERIOS_CONSISTENTES, user=self.user)
        for codigo, criterio in self.criterios.items():
            AHPComparisonService.save_comparacoes_intensidades(self.versao, criterio, self.intensidades[codigo], VALORES_INTENSIDADES_CONSISTENTES, user=self.user)
        AHPVersionService.ativar(self.versao, user=self.user)
        self.versao.refresh_from_db()

        self.atendimento = Atendimento.objects.create(nome="Cliente", email="c@test.com")
        for codigo in self.criterios:
            AvaliacaoCriterioAtendimento.objects.create(
                atendimento=self.atendimento, criterio=self.criterios[codigo], intensidade=self.intensidades[codigo][2]
            )

    def test_persist_writes_audit_row_and_updates_atendimento_atomically(self):
        resultado = ServicePriorityClassificationService.classify(self.atendimento)

        auditoria = ServicePersistenceService.persist(self.atendimento, resultado, self.versao, user=self.user)

        self.assertEqual(AuditoriaClassificacao.objects.count(), 1)
        self.assertEqual(auditoria.prioridade, Atendimento.Prioridade.P1)
        self.assertEqual(auditoria.classificacao_cor, "#DC2626")
        self.assertIn("URGENCIA", auditoria.versao_matriz_criterios["ordem"])

        self.atendimento.refresh_from_db()
        self.assertEqual(self.atendimento.prioridade, Atendimento.Prioridade.P1)
        self.assertAlmostEqual(self.atendimento.indice_ahp, 100.0, places=3)
        self.assertEqual(self.atendimento.versao_ahp_utilizada_id, self.versao.id)
        self.assertEqual(self.atendimento.analise_ia_status, Atendimento.AnaliseIAStatus.CONCLUIDA)

    def test_ia_never_touches_status_atendimento(self):
        resultado = ServicePriorityClassificationService.classify(self.atendimento)
        ServicePersistenceService.persist(self.atendimento, resultado, self.versao, user=self.user)

        self.atendimento.refresh_from_db()
        self.assertEqual(self.atendimento.status_atendimento, Atendimento.StatusAtendimento.AGUARDANDO)

    def test_later_config_change_does_not_alter_historical_audit(self):
        resultado = ServicePriorityClassificationService.classify(self.atendimento)
        auditoria = ServicePersistenceService.persist(self.atendimento, resultado, self.versao, user=self.user)

        indice_congelado = auditoria.indice
        pesos_congelados = dict(auditoria.pesos_criterios)

        # simula uma mudanca de configuracao (nova versao ativa com pesos diferentes)
        novo_criterio = self.criterios[CODIGO_URGENCIA]
        novo_criterio.nome = "Urgencia (renomeado)"
        novo_criterio.save()

        auditoria.refresh_from_db()
        self.assertEqual(auditoria.indice, indice_congelado)
        self.assertEqual(auditoria.pesos_criterios, pesos_congelados)
