"""
AHPNormalizationService: normaliza P(a) para o indice 0-100 usado na fila.
"""


class AHPNormalizationService:
    @staticmethod
    def compute_indice(p: float, p_max: float) -> float:
        """Indice(a) = 100 * P(a) / P_max, sempre restrito a [0, 100]."""
        if p_max <= 0:
            raise ValueError("P_max precisa ser positivo para normalizar o indice.")

        indice = 100.0 * p / p_max
        return max(0.0, min(100.0, indice))
