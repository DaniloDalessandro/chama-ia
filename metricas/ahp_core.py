"""
ahp_core.py — Motor AHP puro (sem Django).

Espelha exatamente a lógica de:
  backend/ahp/services/synthesis_service.py
  backend/ahp/services/eigenvector_service.py
  backend/ahp/services/consistency_service.py

Valores de referência extraídos da configuração padrão do sistema (VersaoAHP v1).
"""

import numpy as np

# ---------------------------------------------------------------------------
# Configuração AHP — critérios e pesos (escala de Saaty normalizada)
# ---------------------------------------------------------------------------

CRITERIOS = ["URGENCIA", "IMPACTO_NO_CLIENTE", "SENTIMENTO_DO_CLIENTE", "TEMPO_DE_ESPERA"]

# Matriz de comparação par-a-par (triângulo superior, escala de Saaty 1-9)
# Urgência é 3x mais importante que Impacto, 5x que Sentimento, 7x que Tempo
MATRIZ_CRITERIOS = np.array([
    [1,   3,   5,   7  ],   # URGENCIA
    [1/3, 1,   3,   5  ],   # IMPACTO_NO_CLIENTE
    [1/5, 1/3, 1,   3  ],   # SENTIMENTO_DO_CLIENTE
    [1/7, 1/5, 1/3, 1  ],   # TEMPO_DE_ESPERA
], dtype=float)

# Índices de consistência aleatória (Saaty)
RI = {1: 0.0, 2: 0.0, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32}


def calcular_pesos_eigenvector(matriz: np.ndarray) -> tuple:
    """Retorna (pesos normalizados, lambda_max, CI, CR)."""
    n = matriz.shape[0]
    col_sums = matriz.sum(axis=0)
    norm = matriz / col_sums
    pesos = norm.mean(axis=1)

    # Consistência
    weighted = matriz @ pesos
    lambdas = weighted / pesos
    lambda_max = lambdas.mean()
    ci = (lambda_max - n) / (n - 1)
    cr = ci / RI.get(n, 1.12)

    return pesos, lambda_max, ci, cr


# Pesos dos critérios calculados
PESOS_CRITERIOS_ARR, LAMBDA_MAX_C, CI_C, CR_C = calcular_pesos_eigenvector(MATRIZ_CRITERIOS)
PESOS_CRITERIOS = dict(zip(CRITERIOS, PESOS_CRITERIOS_ARR))

# ---------------------------------------------------------------------------
# Intensidades e pesos locais por critério
# ---------------------------------------------------------------------------

INTENSIDADES_ORDEM = ["ausente", "baixa", "moderada", "alta", "critica"]

# Matrizes de comparação par-a-par das intensidades (5x5) por critério.
# Usamos a mesma escala para todos os critérios (critério é o mesmo).
MATRIZ_INTENSIDADES = np.array([
    [1,   1/5, 1/7, 1/9, 1/9],  # ausente
    [5,   1,   1/3, 1/5, 1/7],  # baixa
    [7,   3,   1,   1/3, 1/5],  # moderada
    [9,   5,   3,   1,   1/3],  # alta
    [9,   7,   5,   3,   1  ],  # critica
], dtype=float)

PESOS_INT_ARR, _, _, _ = calcular_pesos_eigenvector(MATRIZ_INTENSIDADES)
PESOS_INTENSIDADES_BASE = dict(zip(INTENSIDADES_ORDEM, PESOS_INT_ARR))

# Pesos de intensidade são os mesmos para todos os critérios nesta versão
PRIORIDADES_POR_CRITERIO = {c: dict(PESOS_INTENSIDADES_BASE) for c in CRITERIOS}

# ---------------------------------------------------------------------------
# Síntese AHP — P(a)
# ---------------------------------------------------------------------------

def compute_p(intensidades_escolhidas: dict) -> tuple:
    """
    intensidades_escolhidas: {criterio_codigo: intensidade_codigo}
    Retorna (P_total, contribuicoes_dict)
    """
    contribuicoes = {}
    p_total = 0.0
    for criterio, peso in PESOS_CRITERIOS.items():
        intensidade = intensidades_escolhidas.get(criterio, "ausente")
        p_int = PRIORIDADES_POR_CRITERIO[criterio].get(intensidade, 0.0)
        contrib = peso * p_int
        contribuicoes[criterio] = contrib
        p_total += contrib
    return p_total, contribuicoes


def compute_p_max() -> float:
    return sum(
        peso * max(PRIORIDADES_POR_CRITERIO[c].values())
        for c, peso in PESOS_CRITERIOS.items()
    )


def normalizar_indice(p: float, p_max: float) -> float:
    """Converte P(a) para índice 0–100."""
    return round((p / p_max) * 100, 2) if p_max > 0 else 0.0


# Fronteiras reais do backend (VersaoAHP v1)
MARGEM_TRANSICAO = 3.0
_FRONTEIRAS_BANDA = (80.0, 60.0, 35.0)


def classificar_banda(indice: float) -> str:
    """Classifica pelo índice sem considerar zona de transição."""
    if indice >= 80:
        return "P1 — Crítica"
    elif indice >= 60:
        return "P2 — Alta"
    elif indice >= 35:
        return "P3 — Média"
    else:
        return "P4 — Baixa"


def fronteira_mais_proxima(indice: float) -> float | None:
    """Retorna a fronteira mais próxima se o índice estiver dentro de MARGEM_TRANSICAO, senão None."""
    for f in _FRONTEIRAS_BANDA:
        if abs(indice - f) <= MARGEM_TRANSICAO:
            return f
    return None


def classificar_banda_com_zona(indice: float) -> str:
    """Classifica considerando zona de transição fuzzy: retorna 'REVISAO_HUMANA'
    se o índice estiver a menos de MARGEM_TRANSICAO pontos de qualquer fronteira."""
    if fronteira_mais_proxima(indice) is not None:
        return "REVISAO_HUMANA"
    return classificar_banda(indice)


def compute_p_fuzzy(intensidades_escolhidas: dict, confiancas: dict, alpha: float = 0.20) -> tuple:
    """
    Extensão fuzzy ponderada por confiança.
    Retorna (P_l, P_m, P_u, contribuicoes_fuzzy)
    """
    p_l = p_m = p_u = 0.0
    contribs = {}
    for criterio, peso in PESOS_CRITERIOS.items():
        intensidade = intensidades_escolhidas.get(criterio, "ausente")
        priors = PRIORIDADES_POR_CRITERIO[criterio]
        m = priors.get(intensidade, 0.0)
        c = float(confiancas.get(criterio, 1.0))
        p_max_c = max(priors.values())
        spread = alpha * (1.0 - c)
        l = max(0.0, m - spread)
        u = min(p_max_c, m + spread)
        contribs[criterio] = (peso * l, peso * m, peso * u)
        p_l += peso * l
        p_m += peso * m
        p_u += peso * u
    return p_l, p_m, p_u, contribs


P_MAX = compute_p_max()
