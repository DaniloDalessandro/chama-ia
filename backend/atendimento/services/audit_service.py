"""
AuditService: helpers de leitura para auditoria e (nas fases seguintes) para
a tela de explicacao. Reconstroi, a partir das Comparacao (imutaveis apos a
versao sair de RASCUNHO), as matrizes efetivamente usadas por uma VersaoAHP
-- usado para congelar uma "foto" fiel no momento de cada classificacao.
"""

from ahp.models import Criterio, Intensidade, Termo, VersaoAHP
from ahp.services.comparison_service import AHPComparisonService
from ahp.services.matrix_service import AHPMatrixService


class AuditService:
    @staticmethod
    def snapshot_matrizes(versao_ahp: VersaoAHP) -> tuple:
        """
        Retorna (matriz_criterios, matriz_intensidades) prontos para JSON:
        matriz_criterios = {"ordem": [codigo, ...], "matriz": [[...], ...]}
        matriz_intensidades = {criterio_codigo: {"ordem": [...], "matriz": [...]}}

        Usa os codigos congelados em versao_ahp.pesos_criterios/prioridades_intensidades
        (nao a lista "ativa hoje" de criterios/intensidades, que pode ter mudado
        depois que a versao foi ativada) para reconstruir exatamente o que foi usado.
        """
        codigos_criterios = list((versao_ahp.pesos_criterios or {}).keys())
        criterios = list(Criterio.all_objects.filter(codigo__in=codigos_criterios).order_by("ordem"))

        valores_criterios = AHPComparisonService.get_valores_matrix_criterios(versao_ahp, criterios)
        matrix_criterios = AHPMatrixService.build_matrix(len(criterios), valores_criterios)
        matriz_criterios = {
            "ordem": [c.codigo for c in criterios],
            "matriz": matrix_criterios.tolist(),
        }

        matriz_intensidades = {}
        prioridades_por_criterio = versao_ahp.prioridades_intensidades or {}
        for criterio in criterios:
            codigos_intensidades = list(prioridades_por_criterio.get(criterio.codigo, {}).keys())
            intensidades = list(
                Intensidade.all_objects.filter(criterio=criterio, codigo__in=codigos_intensidades).order_by("ordem")
            )
            valores = AHPComparisonService.get_valores_matrix_intensidades(versao_ahp, criterio, intensidades)
            matrix = AHPMatrixService.build_matrix(len(intensidades), valores)
            matriz_intensidades[criterio.codigo] = {
                "ordem": [i.codigo for i in intensidades],
                "matriz": matrix.tolist(),
            }

        return matriz_criterios, matriz_intensidades

    @staticmethod
    def gerar_explicacao(auditoria) -> str:
        """
        Texto objetivo de explicacao (secao 7, Agente 7) -- nunca revela chain
        of thought, prompts internos ou calculos detalhados, apenas o resumo
        dos fatores que levaram a prioridade final.
        """
        if auditoria.prioridade == "revisao_humana":
            return "Revisao humana necessaria -- dados insuficientes ou inconclusivos para classificar automaticamente."

        linhas = [f"Prioridade {auditoria.prioridade.upper()} (indice {auditoria.indice:.1f})."]
        linhas.append("")
        linhas.append("Principais fatores:")
        for codigo, contribuicao in sorted(auditoria.contribuicoes.items(), key=lambda kv: -kv[1]):
            intensidade = auditoria.intensidades.get(codigo, "-")
            linhas.append(f"- {codigo}: intensidade {intensidade} (contribuicao {contribuicao:.3f})")
        if auditoria.regra_critica:
            linhas.append("- regra critica confirmada")
        return "\n".join(linhas)

    @staticmethod
    def checar_consistencia(state: dict) -> dict:
        """
        Agente 7 (Auditoria): checagens de consistencia puramente Python sobre
        o estado final do grafo -- sem chamada de LLM. Nunca bloqueia o
        pipeline, apenas registra alertas para revisao humana/auditoria.
        """
        checagens = []
        alertas = []

        agente3 = state.get("agente3_resultado") or {}
        termos_citados = agente3.get("termos_correspondidos") or []
        if termos_citados:
            ids_citados = {t.get("termo_id") for t in termos_citados if t.get("termo_id") is not None}
            ids_aprovados = set(
                Termo.objects.filter(id__in=ids_citados, status_aprovacao=Termo.StatusAprovacao.APROVADO).values_list("id", flat=True)
            )
            for termo_id in ids_citados - ids_aprovados:
                alertas.append(f"Termo id={termo_id} citado pelo Agente 3 nao existe ou nao esta aprovado.")
        checagens.append("termos_correspondidos verificados")

        agente4 = state.get("agente4_resultado") or {}
        for avaliacao in agente4.get("avaliacoes") or []:
            if not avaliacao.get("dados_ausentes") and not (avaliacao.get("evidencia") or "").strip():
                alertas.append(
                    f"Criterio {avaliacao.get('criterio_codigo')} avaliado sem dados_ausentes mas sem evidencia registrada."
                )
        checagens.append("avaliacoes de criterios verificadas")

        agente5 = state.get("agente5_resultado") or {}
        if agente5.get("regra_critica_confirmada") and not (agente5.get("justificativa") or "").strip():
            alertas.append("Regra critica confirmada pelo Agente 5 sem justificativa registrada.")
        checagens.append("regra critica verificada")

        if state.get("agente6_resultado") is None:
            alertas.append("Agente 6 (AHP) nao produziu resultado -- classificacao pode estar ausente.")
        checagens.append("classificacao AHP verificada")

        return {"checagens": checagens, "alertas": alertas}
