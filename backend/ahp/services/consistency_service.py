"""
AHPConsistencyService: indice de consistencia (CI), indice aleatorio (RI) e
razao de consistencia (CR) de Saaty.
"""

# Tabela de Indice Aleatorio (RI) de Saaty, n = 1..15.
RANDOM_INDEX = {
    1: 0.00,
    2: 0.00,
    3: 0.58,
    4: 0.90,
    5: 1.12,
    6: 1.24,
    7: 1.32,
    8: 1.41,
    9: 1.45,
    10: 1.49,
    11: 1.51,
    12: 1.48,
    13: 1.56,
    14: 1.57,
    15: 1.59,
}


class AHPConsistencyService:
    CR_THRESHOLD = 0.10

    @staticmethod
    def compute_ci(lambda_max: float, n: int) -> float:
        """CI = (lambda_max - n) / (n - 1). Para n <= 1, nao ha comparacao: CI = 0.0."""
        if n <= 1:
            return 0.0
        return (lambda_max - n) / (n - 1)

    @staticmethod
    def compute_cr(ci: float, n: int) -> tuple:
        """
        Retorna (cr, ri). Para n > 15 levanta ValueError (fora da tabela de Saaty).
        Para n <= 2, RI = 0 e a matriz e trivialmente consistente (CR = 0.0).
        """
        if n < 1:
            raise ValueError("n precisa ser >= 1.")
        if n > 15:
            raise ValueError(f"Nao ha Indice Aleatorio (RI) tabelado para n={n} (maximo 15).")

        ri = RANDOM_INDEX[n]
        if ri == 0:
            return 0.0, ri

        return ci / ri, ri

    @staticmethod
    def is_consistent(cr: float) -> bool:
        return cr <= AHPConsistencyService.CR_THRESHOLD
