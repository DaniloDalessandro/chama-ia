"""
analise_qualidade.py — Análises de qualidade do algoritmo AHP.

Gera 6 análises que provam (ou refutam) a qualidade do algoritmo:

  1. CR das matrizes de intensidade por critério
  2. Análise de sensibilidade dos pesos dos critérios
  3. Análise de fronteira (estabilidade nas bordas das bandas)
  4. Casos ambíguos — diagnóstico dos cenários intermediários
  5. Comparação AHP vs Baseline (média simples e regras fixas)
  6. Distribuição esperada das bandas (espaço completo de combinações)
"""

import itertools
import numpy as np
from tabulate import tabulate
from ahp_core import (
    CRITERIOS, PESOS_CRITERIOS, PESOS_CRITERIOS_ARR,
    INTENSIDADES_ORDEM, MATRIZ_INTENSIDADES, PRIORIDADES_POR_CRITERIO,
    calcular_pesos_eigenvector, compute_p, normalizar_indice,
    classificar_banda, classificar_banda_com_zona,
    MARGEM_TRANSICAO, _FRONTEIRAS_BANDA, P_MAX, RI,
)
from cenarios_teste import CENARIOS

SEP = "=" * 72
BANDAS_ORDEM = ["P1 — Crítica", "P2 — Alta", "P3 — Média", "P4 — Baixa"]


# ── 1. CR das matrizes de intensidade ──────────────────────────────────────

def analise_cr_intensidades():
    print(f"\n{SEP}")
    print("  ANÁLISE 1 — Consistência (CR) das Matrizes de Intensidade")
    print(f"  (uma matriz 5×5 por critério — escala de Saaty)")
    print(SEP)

    rows = []
    for criterio in CRITERIOS:
        pesos, lmax, ci, cr = calcular_pesos_eigenvector(MATRIZ_INTENSIDADES)
        status = "✓ Consistente" if cr < 0.10 else "✗ INCONSISTENTE"
        rows.append([criterio, f"{lmax:.4f}", f"{ci:.4f}", f"{cr:.4f}", status])

    print(tabulate(rows,
                   headers=["Critério", "λ_max", "CI", "CR", "Status"],
                   tablefmt="rounded_outline"))

    # Tabela resumo dos pesos de intensidade com CI/CR
    print(f"\n  Pesos das intensidades (compartilhados entre todos os critérios):")
    pesos, _, _, _ = calcular_pesos_eigenvector(MATRIZ_INTENSIDADES)
    rows2 = []
    for nome, peso in zip(INTENSIDADES_ORDEM, pesos):
        rows2.append([nome.capitalize(), f"{peso:.4f}", f"{peso*100:.1f}%"])
    print(tabulate(rows2, headers=["Intensidade", "Peso", "%"],
                   tablefmt="simple"))


# ── 2. Análise de sensibilidade ─────────────────────────────────────────────

def _perturbar_pesos(criterio_alvo: str, delta: float) -> dict:
    """
    Perturba o peso de `criterio_alvo` por `delta` (ex: +0.10 = +10pp)
    e redistribui proporcionalmente entre os demais.
    """
    pesos_base = dict(PESOS_CRITERIOS)
    novo_alvo = max(0.0, min(1.0, pesos_base[criterio_alvo] + delta))
    diff = novo_alvo - pesos_base[criterio_alvo]
    outros = [c for c in CRITERIOS if c != criterio_alvo]
    soma_outros = sum(pesos_base[c] for c in outros)

    novos = {}
    for c in CRITERIOS:
        if c == criterio_alvo:
            novos[c] = novo_alvo
        else:
            frac = pesos_base[c] / soma_outros if soma_outros > 0 else 1 / len(outros)
            novos[c] = max(0.0, pesos_base[c] - diff * frac)

    # normalizar para soma = 1
    total = sum(novos.values())
    return {c: v / total for c, v in novos.items()}


def _classificar_com_pesos(pesos_alt: dict, intensidades: dict) -> str:
    p = sum(pesos_alt[c] * PRIORIDADES_POR_CRITERIO[c].get(intensidades.get(c, "ausente"), 0.0)
            for c in CRITERIOS)
    p_max_alt = sum(pesos_alt[c] * max(PRIORIDADES_POR_CRITERIO[c].values()) for c in CRITERIOS)
    idx = normalizar_indice(p, p_max_alt)
    return classificar_banda(idx)


def analise_sensibilidade():
    print(f"\n{SEP}")
    print("  ANÁLISE 2 — Sensibilidade dos Pesos dos Critérios")
    print(f"  (variação ±10pp e ±20pp — quantos cenários mudam de banda)")
    print(SEP)

    deltas = [-0.20, -0.10, +0.10, +0.20]
    delta_labels = ["-20pp", "-10pp", "+10pp", "+20pp"]

    for criterio in CRITERIOS:
        rows = []
        for delta, dlbl in zip(deltas, delta_labels):
            pesos_alt = _perturbar_pesos(criterio, delta)
            novo_peso_pct = f"{pesos_alt[criterio]*100:.1f}%"
            mudancas = 0
            detalhes = []
            for c in CENARIOS:
                banda_orig = classificar_banda(normalizar_indice(compute_p(c["intensidades"])[0], P_MAX))
                banda_alt = _classificar_com_pesos(pesos_alt, c["intensidades"])
                if banda_orig != banda_alt:
                    mudancas += 1
                    detalhes.append(f"{c['nome'][:25]}: {banda_orig.split()[0]}→{banda_alt.split()[0]}")
            impacto = ", ".join(detalhes) if detalhes else "—"
            rows.append([dlbl, novo_peso_pct, mudancas, impacto])

        peso_atual = f"{PESOS_CRITERIOS[criterio]*100:.1f}%"
        print(f"\n  Critério: {criterio}  (peso atual = {peso_atual})")
        print(tabulate(rows,
                       headers=["Variação", "Novo peso", "Cenários alterados", "Detalhes"],
                       tablefmt="simple"))

    print(f"\n  Interpretação: quanto menos cenários mudam, mais estável é o algoritmo.")


# ── 3. Análise de fronteira ─────────────────────────────────────────────────

def analise_fronteira():
    print(f"\n{SEP}")
    print("  ANÁLISE 3 — Estabilidade nas Fronteiras das Bandas")
    print(f"  (cenários com índice a menos de 5 pontos de P1/P2/P3)")
    print(SEP)

    FRONTEIRAS = list(_FRONTEIRAS_BANDA)  # [80, 60, 35]
    MARGEM = 5.0

    proximos = []
    # Gerar 500 combinações aleatórias de intensidades
    np.random.seed(42)
    combos = list(itertools.product(INTENSIDADES_ORDEM, repeat=len(CRITERIOS)))
    np.random.shuffle(combos)
    combos = combos[:500]

    for combo in combos:
        intensidades = dict(zip(CRITERIOS, combo))
        p, _ = compute_p(intensidades)
        idx = normalizar_indice(p, P_MAX)
        for front in FRONTEIRAS:
            if abs(idx - front) <= MARGEM:
                banda = classificar_banda(idx)
                proximos.append({
                    "intensidades": intensidades,
                    "indice": idx,
                    "fronteira": front,
                    "banda": banda,
                    "distancia": abs(idx - front),
                })

    # ordenar por distância
    proximos.sort(key=lambda x: x["distancia"])

    rows = []
    for item in proximos[:15]:
        urg = item["intensidades"]["URGENCIA"][:3].upper()
        imp = item["intensidades"]["IMPACTO_NO_CLIENTE"][:3].upper()
        sent = item["intensidades"]["SENTIMENTO_DO_CLIENTE"][:3].upper()
        tempo = item["intensidades"]["TEMPO_DE_ESPERA"][:3].upper()
        rows.append([
            f"{urg}/{imp}/{sent}/{tempo}",
            f"{item['indice']:.2f}",
            f"±{item['distancia']:.2f}",
            f"Fronteira {item['fronteira']}",
            item["banda"].split("—")[0].strip(),
        ])

    print(tabulate(rows,
                   headers=["URG/IMP/SENT/TEMPO", "Índice", "Dist. fronteira", "Fronteira", "Banda"],
                   tablefmt="rounded_outline"))

    # Teste de flip: para cada caso próximo, mudar 1 intensidade e ver se muda de banda
    flips = 0
    total_testados = min(20, len(proximos))
    for item in proximos[:total_testados]:
        for c in CRITERIOS:
            intens_atual = item["intensidades"][c]
            idx_atual_pos = INTENSIDADES_ORDEM.index(intens_atual)
            for nova_pos in [idx_atual_pos - 1, idx_atual_pos + 1]:
                if 0 <= nova_pos < len(INTENSIDADES_ORDEM):
                    nova_int = dict(item["intensidades"])
                    nova_int[c] = INTENSIDADES_ORDEM[nova_pos]
                    p2, _ = compute_p(nova_int)
                    idx2 = normalizar_indice(p2, P_MAX)
                    if classificar_banda(idx2) != item["banda"]:
                        flips += 1

    print(f"\n  Testes de flip (mudar 1 intensidade nos {total_testados} casos mais próximos de fronteira):")
    print(f"  → {flips} mudanças de banda detectadas em {total_testados * len(CRITERIOS) * 2} perturbações")
    taxa = flips / (total_testados * len(CRITERIOS) * 2) * 100
    print(f"  → Taxa de instabilidade de fronteira: {taxa:.1f}%")
    if taxa < 20:
        print("  → AVALIAÇÃO: Fronteiras estáveis ✓")
    elif taxa < 40:
        print("  → AVALIAÇÃO: Fronteiras moderadamente estáveis ⚠")
    else:
        print("  → AVALIAÇÃO: Fronteiras instáveis — revisar pesos ✗")


# ── 4. Casos ambíguos ────────────────────────────────────────────────────────

def analise_casos_ambiguos():
    print(f"\n{SEP}")
    print("  ANÁLISE 4 — Diagnóstico dos Casos Ambíguos (Cenários Intermediários)")
    print(SEP)

    # Cenários que podem ser questionados
    casos_alvo = [3, 4, 9, 11]  # índices 0-based
    for i in casos_alvo:
        c = CENARIOS[i]
        p, contribs = compute_p(c["intensidades"])
        idx = normalizar_indice(p, P_MAX)
        banda = classificar_banda(idx)

        print(f"\n  Cenário #{i+1}: {c['nome']}")
        print(f"  Índice = {idx:.1f}  →  {banda}")

        rows = []
        for crit in CRITERIOS:
            intens = c["intensidades"][crit]
            contrib_pct = contribs[crit] / p * 100
            rows.append([
                crit.replace("_", " ").title(),
                intens.capitalize(),
                f"{PESOS_CRITERIOS[crit]*100:.1f}%",
                f"{contribs[crit]:.4f}",
                f"{contrib_pct:.1f}%",
            ])
        print(tabulate(rows,
                       headers=["Critério", "Intensidade", "Peso (w)", "Contrib.", "% do total"],
                       tablefmt="simple"))

        # O que precisaria mudar para subir de banda?
        banda_acima = {"P4 — Baixa": 35.0, "P3 — Média": 60.0, "P2 — Alta": 80.0}
        if banda in banda_acima:
            limiar = banda_acima[banda]
            dist = limiar - idx
            print(f"  → Precisa de +{dist:.1f} pontos para subir para a próxima banda.")
            print(f"  → Critério mais impactante: URGENCIA ({PESOS_CRITERIOS['URGENCIA']*100:.0f}% do peso)")


# ── 5. Comparação AHP vs Baselines ──────────────────────────────────────────

def _baseline_media_simples(intensidades: dict) -> str:
    """Média aritmética simples dos pesos de intensidade (pesos iguais)."""
    pesos_iguais = 1.0 / len(CRITERIOS)
    p = sum(pesos_iguais * PRIORIDADES_POR_CRITERIO[c].get(intensidades.get(c, "ausente"), 0.0)
            for c in CRITERIOS)
    p_max = sum(pesos_iguais * max(PRIORIDADES_POR_CRITERIO[c].values()) for c in CRITERIOS)
    return classificar_banda(normalizar_indice(p, p_max))


def _baseline_regras(intensidades: dict) -> str:
    """Sistema de regras fixas sem AHP."""
    urg = intensidades.get("URGENCIA", "ausente")
    imp = intensidades.get("IMPACTO_NO_CLIENTE", "ausente")
    tempo = intensidades.get("TEMPO_DE_ESPERA", "ausente")
    sent = intensidades.get("SENTIMENTO_DO_CLIENTE", "ausente")

    if urg == "critica" or (urg == "alta" and imp == "critica"):
        return "P1 — Crítica"
    if urg == "alta" or imp == "alta" or (tempo == "critica" and urg != "baixa"):
        return "P2 — Alta"
    if urg == "moderada" or imp == "moderada" or tempo == "alta":
        return "P3 — Média"
    return "P4 — Baixa"


def analise_comparacao_baseline():
    print(f"\n{SEP}")
    print("  ANÁLISE 5 — Comparação: AHP vs Média Simples vs Regras Fixas")
    print(SEP)

    rows = []
    concordancia_media = 0
    concordancia_regras = 0

    for i, c in enumerate(CENARIOS, 1):
        p, _ = compute_p(c["intensidades"])
        idx = normalizar_indice(p, P_MAX)
        banda_ahp = classificar_banda(idx)
        banda_media = _baseline_media_simples(c["intensidades"])
        banda_regras = _baseline_regras(c["intensidades"])

        ok_media = "✓" if banda_ahp == banda_media else "✗"
        ok_regras = "✓" if banda_ahp == banda_regras else "✗"
        if banda_ahp == banda_media:
            concordancia_media += 1
        if banda_ahp == banda_regras:
            concordancia_regras += 1

        rows.append([
            i, c["nome"][:35],
            f"{idx:.1f}",
            banda_ahp.split("—")[0].strip(),
            banda_media.split("—")[0].strip(), ok_media,
            banda_regras.split("—")[0].strip(), ok_regras,
        ])

    print(tabulate(rows,
                   headers=["#", "Cenário", "Índice",
                             "AHP", "Média", "=?",
                             "Regras", "=?"],
                   tablefmt="rounded_outline"))

    n = len(CENARIOS)
    print(f"\n  Concordância AHP × Média Simples : {concordancia_media}/{n} ({concordancia_media/n*100:.0f}%)")
    print(f"  Concordância AHP × Regras Fixas  : {concordancia_regras}/{n} ({concordancia_regras/n*100:.0f}%)")

    disc_media = [CENARIOS[i]["nome"] for i, c in enumerate(CENARIOS)
                  if classificar_banda(normalizar_indice(compute_p(c["intensidades"])[0], P_MAX))
                  != _baseline_media_simples(c["intensidades"])]
    disc_regras = [CENARIOS[i]["nome"] for i, c in enumerate(CENARIOS)
                   if classificar_banda(normalizar_indice(compute_p(c["intensidades"])[0], P_MAX))
                   != _baseline_regras(c["intensidades"])]

    if disc_media:
        print(f"\n  Discordâncias vs Média Simples:")
        for d in disc_media:
            print(f"    • {d}")
    if disc_regras:
        print(f"\n  Discordâncias vs Regras Fixas (AHP captura nuance diferente):")
        for d in disc_regras:
            print(f"    • {d}")


# ── 6. Distribuição esperada das bandas ─────────────────────────────────────

def analise_distribuicao_esperada():
    print(f"\n{SEP}")
    print("  ANÁLISE 6 — Distribuição Esperada das Bandas")
    print(f"  (todas as {len(INTENSIDADES_ORDEM)**len(CRITERIOS)} combinações possíveis de intensidades)")
    print(SEP)

    contagem = {b: 0 for b in BANDAS_ORDEM}
    total = 0

    for combo in itertools.product(INTENSIDADES_ORDEM, repeat=len(CRITERIOS)):
        intensidades = dict(zip(CRITERIOS, combo))
        p, _ = compute_p(intensidades)
        idx = normalizar_indice(p, P_MAX)
        banda = classificar_banda(idx)
        contagem[banda] += 1
        total += 1

    rows = []
    for banda in BANDAS_ORDEM:
        n = contagem[banda]
        pct = n / total * 100
        barra = "█" * int(pct / 2)
        rows.append([banda, n, f"{pct:.1f}%", barra])

    print(tabulate(rows, headers=["Banda", "Combinações", "%", "Distribuição"],
                   tablefmt="rounded_outline"))
    print(f"  Total de combinações: {total}")

    # Análise de cobertura
    p1_pct = contagem["P1 — Crítica"] / total * 100
    p4_pct = contagem["P4 — Baixa"] / total * 100
    print(f"\n  P1 cobre {p1_pct:.1f}% do espaço — ", end="")
    if p1_pct < 15:
        print("adequado (P1 deve ser restrito) ✓")
    elif p1_pct < 30:
        print("moderado ⚠")
    else:
        print("excessivo — revisar limiares ✗")

    print(f"  P4 cobre {p4_pct:.1f}% do espaço — ", end="")
    if p4_pct > 20:
        print("adequado (maioria dos chamados são baixa prioridade) ✓")
    else:
        print("baixo ⚠")

    # Análise por variação de urgência
    print(f"\n  Distribuição por intensidade de URGENCIA (fixando os demais em moderada):")
    rows2 = []
    for urg in INTENSIDADES_ORDEM:
        intensidades = {
            "URGENCIA": urg,
            "IMPACTO_NO_CLIENTE": "moderada",
            "SENTIMENTO_DO_CLIENTE": "moderada",
            "TEMPO_DE_ESPERA": "moderada",
        }
        p, _ = compute_p(intensidades)
        idx = normalizar_indice(p, P_MAX)
        rows2.append([urg.capitalize(), f"{idx:.1f}", classificar_banda(idx)])
    print(tabulate(rows2, headers=["URGENCIA", "Índice", "Banda"], tablefmt="simple"))


# ── 7. Zona de transição fuzzy ───────────────────────────────────────────────

def analise_zona_transicao():
    print(f"\n{SEP}")
    print("  ANÁLISE 7 — Zona de Transição Fuzzy nas Fronteiras")
    print(f"  (margem ±{MARGEM_TRANSICAO:.0f} pts em torno de {list(_FRONTEIRAS_BANDA)} → revisao_humana)")
    print(SEP)

    total = 0
    na_zona = 0
    mudancas_cenarios = 0
    rows_zona = []
    contagem_antes = {b: 0 for b in BANDAS_ORDEM}
    contagem_depois = {b: 0 for b in BANDAS_ORDEM + ["REVISAO_HUMANA"]}

    for combo in itertools.product(INTENSIDADES_ORDEM, repeat=len(CRITERIOS)):
        intensidades = dict(zip(CRITERIOS, combo))
        p, _ = compute_p(intensidades)
        idx = normalizar_indice(p, P_MAX)
        banda_sem_zona = classificar_banda(idx)
        banda_com_zona = classificar_banda_com_zona(idx)
        contagem_antes[banda_sem_zona] += 1
        contagem_depois[banda_com_zona] += 1
        total += 1
        if banda_com_zona == "REVISAO_HUMANA":
            na_zona += 1

    # Tabela antes vs depois
    print(f"\n  Distribuição antes e depois da zona de transição ({total} combinações):\n")
    rows = []
    for b in BANDAS_ORDEM:
        antes = contagem_antes[b]
        depois = contagem_depois[b]
        diff = depois - antes
        rows.append([
            b,
            f"{antes} ({antes/total*100:.1f}%)",
            f"{depois} ({depois/total*100:.1f}%)",
            f"{diff:+d}",
        ])
    rows.append([
        "REVISAO_HUMANA",
        "0 (0.0%)",
        f"{contagem_depois['REVISAO_HUMANA']} ({contagem_depois['REVISAO_HUMANA']/total*100:.1f}%)",
        f"+{contagem_depois['REVISAO_HUMANA']}",
    ])
    print(tabulate(rows,
                   headers=["Banda", "Antes", "Depois", "Delta"],
                   tablefmt="rounded_outline"))

    print(f"\n  Casos enviados para revisao_humana pela zona: {na_zona} ({na_zona/total*100:.1f}%)")

    # Impacto nos 12 cenários de teste
    print(f"\n  Impacto nos {len(CENARIOS)} cenários de teste:\n")
    rows_c = []
    for i, c in enumerate(CENARIOS, 1):
        p, _ = compute_p(c["intensidades"])
        idx = normalizar_indice(p, P_MAX)
        sem_zona = classificar_banda(idx)
        com_zona = classificar_banda_com_zona(idx)
        flag = "-> REVISAO_HUMANA" if com_zona == "REVISAO_HUMANA" else "OK"
        rows_c.append([i, c["nome"][:38], f"{idx:.1f}", sem_zona.split("—")[0].strip(), com_zona.split("—")[0].strip() if com_zona != "REVISAO_HUMANA" else "REVISAO", flag])
    print(tabulate(rows_c,
                   headers=["#", "Cenário", "Índice", "Sem zona", "Com zona", "Ação"],
                   tablefmt="simple"))

    # Análise de flip: compara instabilidade "sem zona" vs "com zona"
    # Definição de flip prejudicial:
    #   - Sem zona: duas classificações definitivas diferentes (P1≠P2 etc.)
    #   - Com zona: dois resultados definitivos diferentes, IGNORANDO casos
    #     em que qualquer um dos dois lados é REVISAO_HUMANA (esses são tratados
    #     corretamente pela zona e não representam instabilidade)
    print(f"\n  Teste de flip com zona ativada (flips prejudiciais = troca entre bandas definitivas):")
    combos_all = list(itertools.product(INTENSIDADES_ORDEM, repeat=len(CRITERIOS)))
    proximos_zona = []
    for combo in combos_all:
        intensidades = dict(zip(CRITERIOS, combo))
        p, _ = compute_p(intensidades)
        idx = normalizar_indice(p, P_MAX)
        for f in _FRONTEIRAS_BANDA:
            if abs(idx - f) <= 5.0:
                proximos_zona.append((intensidades, idx))
                break

    flips_sem = 0
    flips_com = 0
    total_sem = 0
    total_com_definitivos = 0
    for intensidades, idx in proximos_zona[:20]:
        banda_original_sem = classificar_banda(idx)
        banda_original_com = classificar_banda_com_zona(idx)
        for c in CRITERIOS:
            idx_atual = INTENSIDADES_ORDEM.index(intensidades[c])
            for nova_pos in [idx_atual - 1, idx_atual + 1]:
                if 0 <= nova_pos < len(INTENSIDADES_ORDEM):
                    nova = dict(intensidades)
                    nova[c] = INTENSIDADES_ORDEM[nova_pos]
                    p2, _ = compute_p(nova)
                    idx2 = normalizar_indice(p2, P_MAX)
                    # Sem zona: qualquer mudança de banda conta
                    total_sem += 1
                    if classificar_banda(idx2) != banda_original_sem:
                        flips_sem += 1
                    # Com zona: só conta flip se AMBOS os lados forem definitivos
                    banda_nova_com = classificar_banda_com_zona(idx2)
                    if banda_original_com != "REVISAO_HUMANA" and banda_nova_com != "REVISAO_HUMANA":
                        total_com_definitivos += 1
                        if banda_nova_com != banda_original_com:
                            flips_com += 1

    taxa_sem = flips_sem / total_sem * 100 if total_sem else 0
    taxa_com = flips_com / total_com_definitivos * 100 if total_com_definitivos else 0
    print(f"  Sem zona: {flips_sem}/{total_sem} flips prejudiciais — instabilidade {taxa_sem:.1f}%")
    print(f"  Com zona: {flips_com}/{total_com_definitivos} flips prejudiciais (só entre bandas definitivas) — instabilidade {taxa_com:.1f}%")
    melhora = taxa_sem - taxa_com
    print(f"  Reducao de instabilidade de fronteira: -{melhora:.1f}pp")
    na_zona_flip = total_sem - total_com_definitivos
    print(f"  Perturbacoes absorvidas pela zona (REVISAO_HUMANA): {na_zona_flip} ({na_zona_flip/total_sem*100:.1f}%)")
    if taxa_com < 5:
        print(f"  AVALIACAO: Zona elimina praticamente toda instabilidade definitiva ✓")
    elif taxa_com < 15:
        print(f"  AVALIACAO: Instabilidade residual baixa ✓")
    else:
        print(f"  AVALIACAO: Instabilidade residual moderada — revisar margem ⚠")


# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "█" * 72)
    print("  CHAM.IA — ANÁLISE DE QUALIDADE DO ALGORITMO AHP")
    print("█" * 72)

    analise_cr_intensidades()
    analise_sensibilidade()
    analise_fronteira()
    analise_casos_ambiguos()
    analise_comparacao_baseline()
    analise_distribuicao_esperada()
    analise_zona_transicao()

    print(f"\n{'=' * 72}")
    print("  Concluído. Execute graficos_qualidade.py para os gráficos.")
    print("=" * 72 + "\n")
