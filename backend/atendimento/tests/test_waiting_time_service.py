from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from ahp.models import CODIGO_TEMPO_DE_ESPERA, Criterio, FaixaTempoEspera, Intensidade
from atendimento.models import Atendimento
from atendimento.services.waiting_time_service import WaitingTimeService


class WaitingTimeServiceTests(TestCase):
    def setUp(self):
        self.criterio = Criterio.objects.create(nome="Tempo de Espera", codigo=CODIGO_TEMPO_DE_ESPERA)
        self.baixa = Intensidade.objects.create(criterio=self.criterio, nome="Baixa", codigo=Intensidade.Codigo.BAIXA)
        self.moderada = Intensidade.objects.create(criterio=self.criterio, nome="Moderada", codigo=Intensidade.Codigo.MODERADA)
        self.critica = Intensidade.objects.create(criterio=self.criterio, nome="Critica", codigo=Intensidade.Codigo.CRITICA)

        FaixaTempoEspera.objects.create(criterio=self.criterio, minutos_min=0, minutos_max=5, intensidade=self.baixa, ordem=1)
        FaixaTempoEspera.objects.create(criterio=self.criterio, minutos_min=5, minutos_max=15, intensidade=self.moderada, ordem=2)
        FaixaTempoEspera.objects.create(criterio=self.criterio, minutos_min=15, minutos_max=None, intensidade=self.critica, ordem=3)

        self.atendimento = Atendimento.objects.create(nome="Cliente", email="c@test.com")

    def test_compute_wait_minutes_matches_timestamp_delta(self):
        agora = self.atendimento.criado_em + timedelta(minutes=12)
        minutos = WaitingTimeService.compute_wait_minutes(self.atendimento, agora=agora)
        self.assertAlmostEqual(minutos, 12.0, places=1)

    def test_boundary_values_map_to_correct_faixa(self):
        self.assertEqual(WaitingTimeService.get_intensidade_for_wait(0), self.baixa)
        self.assertEqual(WaitingTimeService.get_intensidade_for_wait(4.9), self.baixa)
        self.assertEqual(WaitingTimeService.get_intensidade_for_wait(5), self.moderada)
        self.assertEqual(WaitingTimeService.get_intensidade_for_wait(14.9), self.moderada)
        self.assertEqual(WaitingTimeService.get_intensidade_for_wait(15), self.critica)
        self.assertEqual(WaitingTimeService.get_intensidade_for_wait(1000), self.critica)

    def test_get_intensidade_atual_end_to_end(self):
        agora = self.atendimento.criado_em + timedelta(minutes=20)
        intensidade = WaitingTimeService.get_intensidade_atual(self.atendimento, agora=agora)
        self.assertEqual(intensidade, self.critica)

    def test_missing_criterio_raises(self):
        self.criterio.soft_delete()
        with self.assertRaises(ValueError):
            WaitingTimeService.get_intensidade_for_wait(10)
