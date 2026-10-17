"""
graficos.py — Geração de gráficos AHP para o sistema Cham.IA.

Gera 6 gráficos salvos em saida/:
  1. pesos_criterios.png       — Barras dos pesos dos critérios
  2. pesos_intensidades.png    — Barras dos pesos das intensidades
  3. matriz_criterios.png      — Heatmap da matriz de comparação
  4. cenarios_indice.png       — Barras horizontais dos 12 cenários
  5. cenarios_fuzzy.png        — Barras com intervalo fuzzy (4 cenários)
  6. contribuicoes_pizza.png   — Pizza de contribuição (cenário crítico)
"""

import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns

from ahp_core import (
    CRITERIOS, PESOS_CRITERIOS, PESOS_INTENSIDADES_BASE,
    INTENSIDADES_ORDEM, MATRIZ_CRITERIOS,
    compute_p, normalizar_indice, classificar_banda,
    compute_p_fuzzy, P_MAX,
)
from cenarios_teste import CENARIOS

SAIDA = os.path.join(os.path.dirname(__file__), "saida")
os.makedirs(SAIDA, exist_ok=True)

PALETTE = {
    "P1 — Crítica": "#ef4444",
    "P2 — Alta":    "#f97316",
    "P3 — Média":   "#eab308",
    "P4 — Baixa":   "#22c55e",
}

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.dpi": 120,
})


# ── 1. Pesos dos critérios ──────────────────────────────────────────────────
def grafico_pesos_criterios():
    labels = [c.replace("_", "\n") for c in CRITERIOS]
    valores = [PESOS_CRITERIOS[c] for c in CRITERIOS]
    cores = ["#3b82f6", "#8b5cf6", "#ec4899", "#14b8a6"]

    fig, ax = plt.subplots(figsize=(8, 4.5))
    bars = ax.bar(labels, valores, color=cores, width=0.5, zorder=2)
    ax.set_title("Pesos dos Critérios — AHP (Eigenvector)", fontsize=13, fontweight="bold", pad=12)
    ax.set_ylabel("Peso (w)", fontsize=10)
    ax.yaxis.grid(True, linestyle="--", alpha=0.5, zorder=0)
    for bar, val in zip(bars, valores):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.005,
                f"{val:.3f}\n({val*100:.1f}%)", ha="center", va="bottom", fontsize=9)
    ax.set_ylim(0, max(valores) * 1.25)
    fig.tight_layout()
    path = os.path.join(SAIDA, "pesos_criterios.png")
    fig.savefig(path)
    plt.close(fig)
    print(f"  ✓ {path}")


# ── 2. Pesos das intensidades ───────────────────────────────────────────────
def grafico_pesos_intensidades():
    labels = [i.capitalize() for i in INTENSIDADES_ORDEM]
    valores = [PESOS_INTENSIDADES_BASE[i] for i in INTENSIDADES_ORDEM]
    cores = ["#94a3b8", "#22c55e", "#eab308", "#f97316", "#ef4444"]

    fig, ax = plt.subplots(figsize=(8, 4.5))
    bars = ax.bar(labels, valores, color=cores, width=0.5, zorder=2)
    ax.set_title("Pesos das Intensidades — Escala AHP", fontsize=13, fontweight="bold", pad=12)
    ax.set_ylabel("Peso local (p)", fontsize=10)
    ax.yaxis.grid(True, linestyle="--", alpha=0.5, zorder=0)
    for bar, val in zip(bars, valores):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.002,
                f"{val:.3f}", ha="center", va="bottom", fontsize=9)
    ax.set_ylim(0, max(valores) * 1.25)
    fig.tight_layout()
    path = os.path.join(SAIDA, "pesos_intensidades.png")
    fig.savefig(path)
    plt.close(fig)
    print(f"  ✓ {path}")


# ── 3. Heatmap da matriz de comparação ─────────────────────────────────────
def grafico_matriz_criterios():
    labels = ["Urgência", "Impacto", "Sentimento", "Tempo"]
    fig, ax = plt.subplots(figsize=(7, 5.5))
    mask = np.zeros_like(MATRIZ_CRITERIOS, dtype=bool)
    sns.heatmap(
        MATRIZ_CRITERIOS, annot=True, fmt=".2f", cmap="Blues",
        xticklabels=labels, yticklabels=labels,
        linewidths=0.5, ax=ax, cbar_kws={"label": "Valor Saaty"},
    )
    ax.set_title("Matriz de Comparação Par-a-Par — Critérios", fontsize=12, fontweight="bold", pad=12)
    fig.tight_layout()
    path = os.path.join(SAIDA, "matriz_criterios.png")
    fig.savefig(path)
    plt.close(fig)
    print(f"  ✓ {path}")


# ── 4. Barras horizontais dos 12 cenários ──────────────────────────────────
def grafico_cenarios_indice():
    nomes = [c["nome"] for c in CENARIOS]
    indices = []
    bandas = []
    for c in CENARIOS:
        p, _ = compute_p(c["intensidades"])
        idx = normalizar_indice(p, P_MAX)
        indices.append(idx)
        bandas.append(classificar_banda(idx))

    cores = [PALETTE[b] for b in bandas]

    fig, ax = plt.subplots(figsize=(11, 7))
    y_pos = range(len(nomes))
    bars = ax.barh(y_pos, indices, color=cores, height=0.6, zorder=2)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(nomes, fontsize=8.5)
    ax.set_xlabel("Índice AHP (0–100)", fontsize=10)
    ax.set_title("Índice de Prioridade — 12 Cenários de Teste", fontsize=13, fontweight="bold", pad=12)
    ax.xaxis.grid(True, linestyle="--", alpha=0.4, zorder=0)

    # Linhas de referência das bandas
    for xval, lbl, cor in [(80, "P1", "#ef4444"), (60, "P2", "#f97316"), (35, "P3", "#eab308")]:
        ax.axvline(xval, color=cor, linestyle="--", linewidth=1.2, alpha=0.7)
        ax.text(xval + 0.5, len(nomes) - 0.5, lbl, color=cor, fontsize=8, va="top")

    for bar, idx in zip(bars, indices):
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
                f"{idx:.1f}", va="center", fontsize=8)

    legendas = [mpatches.Patch(color=v, label=k) for k, v in PALETTE.items()]
    ax.legend(handles=legendas, loc="lower right", fontsize=8)
    ax.set_xlim(0, 105)
    ax.invert_yaxis()
    fig.tight_layout()
    path = os.path.join(SAIDA, "cenarios_indice.png")
    fig.savefig(path)
    plt.close(fig)
    print(f"  ✓ {path}")


# ── 5. Fuzzy — intervalo de incerteza ──────────────────────────────────────
def grafico_cenarios_fuzzy():
    selecionados = [0, 5, 8, 11]
    nomes, idx_l_list, idx_m_list, idx_u_list = [], [], [], []
    bandas = []

    for i in selecionados:
        c = CENARIOS[i]
        p_l, p_m, p_u, _ = compute_p_fuzzy(c["intensidades"], c["confiancas"])
        nomes.append(c["nome"][:40])
        idx_l_list.append(normalizar_indice(p_l, P_MAX))
        idx_m_list.append(normalizar_indice(p_m, P_MAX))
        idx_u_list.append(normalizar_indice(p_u, P_MAX))
        bandas.append(classificar_banda(normalizar_indice(p_m, P_MAX)))

    y_pos = np.arange(len(nomes))
    errs_l = [m - l for m, l in zip(idx_m_list, idx_l_list)]
    errs_u = [u - m for u, m in zip(idx_u_list, idx_m_list)]
    cores = [PALETTE[b] for b in bandas]

    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.barh(y_pos, idx_m_list, xerr=[errs_l, errs_u], color=cores, height=0.5,
            error_kw={"ecolor": "#475569", "capsize": 6, "capthick": 1.5}, zorder=2)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(nomes, fontsize=9)
    ax.set_xlabel("Índice AHP (0–100)", fontsize=10)
    ax.set_title("Análise Fuzzy — Intervalo de Incerteza do LLM", fontsize=13, fontweight="bold", pad=12)
    ax.xaxis.grid(True, linestyle="--", alpha=0.4, zorder=0)

    for xval, lbl, cor in [(80, "P1", "#ef4444"), (60, "P2", "#f97316"), (35, "P3", "#eab308")]:
        ax.axvline(xval, color=cor, linestyle="--", linewidth=1.2, alpha=0.7)

    ax.set_xlim(0, 105)
    ax.invert_yaxis()
    fig.tight_layout()
    path = os.path.join(SAIDA, "cenarios_fuzzy.png")
    fig.savefig(path)
    plt.close(fig)
    print(f"  ✓ {path}")


# ── 6. Pizza de contribuição (cenário crítico) ──────────────────────────────
def grafico_contribuicoes_pizza():
    c = CENARIOS[0]
    p, contribs = compute_p(c["intensidades"])
    labels = [cr.replace("_", " ").title() for cr in CRITERIOS]
    valores = [contribs[cr] for cr in CRITERIOS]
    cores = ["#3b82f6", "#8b5cf6", "#ec4899", "#14b8a6"]
    explode = [0.05] * len(CRITERIOS)

    fig, ax = plt.subplots(figsize=(7, 6))
    wedges, texts, autotexts = ax.pie(
        valores, labels=labels, autopct="%1.1f%%",
        colors=cores, explode=explode, startangle=90,
        wedgeprops={"linewidth": 1, "edgecolor": "white"},
    )
    for at in autotexts:
        at.set_fontsize(9)
    ax.set_title(f"Contribuição por Critério\n\"{c['nome']}\"",
                 fontsize=12, fontweight="bold", pad=14)
    fig.tight_layout()
    path = os.path.join(SAIDA, "contribuicoes_pizza.png")
    fig.savefig(path)
    plt.close(fig)
    print(f"  ✓ {path}")


if __name__ == "__main__":
    print("\n" + "█" * 60)
    print("  CHAM.IA — Gerando Gráficos AHP")
    print("█" * 60 + "\n")

    grafico_pesos_criterios()
    grafico_pesos_intensidades()
    grafico_matriz_criterios()
    grafico_cenarios_indice()
    grafico_cenarios_fuzzy()
    grafico_contribuicoes_pizza()

    print(f"\n  ✓ 6 gráficos salvos em: {SAIDA}/\n")
