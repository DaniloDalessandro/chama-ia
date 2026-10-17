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


class ComputePFuzzyTests(SimpleTestCase):
    """Testa a extensao fuzzy ponderada por confianca (AHPSynthesisService.compute_p_fuzzy)."""

    def _escolhidas_moderada(self):
        return {c: "moderada" for c in PESOS}

    def test_full_confidence_collapses_to_crisp(self):
        """confianca=1.0 em todos os criterios → l = m = u (retrocompativel com compute_p)."""
        escolhidas = {
            "URGENCIA": "critica",
            "IMPACTO_NO_CLIENTE": "moderada",
            "SENTIMENTO_DO_CLIENTE": "baixa",
            "TEMPO_DE_ESPERA": "critica",
        }
        confiancas = {c: 1.0 for c in escolhidas}
        p_crisp, _ = AHPSynthesisService.compute_p(PESOS, PRIORIDADES, escolhidas)
        p_l, p_m, p_u, _ = AHPSynthesisService.compute_p_fuzzy(PESOS, PRIORIDADES, escolhidas, confiancas, alpha=0.20)

        self.assertAlmostEqual(p_m, p_crisp, places=9)
        self.assertAlmostEqual(p_l, p_m, places=9)
        self.assertAlmostEqual(p_u, p_m, places=9)

    def test_p_m_equals_compute_p_for_any_confidence(self):
        """P_m deve ser identico ao P(a) tradicional independente da confianca."""
        escolhidas = {
            "URGENCIA": "critica",
            "IMPACTO_NO_CLIENTE": "baixa",
            "SENTIMENTO_DO_CLIENTE": "moderada",
            "TEMPO_DE_ESPERA": "baixa",
        }
        confiancas = {"URGENCIA": 0.7, "IMPACTO_NO_CLIENTE": 0.5, "SENTIMENTO_DO_CLIENTE": 0.9, "TEMPO_DE_ESPERA": 1.0}
        p_crisp, _ = AHPSynthesisService.compute_p(PESOS, PRIORIDADES, escolhidas)
        _, p_m, _, _ = AHPSynthesisService.compute_p_fuzzy(PESOS, PRIORIDADES, escolhidas, confiancas)

        self.assertAlmostEqual(p_m, p_crisp, places=9)

    def test_zero_confidence_widens_interval(self):
        """confianca=0.0 → l < m < u (intervalo maximo)."""
        escolhidas = self._escolhidas_moderada()
        confiancas = {c: 0.0 for c in escolhidas}
        p_l, p_m, p_u, _ = AHPSynthesisService.compute_p_fuzzy(PESOS, PRIORIDADES, escolhidas, confiancas, alpha=0.20)

        self.assertLess(p_l, p_m)
        self.assertGreater(p_u, p_m)

    def test_lower_bound_never_below_zero(self):
        """l nunca vai abaixo de zero mesmo com alpha=1 e confianca=0."""
        escolhidas = {c: "baixa" for c in PESOS}
        confiancas = {c: 0.0 for c in PESOS}
        p_l, _, _, contribs = AHPSynthesisService.compute_p_fuzzy(PESOS, PRIORIDADES, escolhidas, confiancas, alpha=1.0)

        self.assertGreaterEqual(p_l, 0.0)
        for contrib_l, _, _ in contribs.values():
            self.assertGreaterEqual(contrib_l, 0.0)

    def test_upper_bound_capped_at_p_max_criterio(self):
        """u nunca supera a prioridade maxima do criterio (intensidade critica)."""
        escolhidas = {c: "critica" for c in PESOS}
        confiancas = {c: 0.0 for c in PESOS}
        _, p_m, p_u, contribs = AHPSynthesisService.compute_p_fuzzy(PESOS, PRIORIDADES, escolhidas, confiancas, alpha=1.0)

        # critica ja e o teto — u deve ser igual a m
        self.assertAlmostEqual(p_u, p_m, places=9)
        for contrib_l, contrib_m, contrib_u in contribs.values():
            self.assertAlmostEqual(contrib_u, contrib_m, places=9)

    def test_missing_confidence_defaults_to_one(self):
        """Criterio sem confianca fornecida usa 1.0 (sem spread)."""
        escolhidas = {
            "URGENCIA": "critica",
            "IMPACTO_NO_CLIENTE": "moderada",
            "SENTIMENTO_DO_CLIENTE": "baixa",
            "TEMPO_DE_ESPERA": "critica",
        }
        confiancas = {"IMPACTO_NO_CLIENTE": 0.5, "SENTIMENTO_DO_CLIENTE": 0.5}
        _, _, _, contribs = AHPSynthesisService.compute_p_fuzzy(PESOS, PRIORIDADES, escolhidas, confiancas)

        # URGENCIA e TEMPO_DE_ESPERA sem confianca → sem spread → l = m = u
        for codigo in ("URGENCIA", "TEMPO_DE_ESPERA"):
            contrib_l, contrib_m, contrib_u = contribs[codigo]
            self.assertAlmostEqual(contrib_l, contrib_m, places=9)
            self.assertAlmostEqual(contrib_u, contrib_m, places=9)

    def test_contribuicoes_fuzzy_structure(self):
        """contribuicoes_fuzzy tem uma tupla (l, m, u) por criterio."""
        escolhidas = self._escolhidas_moderada()
        confiancas = {c: 0.6 for c in escolhidas}
        _, _, _, contribs = AHPSynthesisService.compute_p_fuzzy(PESOS, PRIORIDADES, escolhidas, confiancas)

        self.assertEqual(set(contribs.keys()), set(PESOS.keys()))
        for v in contribs.values():
            self.assertEqual(len(v), 3)
            l, m, u = v
            self.assertLessEqual(l, m)
            self.assertGreaterEqual(u, m)

    def test_alpha_zero_equals_crisp(self):
        """alpha=0 → spread=0 independente da confianca → l = m = u."""
        escolhidas = self._escolhidas_moderada()
        confiancas = {c: 0.0 for c in escolhidas}
        p_l, p_m, p_u, _ = AHPSynthesisService.compute_p_fuzzy(PESOS, PRIORIDADES, escolhidas, confiancas, alpha=0.0)

        self.assertAlmostEqual(p_l, p_m, places=9)
        self.assertAlmostEqual(p_u, p_m, places=9)

    def test_missing_criterio_raises(self):
        """Criterio sem intensidade escolhida levanta ValueError."""
        with self.assertRaises(ValueError):
            AHPSynthesisService.compute_p_fuzzy(PESOS, PRIORIDADES, {"URGENCIA": "critica"}, {})
