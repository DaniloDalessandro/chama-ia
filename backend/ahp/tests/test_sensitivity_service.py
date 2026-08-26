from django.test import SimpleTestCase

from ahp.services.sensitivity_service import AHPSensitivityService


class PerturbWeightTests(SimpleTestCase):
    def test_result_still_sums_to_one(self):
        pesos = {"URGENCIA": 0.4, "IMPACTO_NO_CLIENTE": 0.3, "SENTIMENTO_DO_CLIENTE": 0.2, "TEMPO_DE_ESPERA": 0.1}
        resultado = AHPSensitivityService.perturb_weight(pesos, "URGENCIA", 0.1)
        self.assertAlmostEqual(sum(resultado.values()), 1.0, places=9)
        self.assertAlmostEqual(resultado["URGENCIA"], 0.5, places=9)

    def test_unknown_criterio_raises(self):
        with self.assertRaises(ValueError):
            AHPSensitivityService.perturb_weight({"URGENCIA": 0.5}, "OUTRO", 0.1)

    def test_out_of_bounds_raises(self):
        with self.assertRaises(ValueError):
            AHPSensitivityService.perturb_weight({"URGENCIA": 0.5, "IMPACTO_NO_CLIENTE": 0.5}, "URGENCIA", 0.9)
