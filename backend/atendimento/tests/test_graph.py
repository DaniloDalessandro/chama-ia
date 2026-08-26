from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from ahp.models import (
    CODIGO_IMPACTO_NO_CLIENTE,
    CODIGO_SENTIMENTO_DO_CLIENTE,
    CODIGO_TEMPO_DE_ESPERA,
    CODIGO_URGENCIA,
    Criterio,
    FaixaTempoEspera,
    Intensidade,
)
from ahp.services.comparison_service import AHPComparisonService
from ahp.services.version_service import AHPVersionService
from atendimento.ai.graph import build_graph
from atendimento.models import Atendimento, AuditoriaClassificacao, MensagemAtendimento

User = get_user_model()

VALORES_CRITERIOS = {(0, 1): 2.0, (0, 2): 4.0, (0, 3): 8.0, (1, 2): 2.0, (1, 3): 4.0, (2, 3): 2.0}
VALORES_INTENSIDADES = {(0, 1): 0.5, (0, 2): 0.25, (1, 2): 0.5}

_MODULOS_LLM = [
    "atendimento.ai.agents.agente1_conversa",
    "atendimento.ai.agents.agente2_visual_ocr",
    "atendimento.ai.agents.agente3_termos_contexto",
    "atendimento.ai.agents.agente4_avaliacao_criterios",
    "atendimento.ai.agents.agente5_validacao_critica",
]


class GraphTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="admin@test.com", password="x", name="Admin", role="admin")
        self.criterios = {}
        self.intensidades = {}
        for ordem, codigo in enumerate([CODIGO_URGENCIA, CODIGO_IMPACTO_NO_CLIENTE, CODIGO_SENTIMENTO_DO_CLIENTE, CODIGO_TEMPO_DE_ESPERA], start=1):
            criterio = Criterio.objects.create(nome=codigo.title(), codigo=codigo, ordem=ordem)
            self.criterios[codigo] = criterio
            Intensidade.objects.create(criterio=criterio, nome="Ausente", codigo=Intensidade.Codigo.AUSENTE, ordem=1)
            baixa = Intensidade.objects.create(criterio=criterio, nome="Baixa", codigo=Intensidade.Codigo.BAIXA, ordem=2)
            moderada = Intensidade.objects.create(criterio=criterio, nome="Moderada", codigo=Intensidade.Codigo.MODERADA, ordem=3)
            critica = Intensidade.objects.create(criterio=criterio, nome="Critica", codigo=Intensidade.Codigo.CRITICA, ordem=4)
            Intensidade.objects.create(criterio=criterio, nome="Inconclusiva", codigo=Intensidade.Codigo.INCONCLUSIVA, ordem=5)
            self.intensidades[codigo] = [baixa, moderada, critica]

        ct = self.criterios[CODIGO_TEMPO_DE_ESPERA]
        FaixaTempoEspera.objects.create(criterio=ct, minutos_min=0, minutos_max=5, intensidade=self.intensidades[CODIGO_TEMPO_DE_ESPERA][0], ordem=1)
        FaixaTempoEspera.objects.create(criterio=ct, minutos_min=5, minutos_max=15, intensidade=self.intensidades[CODIGO_TEMPO_DE_ESPERA][1], ordem=2)
        FaixaTempoEspera.objects.create(criterio=ct, minutos_min=15, minutos_max=None, intensidade=self.intensidades[CODIGO_TEMPO_DE_ESPERA][2], ordem=3)

        criterios_ordenados = [self.criterios[c] for c in [CODIGO_URGENCIA, CODIGO_IMPACTO_NO_CLIENTE, CODIGO_SENTIMENTO_DO_CLIENTE, CODIGO_TEMPO_DE_ESPERA]]
        self.versao = AHPVersionService.create_rascunho(user=self.user)
        AHPComparisonService.save_comparacoes_criterios(self.versao, criterios_ordenados, VALORES_CRITERIOS, user=self.user)
        for codigo, criterio in self.criterios.items():
            AHPComparisonService.save_comparacoes_intensidades(self.versao, criterio, self.intensidades[codigo], VALORES_INTENSIDADES, user=self.user)
        AHPVersionService.ativar(self.versao, user=self.user)

        self.atendimento = Atendimento.objects.create(nome="Cliente", email="c@test.com")
        MensagemAtendimento.objects.create(
            atendimento=self.atendimento, remetente_tipo=MensagemAtendimento.RemetenteTipo.CLIENTE, conteudo="Sistema fora do ar",
        )

    def _patch_all_llm_none(self):
        patchers = [patch(f"{modulo}.build_deepseek_llm", return_value=None) for modulo in _MODULOS_LLM]
        for p in patchers:
            p.start()
            self.addCleanup(p.stop)

    def test_full_run_all_agents_degraded_reaches_persist(self):
        self._patch_all_llm_none()
        grafo = build_graph()

        resultado = grafo.invoke({"atendimento_id": self.atendimento.id, "erros": []})

        for chave in [f"agente{n}_resultado" for n in range(1, 8)]:
            self.assertIsNotNone(resultado[chave], chave)

        self.assertIsNotNone(resultado["auditoria_id"])
        self.assertEqual(AuditoriaClassificacao.objects.filter(atendimento=self.atendimento).count(), 1)

        self.atendimento.refresh_from_db()
        self.assertEqual(self.atendimento.analise_ia_status, Atendimento.AnaliseIAStatus.CONCLUIDA)
        # agentes 1, 3, 4, 5 entraram em fallback (sem API key); agente 2 nao tem
        # anexos de imagem neste teste, entao retorna cedo sem sequer tentar o LLM
        self.assertGreaterEqual(len(resultado["erros"]), 4)

    def test_execution_order_via_stream(self):
        self._patch_all_llm_none()
        grafo = build_graph()

        ordem = []
        for update in grafo.stream({"atendimento_id": self.atendimento.id, "erros": []}, stream_mode="updates"):
            ordem.extend(update.keys())

        self.assertEqual(ordem[0], "validacao_seguranca")
        self.assertEqual(ordem[-1], "persistir_resultado")

        pos = {nome: idx for idx, nome in enumerate(ordem)}
        self.assertLess(pos["validacao_seguranca"], pos["agente1"])
        self.assertLess(pos["validacao_seguranca"], pos["agente2"])
        self.assertLess(pos["agente1"], pos["agente3"])
        self.assertLess(pos["agente2"], pos["agente3"])
        self.assertLess(pos["agente3"], pos["agente4"])
        self.assertLess(pos["agente4"], pos["agente5"])
        self.assertLess(pos["agente5"], pos["agente6"])
        self.assertLess(pos["agente6"], pos["agente7"])
        self.assertLess(pos["agente7"], pos["persistir_resultado"])

    def test_partial_agent_failure_still_completes_pipeline(self):
        from django.core.files.base import ContentFile

        from atendimento.models import AnexoAtendimento

        anexo = AnexoAtendimento(atendimento=self.atendimento, nome_original="print.png", tipo_arquivo=AnexoAtendimento.TipoArquivo.IMAGEM, tamanho=200)
        anexo.arquivo.save("print.png", ContentFile(b"conteudo de imagem qualquer" * 10), save=True)

        self._patch_all_llm_none()
        with patch("atendimento.ai.agents.agente2_visual_ocr.build_deepseek_llm", return_value=MagicMock()), \
             patch("atendimento.ai.agents.agente2_visual_ocr.build_chain") as mock_build_chain:
            fake_chain = MagicMock()
            fake_chain.invoke.side_effect = RuntimeError("DeepSeek explodiu")
            mock_build_chain.return_value = fake_chain

            grafo = build_graph()
            resultado = grafo.invoke({"atendimento_id": self.atendimento.id, "erros": []})

        self.assertIsNotNone(resultado["auditoria_id"])
        self.assertTrue(AuditoriaClassificacao.objects.filter(atendimento=self.atendimento).exists())
        self.assertTrue(any(e.get("agente") == "agente2_visual_ocr" for e in resultado["erros"]))

    def test_never_touches_status_atendimento(self):
        self._patch_all_llm_none()
        status_antes = self.atendimento.status_atendimento
        grafo = build_graph()

        grafo.invoke({"atendimento_id": self.atendimento.id, "erros": []})

        self.atendimento.refresh_from_db()
        self.assertEqual(self.atendimento.status_atendimento, status_antes)
