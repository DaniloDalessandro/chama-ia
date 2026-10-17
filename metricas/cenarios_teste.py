"""
cenarios_teste.py — Testes de cenários AHP com tabelas de resultado.

Executa 12 cenários representativos do sistema de chamados e imprime:
  - Tabela de pesos dos critérios
  - Tabela de pesos das intensidades
  - Resultados de cada cenário com índice e banda P1-P4
  - Análise fuzzy com baixa confiança
"""

from tabulate import tabulate
from ahp_core import (
    CRITERIOS, PESOS_CRITERIOS, PESOS_INTENSIDADES_BASE,
    INTENSIDADES_ORDEM, MATRIZ_CRITERIOS, LAMBDA_MAX_C, CI_C, CR_C,
    compute_p, normalizar_indice, classificar_banda, compute_p_fuzzy, P_MAX,
)

SEP = "=" * 70


def tabela_pesos_criterios():
    print(f"\n{SEP}")
    print("  TABELA 1 — Pesos dos Critérios (Eigenvector AHP)")
    print(SEP)
    rows = [
        [c, f"{PESOS_CRITERIOS[c]:.4f}", f"{PESOS_CRITERIOS[c]*100:.1f}%"]
        for c in CRITERIOS
    ]
    print(tabulate(rows, headers=["Critério", "Peso (w)", "Peso (%)"],
                   tablefmt="rounded_outline"))
    print(f"  λ_max = {LAMBDA_MAX_C:.4f}  |  CI = {CI_C:.4f}  |  CR = {CR_C:.4f}",
          "✓ Consistente" if CR_C < 0.10 else "✗ Inconsistente")


def tabela_pesos_intensidades():
    print(f"\n{SEP}")
    print("  TABELA 2 — Pesos das Intensidades (mesmos para todos os critérios)")
    print(SEP)
    rows = [
        [i.capitalize(), f"{PESOS_INTENSIDADES_BASE[i]:.4f}", f"{PESOS_INTENSIDADES_BASE[i]*100:.1f}%"]
        for i in INTENSIDADES_ORDEM
    ]
    print(tabulate(rows, headers=["Intensidade", "Peso (p)", "Peso (%)"],
                   tablefmt="rounded_outline"))


def tabela_matriz_criterios():
    print(f"\n{SEP}")
    print("  TABELA 3 — Matriz de Comparação Par-a-Par (Critérios)")
    print(SEP)
    labels = ["URGENCIA", "IMPACTO", "SENTIMENTO", "TEMPO"]
    rows = []
    for i, lbl in enumerate(labels):
        row = [lbl] + [f"{MATRIZ_CRITERIOS[i, j]:.3f}" for j in range(len(labels))]
        rows.append(row)
    print(tabulate(rows, headers=[""] + labels, tablefmt="rounded_outline"))


def tabela_bandas():
    print(f"\n{SEP}")
    print("  TABELA 4 — Bandas de Prioridade (P1–P4)")
    print(SEP)
    rows = [
        ["P1 — Crítica",  "≥ 75",  "Atenção imediata"],
        ["P2 — Alta",     "50–74", "Alta prioridade"],
        ["P3 — Média",    "25–49", "Prioridade padrão"],
        ["P4 — Baixa",    "< 25",  "Baixa prioridade"],
    ]
    print(tabulate(rows, headers=["Banda", "Índice AHP", "Descrição"],
                   tablefmt="rounded_outline"))
    print(f"  P_max teórico = {P_MAX:.4f}")


CENARIOS = [
    {
        "nome": "Sistema fora do ar (bloqueio total)",
        "intensidades": {"URGENCIA": "critica", "IMPACTO_NO_CLIENTE": "critica",
                         "SENTIMENTO_DO_CLIENTE": "critica", "TEMPO_DE_ESPERA": "alta"},
        "confiancas": {"URGENCIA": 0.95, "IMPACTO_NO_CLIENTE": 0.90,
                       "SENTIMENTO_DO_CLIENTE": 0.85, "TEMPO_DE_ESPERA": 1.0},
    },
    {
        "nome": "Erro crítico em produção",
        "intensidades": {"URGENCIA": "critica", "IMPACTO_NO_CLIENTE": "alta",
                         "SENTIMENTO_DO_CLIENTE": "alta", "TEMPO_DE_ESPERA": "moderada"},
        "confiancas": {"URGENCIA": 0.90, "IMPACTO_NO_CLIENTE": 0.85,
                       "SENTIMENTO_DO_CLIENTE": 0.80, "TEMPO_DE_ESPERA": 1.0},
    },
    {
        "nome": "Falha parcial com cliente frustrado",
        "intensidades": {"URGENCIA": "alta", "IMPACTO_NO_CLIENTE": "alta",
                         "SENTIMENTO_DO_CLIENTE": "alta", "TEMPO_DE_ESPERA": "moderada"},
        "confiancas": {"URGENCIA": 0.80, "IMPACTO_NO_CLIENTE": 0.75,
                       "SENTIMENTO_DO_CLIENTE": 0.90, "TEMPO_DE_ESPERA": 1.0},
    },
    {
        "nome": "Nota fiscal incorreta urgente",
        "intensidades": {"URGENCIA": "alta", "IMPACTO_NO_CLIENTE": "moderada",
                         "SENTIMENTO_DO_CLIENTE": "alta", "TEMPO_DE_ESPERA": "alta"},
        "confiancas": {"URGENCIA": 0.85, "IMPACTO_NO_CLIENTE": 0.70,
                       "SENTIMENTO_DO_CLIENTE": 0.80, "TEMPO_DE_ESPERA": 1.0},
    },
    {
        "nome": "Problema de acesso com espera longa",
        "intensidades": {"URGENCIA": "moderada", "IMPACTO_NO_CLIENTE": "alta",
                         "SENTIMENTO_DO_CLIENTE": "moderada", "TEMPO_DE_ESPERA": "critica"},
        "confiancas": {"URGENCIA": 0.75, "IMPACTO_NO_CLIENTE": 0.80,
                       "SENTIMENTO_DO_CLIENTE": 0.70, "TEMPO_DE_ESPERA": 1.0},
    },
    {
        "nome": "Lentidão no sistema",
        "intensidades": {"URGENCIA": "moderada", "IMPACTO_NO_CLIENTE": "moderada",
                         "SENTIMENTO_DO_CLIENTE": "moderada", "TEMPO_DE_ESPERA": "moderada"},
        "confiancas": {"URGENCIA": 0.80, "IMPACTO_NO_CLIENTE": 0.75,
                       "SENTIMENTO_DO_CLIENTE": 0.70, "TEMPO_DE_ESPERA": 1.0},
    },
    {
        "nome": "Dúvida sobre funcionalidade",
        "intensidades": {"URGENCIA": "baixa", "IMPACTO_NO_CLIENTE": "baixa",
                         "SENTIMENTO_DO_CLIENTE": "baixa", "TEMPO_DE_ESPERA": "baixa"},
        "confiancas": {"URGENCIA": 0.90, "IMPACTO_NO_CLIENTE": 0.90,
                       "SENTIMENTO_DO_CLIENTE": 0.90, "TEMPO_DE_ESPERA": 1.0},
    },
    {
        "nome": "Solicitação de relatório simples",
        "intensidades": {"URGENCIA": "baixa", "IMPACTO_NO_CLIENTE": "baixa",
                         "SENTIMENTO_DO_CLIENTE": "ausente", "TEMPO_DE_ESPERA": "baixa"},
        "confiancas": {"URGENCIA": 0.95, "IMPACTO_NO_CLIENTE": 0.90,
                       "SENTIMENTO_DO_CLIENTE": 0.85, "TEMPO_DE_ESPERA": 1.0},
    },
    {
        "nome": "Urgência máxima + cliente em pânico",
        "intensidades": {"URGENCIA": "critica", "IMPACTO_NO_CLIENTE": "critica",
                         "SENTIMENTO_DO_CLIENTE": "critica", "TEMPO_DE_ESPERA": "critica"},
        "confiancas": {"URGENCIA": 1.0, "IMPACTO_NO_CLIENTE": 1.0,
                       "SENTIMENTO_DO_CLIENTE": 1.0, "TEMPO_DE_ESPERA": 1.0},
    },
    {
        "nome": "Impacto alto, urgência baixa",
        "intensidades": {"URGENCIA": "baixa", "IMPACTO_NO_CLIENTE": "critica",
                         "SENTIMENTO_DO_CLIENTE": "moderada", "TEMPO_DE_ESPERA": "baixa"},
        "confiancas": {"URGENCIA": 0.85, "IMPACTO_NO_CLIENTE": 0.90,
                       "SENTIMENTO_DO_CLIENTE": 0.75, "TEMPO_DE_ESPERA": 1.0},
    },
    {
        "nome": "Tempo de espera crítico, problema leve",
        "intensidades": {"URGENCIA": "baixa", "IMPACTO_NO_CLIENTE": "baixa",
                         "SENTIMENTO_DO_CLIENTE": "moderada", "TEMPO_DE_ESPERA": "critica"},
        "confiancas": {"URGENCIA": 0.90, "IMPACTO_NO_CLIENTE": 0.85,
                       "SENTIMENTO_DO_CLIENTE": 0.80, "TEMPO_DE_ESPERA": 1.0},
    },
    {
        "nome": "Chamado sem dados suficientes (confiança baixa)",
        "intensidades": {"URGENCIA": "moderada", "IMPACTO_NO_CLIENTE": "moderada",
                         "SENTIMENTO_DO_CLIENTE": "baixa", "TEMPO_DE_ESPERA": "moderada"},
        "confiancas": {"URGENCIA": 0.40, "IMPACTO_NO_CLIENTE": 0.35,
                       "SENTIMENTO_DO_CLIENTE": 0.30, "TEMPO_DE_ESPERA": 1.0},
    },
]


def tabela_cenarios():
    print(f"\n{SEP}")
    print("  TABELA 5 — Cenários de Teste com Índice AHP e Banda")
    print(SEP)
    rows = []
    for i, c in enumerate(CENARIOS, 1):
        p, _ = compute_p(c["intensidades"])
        indice = normalizar_indice(p, P_MAX)
        banda = classificar_banda(indice)
        urg = c["intensidades"]["URGENCIA"].capitalize()
        imp = c["intensidades"]["IMPACTO_NO_CLIENTE"].capitalize()
        sent = c["intensidades"]["SENTIMENTO_DO_CLIENTE"].capitalize()
        tempo = c["intensidades"]["TEMPO_DE_ESPERA"].capitalize()
        rows.append([i, c["nome"][:38], urg, imp, sent, tempo,
                     f"{indice:.1f}", banda])
    headers = ["#", "Cenário", "Urgência", "Impacto", "Sentimento", "Tempo",
               "Índice", "Banda"]
    print(tabulate(rows, headers=headers, tablefmt="rounded_outline"))


def tabela_fuzzy():
    print(f"\n{SEP}")
    print("  TABELA 6 — Análise Fuzzy (Incerteza do LLM) — 4 cenários selecionados")
    print(SEP)
    selecionados = [0, 5, 8, 11]
    rows = []
    for i in selecionados:
        c = CENARIOS[i]
        p, _ = compute_p(c["intensidades"])
        p_l, p_m, p_u, _ = compute_p_fuzzy(c["intensidades"], c["confiancas"])
        idx_l = normalizar_indice(p_l, P_MAX)
        idx_m = normalizar_indice(p_m, P_MAX)
        idx_u = normalizar_indice(p_u, P_MAX)
        conf_media = sum(c["confiancas"].values()) / len(c["confiancas"])
        rows.append([
            c["nome"][:35],
            f"{conf_media:.0%}",
            f"{idx_l:.1f}",
            f"{idx_m:.1f}",
            f"{idx_u:.1f}",
            f"±{(idx_u - idx_l)/2:.1f}",
            classificar_banda(idx_m),
        ])
    headers = ["Cenário", "Conf. Média", "Idx_min", "Idx_central", "Idx_max", "Margem", "Banda"]
    print(tabulate(rows, headers=headers, tablefmt="rounded_outline"))


def tabela_contribuicoes():
    print(f"\n{SEP}")
    print("  TABELA 7 — Contribuição por Critério (3 cenários extremos)")
    print(SEP)
    for idx in [0, 6, 8]:
        c = CENARIOS[idx]
        p, contribs = compute_p(c["intensidades"])
        indice = normalizar_indice(p, P_MAX)
        print(f"\n  Cenário: {c['nome']}  →  Índice = {indice:.1f}  ({classificar_banda(indice)})")
        rows = [
            [crit, c["intensidades"][crit].capitalize(),
             f"{PESOS_CRITERIOS[crit]:.3f}",
             f"{contribs[crit]:.4f}",
             f"{(contribs[crit]/p*100):.1f}%"]
            for crit in CRITERIOS
        ]
        print(tabulate(rows, headers=["Critério", "Intensidade", "Peso w", "Contrib.", "%"],
                       tablefmt="simple"))


if __name__ == "__main__":
    print("\n" + "█" * 70)
    print("  CHAM.IA — ANÁLISE DE MÉTRICAS AHP")
    print("  Sistema de Priorização de Chamados por Mensuração Absoluta")
    print("█" * 70)

    tabela_pesos_criterios()
    tabela_pesos_intensidades()
    tabela_matriz_criterios()
    tabela_bandas()
    tabela_cenarios()
    tabela_fuzzy()
    tabela_contribuicoes()

    print(f"\n{'=' * 70}")
    print("  Concluído. Execute graficos.py para gerar os gráficos.")
    print("=" * 70 + "\n")
