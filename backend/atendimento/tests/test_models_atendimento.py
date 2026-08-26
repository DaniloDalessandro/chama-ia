from django.db import IntegrityError, transaction
from django.test import TestCase

from ahp.models import Criterio, Intensidade
from atendimento.models import Atendimento, AvaliacaoCriterioAtendimento


class AtendimentoDefaultsTests(TestCase):
    def test_defaults_on_creation(self):
        atendimento = Atendimento.objects.create(nome="Cliente Teste", email="cliente@test.com")

        self.assertEqual(atendimento.status_atendimento, Atendimento.StatusAtendimento.AGUARDANDO)
        self.assertEqual(atendimento.prioridade, Atendimento.Prioridade.NAO_CLASSIFICADO)
        self.assertEqual(atendimento.analise_ia_status, Atendimento.AnaliseIAStatus.PENDENTE)
        self.assertFalse(atendimento.regra_critica_confirmada)
        self.assertIsNone(atendimento.indice_ahp)


class AvaliacaoCriterioAtendimentoConstraintTests(TestCase):
    def setUp(self):
        self.atendimento = Atendimento.objects.create(nome="Cliente Teste", email="cliente@test.com")
        self.criterio = Criterio.objects.create(nome="Urgencia", codigo="URGENCIA")
        self.intensidade = Intensidade.objects.create(criterio=self.criterio, nome="Alta", codigo=Intensidade.Codigo.ALTA)

    def test_unique_avaliacao_per_atendimento_criterio(self):
        AvaliacaoCriterioAtendimento.objects.create(
            atendimento=self.atendimento, criterio=self.criterio, intensidade=self.intensidade
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                AvaliacaoCriterioAtendimento.objects.create(
                    atendimento=self.atendimento, criterio=self.criterio, intensidade=self.intensidade
                )
