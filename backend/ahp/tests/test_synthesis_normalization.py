from django.test import SimpleTestCase

from ahp.services.normalization_service import AHPNormalizationService
from ahp.services.synthesis_service import AHPSynthesisService

PESOS = {"URGENCIA": 0.4, "IMPACTO_NO_CLIENTE": 0.3, "SENTIMENTO_DO_CLIENTE": 0.2, "TEMPO_DE_ESPERA": 0.1}

PRIORIDADES = {
    "URGENCIA": {"baixa": 0.1, "moderada": 0.3, "critica": 0.6},
    "IMPACTO_NO_CLIENTE": {"baixa": 0.15, "moderada": 0.35, "critica": 0.5},
    "SENTIMENTO_DO_CLIENTE": {"baixa": 0.2, "moderada": 0.3, "critica": 0.5},
    "TEMPO_DE_ESPERA": {"baixa": 0.25, "moderada": 0.35, "critica": 0.4},
}


class ComputePTests(SimpleTestCase):
    def test_sums_weighted_contributions(self):
        escolhidas = {
            "URGENCIA": "critica",
            "IMPACTO_NO_CLIENTE": "moderada",
            "SENTIMENTO_DO_CLIENTE": "baixa",
            "TEMPO_DE_ESPERA": "critica",
        }
        p, contribuicoes = AHPSynthesisService.compute_p(PESOS, PRIORIDADES, escolhidas)

        esperado = 0.4 * 0.6 + 0.3 * 0.35 + 0.2 * 0.2 + 0.1 * 0.4
        self.assertAlmostEqual(p, esperado, places=9)
        self.assertAlmostEqual(contribuicoes["URGENCIA"], 0.4 * 0.6, places=9)

    def test_ausente_contributes_zero(self):
        escolhidas = {
            "URGENCIA": "ausente",
            "IMPACTO_NO_CLIENTE": "moderada",
            "SENTIMENTO_DO_CLIENTE": "baixa",
            "TEMPO_DE_ESPERA": "critica",
        }
        p, contribuicoes = AHPSynthesisService.compute_p(PESOS, PRIORIDADES, escolhidas)
        self.assertEqual(contribuicoes["URGENCIA"], 0.0)

    def test_inconclusiva_raises(self):
        escolhidas = {
            "URGENCIA": "inconclusiva",
            "IMPACTO_NO_CLIENTE": "moderada",
            "SENTIMENTO_DO_CLIENTE": "baixa",
            "TEMPO_DE_ESPERA": "critica",
        }
        with self.assertRaises(ValueError):
            AHPSynthesisService.compute_p(PESOS, PRIORIDADES, escolhidas)

    def test_missing_criterio_raises(self):
        with self.assertRaises(ValueError):
            AHPSynthesisService.compute_p(PESOS, PRIORIDADES, {"URGENCIA": "critica"})


class ComputePMaxTests(SimpleTestCase):
    def test_picks_max_priority_per_criterio(self):
        p_max = AHPSynthesisService.compute_p_max(PESOS, PRIORIDADES)
        esperado = 0.4 * 0.6 + 0.3 * 0.5 + 0.2 * 0.5 + 0.1 * 0.4
        self.assertAlmostEqual(p_max, esperado, places=9)


class ComputeIndiceTests(SimpleTestCase):
    def test_full_score_is_100(self):
        self.assertAlmostEqual(AHPNormalizationService.compute_indice(0.5, 0.5), 100.0, places=6)

    def test_zero_score_is_0(self):
        self.assertAlmostEqual(AHPNormalizationService.compute_indice(0.0, 0.5), 0.0, places=6)

    def test_mid_range_is_within_bounds(self):
        indice = AHPNormalizationService.compute_indice(0.25, 0.5)
        self.assertAlmostEqual(indice, 50.0, places=6)
        self.assertGreaterEqual(indice, 0.0)
        self.assertLessEqual(indice, 100.0)

    def test_clamps_float_overshoot(self):
        indice = AHPNormalizationService.compute_indice(0.500000000002, 0.5)
        self.assertLessEqual(indice, 100.0)

    def test_zero_p_max_raises(self):
        with self.assertRaises(ValueError):
            AHPNormalizationService.compute_indice(0.1, 0.0)

    def test_negative_p_max_raises(self):
        with self.assertRaises(ValueError):
            AHPNormalizationService.compute_indice(0.1, -1.0)
