"""
graficos_qualidade.py — Gráficos de qualidade do algoritmo AHP.

Gera 5 gráficos salvos em saida/:
  7. sensibilidade_criterios.png  — Barras de mudanças por perturbação de peso
  8. distribuicao_bandas.png      — Pizza da distribuição esperada das bandas
  9. fronteira_indice.png         — Scatter dos casos próximos de fronteira
 10. comparacao_baselines.png     — Heatmap AHP vs Média vs Regras
 11. urgencia_impacto_heatmap.png — Heatmap índice por Urgência × Impacto
"""

import itertools
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns

from ahp_core import (
    CRITERIOS, PESOS_CRITERIOS, PRIORIDADES_POR_CRITERIO,
    INTENSIDADES_ORDEM, compute_p, normalizar_indice, classificar_banda, P_MAX,
)
from cenarios_teste import CENARIOS
from analise_qualidade import (
    _perturbar_pesos, _classificar_com_pesos,
    _baseline_media_simples, _baseline_regras,
)

SAIDA = os.path.join(os.path.dirname(__file__), "saida")
os.makedirs(SAIDA, exist_ok=True)

PALETTE = {
    "P1 — Crítica": "#ef4444",
    "P2 — Alta":    "#f97316",
    "P3 — Média":   "#eab308",
    "P4 — Baixa":   "#22c55e",
}
PALETTE_NUM = {"P1 — Crítica": 4, "P2 — Alta": 3, "P3 — Média": 2, "P4 — Baixa": 1}

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.dpi": 120,
})


# ── 7. Sensibilidade dos critérios ──────────────────────────────────────────
def grafico_sensibilidade():
    deltas = [-0.20, -0.10, +0.10, +0.20]
    delta_labels = ["-20pp", "-10pp", "+10pp", "+20pp"]
    crit_labels = [c.replace("_", "\n") for c in CRITERIOS]
    cores_delta = ["#ef4444", "#f97316", "#3b82f6", "#6366f1"]

    n_crit = len(CRITERIOS)
    n_delta = len(deltas)
    data = np.zeros((n_crit, n_delta))

    for i, criterio in enumerate(CRITERIOS):
        for j, delta in enumerate(deltas):
            pesos_alt = _perturbar_pesos(criterio, delta)
            mudancas = sum(
                1 for c in CENARIOS
                if classificar_banda(normalizar_indice(compute_p(c["intensidades"])[0], P_MAX))
                != _classificar_com_pesos(pesos_alt, c["intensidades"])
            )
            data[i, j] = mudancas

    x = np.arange(n_crit)
    width = 0.18
    fig, ax = plt.subplots(figsize=(10, 5))

    for j, (dlbl, cor) in enumerate(zip(delta_labels, cores_delta)):
        offset = (j - 1.5) * width
        bars = ax.bar(x + offset, data[:, j], width, label=dlbl, color=cor, alpha=0.85, zorder=2)
        for bar in bars:
            h = bar.get_height()
            if h > 0:
                ax.text(bar.get_x() + bar.get_width() / 2, h + 0.05,
                        str(int(h)), ha="center", va="bottom", fontsize=8)

    ax.set_xticks(x)
    ax.set_xticklabels(crit_labels, fontsize=9)
    ax.set_ylabel("Nº de cenários que mudam de banda", fontsize=10)
    ax.set_title("Sensibilidade dos Pesos — Impacto nas Classificações\n"
                 "(de 12 cenários testados)", fontsize=12, fontweight="bold", pad=12)
    ax.yaxis.grid(True, linestyle="--", alpha=0.4, zorder=0)
    ax.set_ylim(0, 12)
    ax.legend(title="Variação do peso", fontsize=9)
    fig.tight_layout()
    path = os.path.join(SAIDA, "sensibilidade_criterios.png")
    fig.savefig(path)
    plt.close(fig)
    print(f"  ✓ {path}")


# ── 8. Distribuição esperada das bandas ─────────────────────────────────────
def grafico_distribuicao_bandas():
    contagem = {b: 0 for b in PALETTE}
    for combo in itertools.product(INTENSIDADES_ORDEM, repeat=len(CRITERIOS)):
        intensidades = dict(zip(CRITERIOS, combo))
        p, _ = compute_p(intensidades)
        banda = classificar_banda(normalizar_indice(p, P_MAX))
        contagem[banda] += 1

    labels = list(PALETTE.keys())
    sizes = [contagem[b] for b in labels]
    cores = [PALETTE[b] for b in labels]
    explode = [0.04] * len(labels)

    fig, ax = plt.subplots(figsize=(7, 6))
    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, autopct="%1.1f%%",
        colors=cores, explode=explode, startangle=90,
        wedgeprops={"linewidth": 1.2, "edgecolor": "white"},
    )
    for at in autotexts:
        at.set_fontsize(10)
    total = sum(sizes)
    ax.set_title(f"Distribuição Esperada das Bandas\n"
                 f"({total} combinações possíveis de intensidades)",
                 fontsize=12, fontweight="bold", pad=14)
    fig.tight_layout()
    path = os.path.join(SAIDA, "distribuicao_bandas.png")
    fig.savefig(path)
    plt.close(fig)
    print(f"  ✓ {path}")


# ── 9. Fronteira — scatter dos índices ──────────────────────────────────────
def grafico_fronteira_scatter():
    # Calcular todos os índices possíveis
    indices_por_banda = {b: [] for b in PALETTE}
    for combo in itertools.product(INTENSIDADES_ORDEM, repeat=len(CRITERIOS)):
        intensidades = dict(zip(CRITERIOS, combo))
        p, _ = compute_p(intensidades)
        idx = normalizar_indice(p, P_MAX)
        banda = classificar_banda(idx)
        indices_por_banda[banda].append(idx)

    fig, ax = plt.subplots(figsize=(10, 4.5))
    y_jitter_seed = 0
    for i, (banda, idxs) in enumerate(indices_por_banda.items()):
        if not idxs:
            continue
        np.random.seed(y_jitter_seed + i)
        y = np.random.uniform(i - 0.3, i + 0.3, len(idxs))
        ax.scatter(idxs, y, color=PALETTE[banda], alpha=0.35, s=12, zorder=2)

    # Linhas de fronteira
    for xval, lbl in [(80, "P1/P2"), (60, "P2/P3"), (35, "P3/P4")]:
        ax.axvline(xval, color="#475569", linestyle="--", linewidth=1.5)
        ax.text(xval + 0.5, len(PALETTE) - 0.3, lbl, fontsize=8, color="#475569")

    ax.set_yticks(range(len(PALETTE)))
    ax.set_yticklabels(list(PALETTE.keys()), fontsize=9)
    ax.set_xlabel("Índice AHP (0–100)", fontsize=10)
    ax.set_title("Distribuição dos Índices por Banda — Todas as Combinações",
                 fontsize=12, fontweight="bold", pad=12)
    ax.xaxis.grid(True, linestyle="--", alpha=0.3, zorder=0)
    ax.set_xlim(-2, 105)
    fig.tight_layout()
    path = os.path.join(SAIDA, "fronteira_scatter.png")
    fig.savefig(path)
    plt.close(fig)
    print(f"  ✓ {path}")


# ── 10. Comparação com baselines ─────────────────────────────────────────────
def grafico_comparacao_baselines():
    nomes = [f"#{i+1} {c['nome'][:28]}" for i, c in enumerate(CENARIOS)]
    bandas_ahp, bandas_media, bandas_regras = [], [], []

    for c in CENARIOS:
        p, _ = compute_p(c["intensidades"])
        idx = normalizar_indice(p, P_MAX)
        bandas_ahp.append(PALETTE_NUM[classificar_banda(idx)])
        bandas_media.append(PALETTE_NUM[_baseline_media_simples(c["intensidades"])])
        bandas_regras.append(PALETTE_NUM[_baseline_regras(c["intensidades"])])

    data = np.array([bandas_ahp, bandas_media, bandas_regras])

    fig, ax = plt.subplots(figsize=(13, 5))
    cmap = matplotlib.colors.ListedColormap(["#22c55e", "#eab308", "#f97316", "#ef4444"])
    im = ax.imshow(data, aspect="auto", cmap=cmap, vmin=0.5, vmax=4.5)

    ax.set_yticks([0, 1, 2])
    ax.set_yticklabels(["AHP (sistema)", "Média Simples", "Regras Fixas"], fontsize=10)
    ax.set_xticks(range(len(nomes)))
    ax.set_xticklabels(nomes, rotation=45, ha="right", fontsize=7.5)
    ax.set_title("Comparação: AHP × Média Simples × Regras Fixas\n"
                 "(verde=P4, amarelo=P3, laranja=P2, vermelho=P1)",
                 fontsize=12, fontweight="bold", pad=12)

    # Marcar discordâncias
    for j in range(len(CENARIOS)):
        if bandas_media[j] != bandas_ahp[j]:
            ax.add_patch(plt.Rectangle((j - 0.5, 0.5), 1, 1,
                                       fill=False, edgecolor="black", linewidth=2))
        if bandas_regras[j] != bandas_ahp[j]:
            ax.add_patch(plt.Rectangle((j - 0.5, 1.5), 1, 1,
                                       fill=False, edgecolor="black", linewidth=2))

    ax.text(1.01, 0.5, "□ = discorda do AHP", transform=ax.transAxes,
            fontsize=8, va="center")
    fig.tight_layout()
    path = os.path.join(SAIDA, "comparacao_baselines.png")
    fig.savefig(path)
    plt.close(fig)
    print(f"  ✓ {path}")


# ── 11. Heatmap índice por Urgência × Impacto ────────────────────────────────
def grafico_heatmap_urgencia_impacto():
    # Fixar Sentimento=moderada e Tempo=moderada, variar Urgência e Impacto
    matriz = np.zeros((len(INTENSIDADES_ORDEM), len(INTENSIDADES_ORDEM)))
    for i, urg in enumerate(INTENSIDADES_ORDEM):
        for j, imp in enumerate(INTENSIDADES_ORDEM):
            intensidades = {
                "URGENCIA": urg,
                "IMPACTO_NO_CLIENTE": imp,
                "SENTIMENTO_DO_CLIENTE": "moderada",
                "TEMPO_DE_ESPERA": "moderada",
            }
            p, _ = compute_p(intensidades)
            matriz[i, j] = normalizar_indice(p, P_MAX)

    labels = [i.capitalize() for i in INTENSIDADES_ORDEM]
    fig, ax = plt.subplots(figsize=(7, 5.5))
    sns.heatmap(
        matriz, annot=True, fmt=".1f", cmap="RdYlGn_r",
        xticklabels=labels, yticklabels=labels,
        linewidths=0.5, ax=ax, vmin=0, vmax=100,
        cbar_kws={"label": "Índice AHP (0–100)"},
    )
    ax.set_xlabel("Impacto no Cliente", fontsize=10)
    ax.set_ylabel("Urgência", fontsize=10)
    ax.set_title("Índice AHP: Urgência × Impacto\n"
                 "(Sentimento=Moderada, Tempo=Moderada)",
                 fontsize=12, fontweight="bold", pad=12)

    # Contornos das bandas
    for limiar in [80, 60, 35]:
        for i in range(len(INTENSIDADES_ORDEM)):
            for j in range(len(INTENSIDADES_ORDEM)):
                v = matriz[i, j]
                if abs(v - limiar) < 6:
                    ax.add_patch(plt.Rectangle((j, i), 1, 1,
                                               fill=False, edgecolor="black",
                                               linewidth=1.5, linestyle="--"))

    fig.tight_layout()
    path = os.path.join(SAIDA, "heatmap_urgencia_impacto.png")
    fig.savefig(path)
    plt.close(fig)
    print(f"  ✓ {path}")


if __name__ == "__main__":
    print("\n" + "█" * 60)
    print("  CHAM.IA — Gerando Gráficos de Qualidade AHP")
    print("█" * 60 + "\n")

    grafico_sensibilidade()
    grafico_distribuicao_bandas()
    grafico_fronteira_scatter()
    grafico_comparacao_baselines()
    grafico_heatmap_urgencia_impacto()

    print(f"\n  ✓ 5 gráficos salvos em: {SAIDA}/\n")
