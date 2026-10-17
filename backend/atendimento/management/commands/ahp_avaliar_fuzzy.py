"""
Avaliacao empirica do metodo AHP Fuzzy Ponderado por Confianca.

Gera um dataset sintetico de 20 casos cobrindo todos os cenarios relevantes
(P1 solido, borda P1/P2, P2 solido, borda P2/P3, P3 solido, borda P3/P4, P4 solido)
com diferentes niveis de confianca e compara o metodo crisp (tradicional) vs
o metodo fuzzy contra um gabarito definido por especialista.

Metricas produzidas (secao 7 do documento Metodo_AHP_Fuzzy_ChamIA.docx):
  - Acuracia e Cohen's Kappa (ambos metodos vs gabarito)
  - Precisao, Recall, F1 para a flag revisao_humana
  - Analise de sensibilidade do hiperparametro alpha

Uso:
  python manage.py ahp_avaliar_fuzzy
  python manage.py ahp_avaliar_fuzzy --alpha 0.15
  python manage.py ahp_avaliar_fuzzy --alphas 0.05,0.10,0.15,0.20,0.30,0.50
  python manage.py ahp_avaliar_fuzzy --verbose
"""

import math

from django.core.management.base import BaseCommand

from ahp.services.version_service import AHPVersionService
from atendimento.services.classification_service import ServicePriorityClassificationService

# ---------------------------------------------------------------------------
# Dataset sintetico -- 20 casos
# Cada caso: (descricao, intensidades, confiancas, gabarito)
# gabarito = o que um especialista humano esperaria do sistema:
#   - Alta confianca + longe da borda => banda AHP crisp
#   - Baixa confianca + perto da borda => 'revisao_humana'
# ---------------------------------------------------------------------------
DATASET = [
    # == GRUPO A: P1 solido, alta confianca ====================================
    ("P1 solido - tudo critica c=1.0",
     {"URGENCIA": "critica", "IMPACTO_NO_CLIENTE": "critica",
      "SENTIMENTO_DO_CLIENTE": "critica", "TEMPO_DE_ESPERA": "critica"},
     {"URGENCIA": 1.0, "IMPACTO_NO_CLIENTE": 1.0,
      "SENTIMENTO_DO_CLIENTE": 1.0, "TEMPO_DE_ESPERA": 1.0},
     "p1"),

    ("P1 solido - U=C I=C S=C T=M c=0.95",
     {"URGENCIA": "critica", "IMPACTO_NO_CLIENTE": "critica",
      "SENTIMENTO_DO_CLIENTE": "critica", "TEMPO_DE_ESPERA": "moderada"},
     {"URGENCIA": 0.95, "IMPACTO_NO_CLIENTE": 0.95,
      "SENTIMENTO_DO_CLIENTE": 0.95, "TEMPO_DE_ESPERA": 1.0},
     "p1"),

    ("P1 solido - U=C I=C S=M T=B c=0.90",
     {"URGENCIA": "critica", "IMPACTO_NO_CLIENTE": "critica",
      "SENTIMENTO_DO_CLIENTE": "moderada", "TEMPO_DE_ESPERA": "baixa"},
     {"URGENCIA": 0.90, "IMPACTO_NO_CLIENTE": 0.90,
      "SENTIMENTO_DO_CLIENTE": 0.85, "TEMPO_DE_ESPERA": 1.0},
     "p1"),

    ("P1 solido - U=C I=C S=B T=B c=0.88",
     {"URGENCIA": "critica", "IMPACTO_NO_CLIENTE": "critica",
      "SENTIMENTO_DO_CLIENTE": "baixa", "TEMPO_DE_ESPERA": "baixa"},
     {"URGENCIA": 0.88, "IMPACTO_NO_CLIENTE": 0.88,
      "SENTIMENTO_DO_CLIENTE": 0.85, "TEMPO_DE_ESPERA": 1.0},
     "p1"),

    # == GRUPO B: Borda P1/P2 (~80) -- alta confianca => P1 ok ================
    ("BORDA P1/P2 - U=C I=M S=C T=B c=0.90 => P1",
     {"URGENCIA": "critica", "IMPACTO_NO_CLIENTE": "moderada",
      "SENTIMENTO_DO_CLIENTE": "critica", "TEMPO_DE_ESPERA": "baixa"},
     {"URGENCIA": 0.90, "IMPACTO_NO_CLIENTE": 0.90,
      "SENTIMENTO_DO_CLIENTE": 0.90, "TEMPO_DE_ESPERA": 1.0},
     "p1"),

    # == GRUPO C: Borda P1/P2 -- baixa confianca => REVISAO ===================
    ("BORDA P1/P2 - U=C I=M S=C T=B U_conf=0.35 => REVISAO",
     {"URGENCIA": "critica", "IMPACTO_NO_CLIENTE": "moderada",
      "SENTIMENTO_DO_CLIENTE": "critica", "TEMPO_DE_ESPERA": "baixa"},
     {"URGENCIA": 0.35, "IMPACTO_NO_CLIENTE": 0.90,
      "SENTIMENTO_DO_CLIENTE": 0.90, "TEMPO_DE_ESPERA": 1.0},
     "revisao_humana"),

    ("BORDA P1/P2 - U=C I=C S=B T=B U_conf=0.0 => REVISAO",
     {"URGENCIA": "critica", "IMPACTO_NO_CLIENTE": "critica",
      "SENTIMENTO_DO_CLIENTE": "baixa", "TEMPO_DE_ESPERA": "baixa"},
     {"URGENCIA": 0.0, "IMPACTO_NO_CLIENTE": 1.0,
      "SENTIMENTO_DO_CLIENTE": 1.0, "TEMPO_DE_ESPERA": 1.0},
     "revisao_humana"),

    ("BORDA P1/P2 - U=C I=M S=C T=B U_conf=0.20 => REVISAO",
     {"URGENCIA": "critica", "IMPACTO_NO_CLIENTE": "moderada",
      "SENTIMENTO_DO_CLIENTE": "critica", "TEMPO_DE_ESPERA": "baixa"},
     {"URGENCIA": 0.20, "IMPACTO_NO_CLIENTE": 0.90,
      "SENTIMENTO_DO_CLIENTE": 0.90, "TEMPO_DE_ESPERA": 1.0},
     "revisao_humana"),

    # == GRUPO D: P2 solido, alta confianca ====================================
    ("P2 solido - U=C I=M S=M T=M c=0.85",
     {"URGENCIA": "critica", "IMPACTO_NO_CLIENTE": "moderada",
      "SENTIMENTO_DO_CLIENTE": "moderada", "TEMPO_DE_ESPERA": "moderada"},
     {"URGENCIA": 0.85, "IMPACTO_NO_CLIENTE": 0.85,
      "SENTIMENTO_DO_CLIENTE": 0.85, "TEMPO_DE_ESPERA": 1.0},
     "p2"),

    ("P2 solido - U=M I=C S=C T=B c=0.90",
     {"URGENCIA": "moderada", "IMPACTO_NO_CLIENTE": "critica",
      "SENTIMENTO_DO_CLIENTE": "critica", "TEMPO_DE_ESPERA": "baixa"},
     {"URGENCIA": 0.90, "IMPACTO_NO_CLIENTE": 0.90,
      "SENTIMENTO_DO_CLIENTE": 0.90, "TEMPO_DE_ESPERA": 1.0},
     "p2"),

    ("P2 solido - U=M I=C S=M T=M c=0.90",
     {"URGENCIA": "moderada", "IMPACTO_NO_CLIENTE": "critica",
      "SENTIMENTO_DO_CLIENTE": "moderada", "TEMPO_DE_ESPERA": "moderada"},
     {"URGENCIA": 0.90, "IMPACTO_NO_CLIENTE": 0.90,
      "SENTIMENTO_DO_CLIENTE": 0.90, "TEMPO_DE_ESPERA": 1.0},
     "p2"),

    # == GRUPO E: Borda P2/P3 (~60) -- baixa confianca => REVISAO =============
    ("BORDA P2/P3 - U=M I=C S=M T=B I_conf=0.30 => REVISAO",
     {"URGENCIA": "moderada", "IMPACTO_NO_CLIENTE": "critica",
      "SENTIMENTO_DO_CLIENTE": "moderada", "TEMPO_DE_ESPERA": "baixa"},
     {"URGENCIA": 0.90, "IMPACTO_NO_CLIENTE": 0.30,
      "SENTIMENTO_DO_CLIENTE": 0.90, "TEMPO_DE_ESPERA": 1.0},
     "revisao_humana"),

    ("BORDA P2/P3 - U=M I=C S=M T=B I_conf=0.0 => REVISAO",
     {"URGENCIA": "moderada", "IMPACTO_NO_CLIENTE": "critica",
      "SENTIMENTO_DO_CLIENTE": "moderada", "TEMPO_DE_ESPERA": "baixa"},
     {"URGENCIA": 0.90, "IMPACTO_NO_CLIENTE": 0.0,
      "SENTIMENTO_DO_CLIENTE": 0.90, "TEMPO_DE_ESPERA": 1.0},
     "revisao_humana"),

    # == GRUPO F: P3 solido ====================================================
    ("P3 solido - todos moderada c=0.85",
     {"URGENCIA": "moderada", "IMPACTO_NO_CLIENTE": "moderada",
      "SENTIMENTO_DO_CLIENTE": "moderada", "TEMPO_DE_ESPERA": "moderada"},
     {"URGENCIA": 0.85, "IMPACTO_NO_CLIENTE": 0.85,
      "SENTIMENTO_DO_CLIENTE": 0.85, "TEMPO_DE_ESPERA": 1.0},
     "p3"),

    ("P3 solido - U=B I=C S=M T=B c=0.90",
     {"URGENCIA": "baixa", "IMPACTO_NO_CLIENTE": "critica",
      "SENTIMENTO_DO_CLIENTE": "moderada", "TEMPO_DE_ESPERA": "baixa"},
     {"URGENCIA": 0.90, "IMPACTO_NO_CLIENTE": 0.90,
      "SENTIMENTO_DO_CLIENTE": 0.90, "TEMPO_DE_ESPERA": 1.0},
     "p3"),

    # == GRUPO G: Borda P3/P4 (~35) -- baixa confianca => REVISAO =============
    ("BORDA P3/P4 - U=B I=M S=M T=B I_conf=0.25 => REVISAO",
     {"URGENCIA": "baixa", "IMPACTO_NO_CLIENTE": "moderada",
      "SENTIMENTO_DO_CLIENTE": "moderada", "TEMPO_DE_ESPERA": "baixa"},
     {"URGENCIA": 0.90, "IMPACTO_NO_CLIENTE": 0.25,
      "SENTIMENTO_DO_CLIENTE": 0.90, "TEMPO_DE_ESPERA": 1.0},
     "revisao_humana"),

    ("BORDA P3/P4 - U=B I=M S=M T=B I_conf=0.0 => REVISAO",
     {"URGENCIA": "baixa", "IMPACTO_NO_CLIENTE": "moderada",
      "SENTIMENTO_DO_CLIENTE": "moderada", "TEMPO_DE_ESPERA": "baixa"},
     {"URGENCIA": 0.90, "IMPACTO_NO_CLIENTE": 0.0,
      "SENTIMENTO_DO_CLIENTE": 0.90, "TEMPO_DE_ESPERA": 1.0},
     "revisao_humana"),

    # == GRUPO H: P4 solido ====================================================
    ("P4 solido - tudo baixa c=0.90",
     {"URGENCIA": "baixa", "IMPACTO_NO_CLIENTE": "baixa",
      "SENTIMENTO_DO_CLIENTE": "baixa", "TEMPO_DE_ESPERA": "baixa"},
     {"URGENCIA": 0.90, "IMPACTO_NO_CLIENTE": 0.90,
      "SENTIMENTO_DO_CLIENTE": 0.90, "TEMPO_DE_ESPERA": 1.0},
     "p4"),

    ("P4 solido - U=B I=B S=M T=B c=0.90",
     {"URGENCIA": "baixa", "IMPACTO_NO_CLIENTE": "baixa",
      "SENTIMENTO_DO_CLIENTE": "moderada", "TEMPO_DE_ESPERA": "baixa"},
     {"URGENCIA": 0.90, "IMPACTO_NO_CLIENTE": 0.90,
      "SENTIMENTO_DO_CLIENTE": 0.90, "TEMPO_DE_ESPERA": 1.0},
     "p4"),

    ("P4 solido - U=B I=M S=B T=B c=0.85",
     {"URGENCIA": "baixa", "IMPACTO_NO_CLIENTE": "moderada",
      "SENTIMENTO_DO_CLIENTE": "baixa", "TEMPO_DE_ESPERA": "baixa"},
     {"URGENCIA": 0.85, "IMPACTO_NO_CLIENTE": 0.85,
      "SENTIMENTO_DO_CLIENTE": 0.85, "TEMPO_DE_ESPERA": 1.0},
     "p4"),
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _kappa(y_true, y_pred):
    """Cohen's Kappa para classificacao multiclasse."""
    classes = sorted(set(y_true) | set(y_pred))
    n = len(y_true)
    if n == 0:
        return 0.0

    # Matriz de confusao
    cm = {c: {d: 0 for d in classes} for c in classes}
    for t, p in zip(y_true, y_pred):
        cm[t][p] += 1

    p_o = sum(cm[c][c] for c in classes) / n
    p_e = sum(
        (sum(cm[c][d] for d in classes) / n) * (sum(cm[d][c] for d in classes) / n)
        for c in classes
    )
    return (p_o - p_e) / (1.0 - p_e) if (1.0 - p_e) != 0 else 1.0


def _prf1(y_true, y_pred, pos_label="revisao_humana"):
    tp = sum(1 for t, p in zip(y_true, y_pred) if t == pos_label and p == pos_label)
    fp = sum(1 for t, p in zip(y_true, y_pred) if t != pos_label and p == pos_label)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t == pos_label and p != pos_label)
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1        = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    return precision, recall, f1, tp, fp, fn


def _rodar_dataset(versao_ahp, alpha):
    """Retorna (pred_crisp[], pred_fuzzy[], gabaritos[]) para todos os casos."""
    pred_crisp, pred_fuzzy, gabaritos = [], [], []
    detalhes = []

    for descricao, intensidades, confiancas, gabarito in DATASET:
        # --- crisp (sem confiancas) ---
        r_crisp = ServicePriorityClassificationService.classify_from_intensidades(
            versao_ahp, intensidades
        )
        # --- fuzzy ---
        r_fuzzy = ServicePriorityClassificationService.classify_from_intensidades(
            versao_ahp, intensidades, confiancas=confiancas, alpha=alpha
        )

        pred_crisp.append(r_crisp.prioridade)
        pred_fuzzy.append(r_fuzzy.prioridade)
        gabaritos.append(gabarito)
        detalhes.append({
            "descricao": descricao,
            "gabarito": gabarito,
            "crisp": r_crisp.prioridade,
            "fuzzy": r_fuzzy.prioridade,
            "indice": r_crisp.indice,
            "indice_l": r_fuzzy.indice_l,
            "indice_u": r_fuzzy.indice_u,
        })

    return pred_crisp, pred_fuzzy, gabaritos, detalhes


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------

class Command(BaseCommand):
    help = (
        "Avalia o metodo AHP Fuzzy Ponderado por Confianca contra dados sinteticos. "
        "Produz Acuracia, Cohen's Kappa, Precisao/Recall/F1 para revisao_humana e "
        "analise de sensibilidade do alpha."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--alpha", type=float, default=0.20,
            help="Hiperparametro de escala fuzzy principal (default 0.20).",
        )
        parser.add_argument(
            "--alphas",
            help="Lista de alphas para analise de sensibilidade, separada por virgulas "
                 "(ex: 0.05,0.10,0.20,0.30,0.50). Se fornecida, sobrepoe --alpha.",
        )
        parser.add_argument(
            "--verbose", action="store_true", default=False,
            help="Imprime detalhes de cada caso.",
        )

    def handle(self, *args, **options):
        versao_ahp = AHPVersionService.get_versao_ativa()
        if versao_ahp is None:
            self.stderr.write(self.style.ERROR(
                "Nenhuma VersaoAHP ativa. Ative uma versao antes de rodar este comando."
            ))
            return

        self.stdout.write(self.style.SUCCESS(
            f"\n=== Avaliacao AHP Fuzzy | VersaoAHP #{versao_ahp.numero_versao} | "
            f"{len(DATASET)} casos sinteticos ===\n"
        ))

        alphas = (
            [float(a.strip()) for a in options["alphas"].split(",")]
            if options.get("alphas")
            else [options["alpha"]]
        )

        # ------------------------------------------------------------------
        # 1. Avaliacao principal com o alpha escolhido (ou primeiro da lista)
        # ------------------------------------------------------------------
        alpha_principal = alphas[0]
        pred_crisp, pred_fuzzy, gabaritos, detalhes = _rodar_dataset(versao_ahp, alpha_principal)

        self._print_metricas(pred_crisp, pred_fuzzy, gabaritos, alpha_principal)

        if options["verbose"]:
            self._print_detalhes(detalhes)

        # ------------------------------------------------------------------
        # 2. Analise de sensibilidade (se mais de um alpha)
        # ------------------------------------------------------------------
        if len(alphas) > 1:
            self._print_sensibilidade(versao_ahp, alphas, gabaritos)

        # ------------------------------------------------------------------
        # 3. Interpretacao das metricas
        # ------------------------------------------------------------------
        self._print_guia_metricas()

    # -----------------------------------------------------------------------
    def _print_metricas(self, pred_crisp, pred_fuzzy, gabaritos, alpha):
        n = len(gabaritos)

        acc_crisp = sum(p == g for p, g in zip(pred_crisp, gabaritos)) / n
        acc_fuzzy = sum(p == g for p, g in zip(pred_fuzzy, gabaritos)) / n
        k_crisp   = _kappa(gabaritos, pred_crisp)
        k_fuzzy   = _kappa(gabaritos, pred_fuzzy)

        prec_c, rec_c, f1_c, tp_c, fp_c, fn_c = _prf1(gabaritos, pred_crisp)
        prec_f, rec_f, f1_f, tp_f, fp_f, fn_f = _prf1(gabaritos, pred_fuzzy)

        n_revisao = sum(1 for g in gabaritos if g == "revisao_humana")

        self.stdout.write(f"Alpha = {alpha:.2f}  |  N = {n}  |  Revisoes no gabarito: {n_revisao}\n")
        self.stdout.write(f"{'Metrica':<30} {'Crisp':>10} {'Fuzzy':>10}  {'Delta':>8}")
        self.stdout.write("-" * 62)

        rows = [
            ("Acuracia geral",         acc_crisp, acc_fuzzy),
            ("Cohen's Kappa",           k_crisp,  k_fuzzy),
            ("Precisao revisao_humana", prec_c,   prec_f),
            ("Recall  revisao_humana",  rec_c,    rec_f),
            ("F1      revisao_humana",  f1_c,     f1_f),
        ]
        for nome, vc, vf in rows:
            delta = vf - vc
            delta_str = f"+{delta:.3f}" if delta >= 0 else f"{delta:.3f}"
            self.stdout.write(f"{nome:<30} {vc:>10.3f} {vf:>10.3f}  {delta_str:>8}")

        self.stdout.write("")
        self.stdout.write(f"{'Revisao_humana TP/FP/FN':<30} {'C:' + str(tp_c) + '/' + str(fp_c) + '/' + str(fn_c):>10} "
                          f"{'F:' + str(tp_f) + '/' + str(fp_f) + '/' + str(fn_f):>10}")
        self.stdout.write("")

    def _print_detalhes(self, detalhes):
        self.stdout.write("\n--- Detalhes por caso ---")
        self.stdout.write(f"{'#':<3} {'Gabarito':<16} {'Crisp':<16} {'Fuzzy':<16} {'Indice':>7} {'[l,u]'}")
        self.stdout.write("-" * 90)
        for i, d in enumerate(detalhes, 1):
            ok_c = "OK" if d["crisp"] == d["gabarito"] else "ERRO"
            ok_f = "OK" if d["fuzzy"] == d["gabarito"] else "ERRO"
            indice_str = f"{d['indice']:.1f}" if d["indice"] is not None else "  N/A"
            intervalo = (
                f"[{d['indice_l']:.1f},{d['indice_u']:.1f}]"
                if d["indice_l"] is not None else "n/a"
            )
            crisp_col = f"{d['crisp']:<10}({ok_c})"
            fuzzy_col = f"{d['fuzzy']:<10}({ok_f})"
            self.stdout.write(f"{i:<3} {d['gabarito']:<16} {crisp_col:<16} {fuzzy_col:<16} {indice_str:>7}  {intervalo}")
            self.stdout.write(f"    {d['descricao']}")
        self.stdout.write("")

    def _print_sensibilidade(self, versao_ahp, alphas, gabaritos):
        self.stdout.write("\n--- Sensibilidade ao alpha ---")
        self.stdout.write(f"{'Alpha':>7} {'Acc Fuzzy':>10} {'Kappa':>8} {'Recall Rev':>12} "
                          f"{'F1 Rev':>8} {'N->Revisao':>12}")
        self.stdout.write("-" * 62)
        for alpha in alphas:
            _, pred_fuzzy, _, _ = _rodar_dataset(versao_ahp, alpha)
            acc = sum(p == g for p, g in zip(pred_fuzzy, gabaritos)) / len(gabaritos)
            k   = _kappa(gabaritos, pred_fuzzy)
            _, rec, f1, _, _, _ = _prf1(gabaritos, pred_fuzzy)
            n_rev = sum(1 for p in pred_fuzzy if p == "revisao_humana")
            self.stdout.write(f"{alpha:>7.2f} {acc:>10.3f} {k:>8.3f} {rec:>12.3f} {f1:>8.3f} {n_rev:>12}")
        self.stdout.write("")
        self.stdout.write("Trade-off: alpha maior => mais casos para revisao (recall sobe, pode gerar FP).")
        self.stdout.write("")

    def _print_guia_metricas(self):
        self.stdout.write("=" * 70)
        self.stdout.write("GUIA DE METRICAS (o que cada numero significa)")
        self.stdout.write("=" * 70)
        guia = [
            ("Acuracia geral",
             "Fracao de casos classificados igual ao gabarito. Simples mas "
             "enganosa: um metodo que nunca envia para revisao pode ter acuracia "
             "alta se o gabarito for dominado por P1-P4."),
            ("Cohen's Kappa",
             "Acuracia corrigida pelo acaso. Valores: <0=pior que aleatorio, "
             "0-0.2=leve, 0.2-0.4=razoavel, 0.4-0.6=moderado, 0.6-0.8=bom, "
             ">0.8=excelente. Prefira esta metrica para datasets desbalanceados."),
            ("Precisao revisao_humana",
             "Dos casos enviados para revisao, qual fracao realmente precisava? "
             "Baixa precisao = muitos alarmes falsos (sobrecarga para o time)."),
            ("Recall  revisao_humana",
             "Dos casos que precisavam de revisao, qual fracao foi capturada? "
             "Recall=0% para o crisp (ele nunca captura por confianca). "
             "O fuzzy deve ter recall alto aqui -- este e o ganho principal."),
            ("F1 revisao_humana",
             "Media harmonica de precisao e recall. Resume o trade-off. "
             "Para o crisp espera-se F1=0; para o fuzzy, F1>0 indica melhora real."),
            ("Analise de sensibilidade",
             "Mostra como o alpha afeta as metricas. Escolha o alpha que "
             "maximiza F1 de revisao_humana sem sacrificar acuracia geral. "
             "Recomendacao inicial: alpha=0.20 (ver secao 6 do documento)."),
        ]
        for nome, descricao in guia:
            self.stdout.write(f"\n  {nome}:")
            # Quebra em linhas de 65 chars
            palavras = descricao.split()
            linha = "    "
            for palavra in palavras:
                if len(linha) + len(palavra) + 1 > 70:
                    self.stdout.write(linha)
                    linha = "    " + palavra + " "
                else:
                    linha += palavra + " "
            if linha.strip():
                self.stdout.write(linha)
        self.stdout.write("\n" + "=" * 70 + "\n")
