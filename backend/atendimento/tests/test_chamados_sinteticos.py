"""
30 testes com chamados sinteticos cobrindo todos os caminhos de entrada:

  - Fonte 1 (testes 01-15): classify_from_intensidades — entrada direta via dict,
    sem criar Atendimento no banco. Cobre todas as bandas (P1/P2/P3/P4/revisao_humana)
    com cenarios reais de suporte.

  - Fonte 2 (testes 16-25): classify() — avaliações persistidas em
    AvaliacaoCriterioAtendimento + persist() para verificar auditoria.

  - Fonte 3 (testes 26-30): agente6_node — simulando saída do Agente 4 (LLM)
    via state dict, como acontece no pipeline real de chat.

Pesos derivados da matriz consistente usada no setUp:
  w_U = 8/15  w_I = 4/15  w_S = 2/15  w_T = 1/15
Prioridades de intensidade: p_baixa = 1/7  p_moderada = 2/7  p_critica = 4/7
p_max = 4/7  (todos criticos)

Bandas: P1 >= 80  |  P2 >= 60  |  P3 >= 35  |  P4 < 35
"""

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
from atendimento.ai.agents.agente6_ahp import agente6_node
from atendimento.models import Atendimento, AuditoriaClassificacao, AvaliacaoCriterioAtendimento
from atendimento.services.classification_service import ServicePriorityClassificationService
from atendimento.services.persistence_service import ServicePersistenceService

User = get_user_model()

# Matriz AHP consistente com CR ~ 0 (distancias de ordem)
_PESOS_CRITERIOS = {(0, 1): 2.0, (0, 2): 4.0, (0, 3): 8.0, (1, 2): 2.0, (1, 3): 4.0, (2, 3): 2.0}
_PESOS_INTENSIDADES = {(0, 1): 0.5, (0, 2): 0.25, (1, 2): 0.5}


# ---------------------------------------------------------------------------
# Mixin de setup compartilhado
# ---------------------------------------------------------------------------

class _AHPMixin:
    """Cria criterios, intensidades, faixas de tempo e VersaoAHP ativa."""

    def _setup_ahp(self):
        self.user = User.objects.create_user(
            email="admin@sinteticos.com", password="x", name="Admin", role="admin"
        )
        self.criterios = {}
        self.intensidades = {}
        for ordem, codigo in enumerate(
            [CODIGO_URGENCIA, CODIGO_IMPACTO_NO_CLIENTE, CODIGO_SENTIMENTO_DO_CLIENTE, CODIGO_TEMPO_DE_ESPERA],
            start=1,
        ):
            c = Criterio.objects.create(nome=codigo.title(), codigo=codigo, ordem=ordem)
            self.criterios[codigo] = c
            Intensidade.objects.create(criterio=c, nome="Ausente", codigo=Intensidade.Codigo.AUSENTE, ordem=1)
            b = Intensidade.objects.create(criterio=c, nome="Baixa", codigo=Intensidade.Codigo.BAIXA, ordem=2)
            m = Intensidade.objects.create(criterio=c, nome="Moderada", codigo=Intensidade.Codigo.MODERADA, ordem=3)
            cr = Intensidade.objects.create(criterio=c, nome="Critica", codigo=Intensidade.Codigo.CRITICA, ordem=4)
            Intensidade.objects.create(criterio=c, nome="Inconclusiva", codigo=Intensidade.Codigo.INCONCLUSIVA, ordem=5)
            self.intensidades[codigo] = {"baixa": b, "moderada": m, "critica": cr}

        ct = self.criterios[CODIGO_TEMPO_DE_ESPERA]
        FaixaTempoEspera.objects.create(criterio=ct, minutos_min=0, minutos_max=5,
                                        intensidade=self.intensidades[CODIGO_TEMPO_DE_ESPERA]["baixa"], ordem=1)
        FaixaTempoEspera.objects.create(criterio=ct, minutos_min=5, minutos_max=15,
                                        intensidade=self.intensidades[CODIGO_TEMPO_DE_ESPERA]["moderada"], ordem=2)
        FaixaTempoEspera.objects.create(criterio=ct, minutos_min=15, minutos_max=None,
                                        intensidade=self.intensidades[CODIGO_TEMPO_DE_ESPERA]["critica"], ordem=3)

        ordenados = [self.criterios[c] for c in
                     [CODIGO_URGENCIA, CODIGO_IMPACTO_NO_CLIENTE, CODIGO_SENTIMENTO_DO_CLIENTE, CODIGO_TEMPO_DE_ESPERA]]
        rascunho = AHPVersionService.create_rascunho(user=self.user)
        AHPComparisonService.save_comparacoes_criterios(rascunho, ordenados, _PESOS_CRITERIOS, user=self.user)
        for codigo, criterio in self.criterios.items():
            lista = [self.intensidades[codigo]["baixa"],
                     self.intensidades[codigo]["moderada"],
                     self.intensidades[codigo]["critica"]]
            AHPComparisonService.save_comparacoes_intensidades(rascunho, criterio, lista,
                                                               _PESOS_INTENSIDADES, user=self.user)
        AHPVersionService.ativar(rascunho, user=self.user)
        self.versao = AHPVersionService.get_versao_ativa()

    def _int(self, urgencia="critica", impacto="critica", sentimento="critica", tempo="critica"):
        return {
            CODIGO_URGENCIA: urgencia,
            CODIGO_IMPACTO_NO_CLIENTE: impacto,
            CODIGO_SENTIMENTO_DO_CLIENTE: sentimento,
            CODIGO_TEMPO_DE_ESPERA: tempo,
        }

    def _avaliar_db(self, atendimento, urgencia="critica", impacto="critica",
                    sentimento="critica", tempo="critica"):
        """Cria AvaliacaoCriterioAtendimento para os 4 criterios."""
        mapa = {
            CODIGO_URGENCIA: urgencia,
            CODIGO_IMPACTO_NO_CLIENTE: impacto,
            CODIGO_SENTIMENTO_DO_CLIENTE: sentimento,
            CODIGO_TEMPO_DE_ESPERA: tempo,
        }
        for codigo, nivel in mapa.items():
            if nivel == "inconclusiva":
                intensidade = Intensidade.objects.get(criterio=self.criterios[codigo],
                                                      codigo=Intensidade.Codigo.INCONCLUSIVA)
            else:
                intensidade = self.intensidades[codigo][nivel]
            AvaliacaoCriterioAtendimento.objects.create(
                atendimento=atendimento, criterio=self.criterios[codigo],
                intensidade=intensidade, origem="manual",
            )


# ===========================================================================
# FONTE 1 — classify_from_intensidades (sem Atendimento no banco)
# ===========================================================================

class ChamadosSinteticosDirectTests(_AHPMixin, TestCase):
    """
    15 cenarios via classify_from_intensidades.
    Nenhuma chamada de LLM — entrada direta por dict de intensidades.
    """

    def setUp(self):
        self._setup_ahp()

    # --- P1 ---

    def test_01_servidor_web_completamente_fora_do_ar(self):
        """Todos os criterios criticos — indice = 100, P1."""
        r = ServicePriorityClassificationService.classify_from_intensidades(
            self.versao, self._int()
        )
        self.assertFalse(r.revisao_humana)
        self.assertAlmostEqual(r.indice, 100.0, places=3)
        self.assertEqual(r.prioridade, Atendimento.Prioridade.P1)

    def test_02_sistema_de_pagamento_bloqueado(self):
        """U=C I=C S=C T=B — clientes nao conseguem pagar, atendimento recente."""
        r = ServicePriorityClassificationService.classify_from_intensidades(
            self.versao, self._int(tempo="baixa")
        )
        self.assertFalse(r.revisao_humana)
        self.assertGreaterEqual(r.indice, 80.0)
        self.assertEqual(r.prioridade, Atendimento.Prioridade.P1)

    def test_03_dados_corrompidos_sem_backup(self):
        """U=C I=C S=B T=B — urgencia e impacto maximos, sentimento baixo."""
        r = ServicePriorityClassificationService.classify_from_intensidades(
            self.versao, self._int(sentimento="baixa", tempo="baixa")
        )
        self.assertFalse(r.revisao_humana)
        self.assertAlmostEqual(r.indice, 85.0, places=1)
        self.assertEqual(r.prioridade, Atendimento.Prioridade.P1)

    def test_04_sistema_de_nfe_em_falha_total(self):
        """U=C I=C S=M T=B — NF-e parada, equipe moderadamente irritada."""
        r = ServicePriorityClassificationService.classify_from_intensidades(
            self.versao, self._int(sentimento="moderada", tempo="baixa")
        )
        self.assertFalse(r.revisao_humana)
        self.assertGreater(r.indice, 80.0)
        self.assertEqual(r.prioridade, Atendimento.Prioridade.P1)

    def test_05_cliente_perdendo_vendas_em_tempo_real(self):
        """U=C I=M S=C T=B — alta urgencia, impacto moderado, cliente em panico."""
        r = ServicePriorityClassificationService.classify_from_intensidades(
            self.versao, self._int(impacto="moderada", tempo="baixa")
        )
        self.assertFalse(r.revisao_humana)
        self.assertGreaterEqual(r.indice, 80.0)
        self.assertEqual(r.prioridade, Atendimento.Prioridade.P1)

    # --- P2 ---

    def test_06_lentidao_severa_afetando_todos_usuarios(self):
        """U=M I=C S=C T=B — sistema lento mas funcional, impacto alto."""
        r = ServicePriorityClassificationService.classify_from_intensidades(
            self.versao, self._int(urgencia="moderada", tempo="baixa")
        )
        self.assertFalse(r.revisao_humana)
        self.assertGreaterEqual(r.indice, 60.0)
        self.assertLess(r.indice, 80.0)
        self.assertEqual(r.prioridade, Atendimento.Prioridade.P2)

    def test_07_acesso_negado_para_equipe_inteira(self):
        """U=C I=M S=M T=B — sem acesso, mas nao ha perda de dados."""
        r = ServicePriorityClassificationService.classify_from_intensidades(
            self.versao, self._int(impacto="moderada", sentimento="moderada", tempo="baixa")
        )
        self.assertFalse(r.revisao_humana)
        self.assertAlmostEqual(r.indice, 75.0, places=1)
        self.assertEqual(r.prioridade, Atendimento.Prioridade.P2)

    def test_08_integracao_erp_intermitente(self):
        """U=M I=C S=M T=B — falha intermitente, impacto alto mas nao critico."""
        r = ServicePriorityClassificationService.classify_from_intensidades(
            self.versao, self._int(urgencia="moderada", sentimento="moderada", tempo="baixa")
        )
        self.assertFalse(r.revisao_humana)
        self.assertGreaterEqual(r.indice, 60.0)
        self.assertLess(r.indice, 80.0)
        self.assertEqual(r.prioridade, Atendimento.Prioridade.P2)

    def test_09_relatorio_de_vendas_com_valores_errados(self):
        """U=C I=B S=C T=M — relatorio errado, cliente irritado, pouco impacto operacional."""
        r = ServicePriorityClassificationService.classify_from_intensidades(
            self.versao, self._int(impacto="baixa", tempo="moderada")
        )
        self.assertFalse(r.revisao_humana)
        self.assertGreaterEqual(r.indice, 60.0)
        self.assertLess(r.indice, 80.0)
        self.assertEqual(r.prioridade, Atendimento.Prioridade.P2)

    # --- P3 ---

    def test_10_funcionalidade_travada_uso_moderado(self):
        """Todos moderada — situacao padrao de suporte, indice = 50."""
        r = ServicePriorityClassificationService.classify_from_intensidades(
            self.versao, self._int(urgencia="moderada", impacto="moderada",
                                   sentimento="moderada", tempo="moderada")
        )
        self.assertFalse(r.revisao_humana)
        self.assertAlmostEqual(r.indice, 50.0, places=1)
        self.assertEqual(r.prioridade, Atendimento.Prioridade.P3)

    def test_11_bug_em_exportacao_baixa_urgencia(self):
        """U=B I=C S=M T=B — bug no export, nao bloqueia fluxo principal."""
        r = ServicePriorityClassificationService.classify_from_intensidades(
            self.versao, self._int(urgencia="baixa", sentimento="moderada", tempo="baixa")
        )
        self.assertFalse(r.revisao_humana)
        self.assertGreaterEqual(r.indice, 35.0)
        self.assertLess(r.indice, 60.0)
        self.assertEqual(r.prioridade, Atendimento.Prioridade.P3)

    def test_12_botao_com_visual_quebrado_baixa_urgencia(self):
        """U=B I=M S=C T=B — erro cosmético, cliente irritado mas sem impacto real."""
        r = ServicePriorityClassificationService.classify_from_intensidades(
            self.versao, self._int(urgencia="baixa", impacto="moderada", tempo="baixa")
        )
        self.assertFalse(r.revisao_humana)
        self.assertGreaterEqual(r.indice, 35.0)
        self.assertLess(r.indice, 60.0)
        self.assertEqual(r.prioridade, Atendimento.Prioridade.P3)

    # --- P4 ---

    def test_13_duvida_sobre_uso_de_funcionalidade(self):
        """Todos baixa — apenas uma pergunta, sem problema real. indice = 25."""
        r = ServicePriorityClassificationService.classify_from_intensidades(
            self.versao, self._int(urgencia="baixa", impacto="baixa",
                                   sentimento="baixa", tempo="baixa")
        )
        self.assertFalse(r.revisao_humana)
        self.assertAlmostEqual(r.indice, 25.0, places=1)
        self.assertEqual(r.prioridade, Atendimento.Prioridade.P4)

    def test_14_sugestao_de_melhoria_de_interface(self):
        """U=B I=B S=M T=B — pedido de feature, cliente educado, sem urgencia."""
        r = ServicePriorityClassificationService.classify_from_intensidades(
            self.versao, self._int(urgencia="baixa", impacto="baixa",
                                   sentimento="moderada", tempo="baixa")
        )
        self.assertFalse(r.revisao_humana)
        self.assertLess(r.indice, 35.0)
        self.assertEqual(r.prioridade, Atendimento.Prioridade.P4)

    # --- revisao_humana ---

    def test_15_urgencia_inconclusiva_dispara_revisao(self):
        """LLM nao conseguiu avaliar URGENCIA — revisao humana obrigatoria."""
        intensidades = self._int()
        intensidades[CODIGO_URGENCIA] = Intensidade.Codigo.INCONCLUSIVA
        r = ServicePriorityClassificationService.classify_from_intensidades(
            self.versao, intensidades
        )
        self.assertTrue(r.revisao_humana)
        self.assertEqual(r.prioridade, Atendimento.Prioridade.REVISAO_HUMANA)
        self.assertIsNone(r.indice)
        self.assertTrue(any(CODIGO_URGENCIA in m for m in r.motivos_revisao_humana))


# ===========================================================================
# FONTE 2 — classify() via AvaliacaoCriterioAtendimento no banco
# ===========================================================================

class ChamadosSinteticosDBTests(_AHPMixin, TestCase):
    """
    10 cenarios via classify() com avaliacoes persistidas no banco.
    Inclui persist() para verificar consistencia da AuditoriaClassificacao.
    """

    def setUp(self):
        self._setup_ahp()

    # --- P1 ---

    def test_16_ecommerce_sistema_fora_do_ar_via_db(self):
        """Todos criticos no banco — P1 com indice = 100."""
        at = Atendimento.objects.create(nome="Loja Virtual", email="loja@test.com")
        self._avaliar_db(at)
        r = ServicePriorityClassificationService.classify(at)
        self.assertEqual(r.prioridade, Atendimento.Prioridade.P1)
        self.assertAlmostEqual(r.indice, 100.0, places=3)
        self.assertFalse(r.revisao_humana)

    def test_17_financeiro_nao_processa_pagamentos_via_db(self):
        """U=C I=C S=B T=B no banco — pagamento parado, indice ~85."""
        at = Atendimento.objects.create(nome="Financeiro", email="fin@test.com")
        self._avaliar_db(at, sentimento="baixa", tempo="baixa")
        r = ServicePriorityClassificationService.classify(at)
        self.assertEqual(r.prioridade, Atendimento.Prioridade.P1)
        self.assertAlmostEqual(r.indice, 85.0, places=1)

    # --- P2 ---

    def test_18_cliente_vip_sem_acesso_via_db(self):
        """U=M I=C S=M T=B no banco — cliente VIP bloqueado, mas sistema funciona."""
        at = Atendimento.objects.create(nome="Cliente VIP", email="vip@test.com")
        self._avaliar_db(at, urgencia="moderada", sentimento="moderada", tempo="baixa")
        r = ServicePriorityClassificationService.classify(at)
        self.assertEqual(r.prioridade, Atendimento.Prioridade.P2)
        self.assertGreaterEqual(r.indice, 60.0)
        self.assertLess(r.indice, 80.0)

    def test_19_sistema_lento_varios_usuarios_via_db(self):
        """U=C I=M S=M T=B no banco — lentidao generalizada, indice = 75."""
        at = Atendimento.objects.create(nome="TI Corporativo", email="ti@test.com")
        self._avaliar_db(at, impacto="moderada", sentimento="moderada", tempo="baixa")
        r = ServicePriorityClassificationService.classify(at)
        self.assertEqual(r.prioridade, Atendimento.Prioridade.P2)
        self.assertAlmostEqual(r.indice, 75.0, places=1)

    # --- P3 ---

    def test_20_bug_menor_em_relatorio_via_db(self):
        """Todos moderada no banco — bug comum, indice = 50."""
        at = Atendimento.objects.create(nome="Contabilidade", email="conta@test.com")
        self._avaliar_db(at, urgencia="moderada", impacto="moderada",
                         sentimento="moderada", tempo="moderada")
        r = ServicePriorityClassificationService.classify(at)
        self.assertEqual(r.prioridade, Atendimento.Prioridade.P3)
        self.assertAlmostEqual(r.indice, 50.0, places=1)

    def test_21_label_errada_sem_impacto_critico_via_db(self):
        """U=B I=M S=C T=B no banco — erro visual, cliente irritado."""
        at = Atendimento.objects.create(nome="Marketing", email="mkt@test.com")
        self._avaliar_db(at, urgencia="baixa", impacto="moderada", tempo="baixa")
        r = ServicePriorityClassificationService.classify(at)
        self.assertEqual(r.prioridade, Atendimento.Prioridade.P3)
        self.assertGreaterEqual(r.indice, 35.0)

    # --- P4 ---

    def test_22_pergunta_sobre_configuracao_via_db(self):
        """Todos baixa no banco — duvida simples, sem urgencia. indice = 25."""
        at = Atendimento.objects.create(nome="Novo Usuario", email="novo@test.com")
        self._avaliar_db(at, urgencia="baixa", impacto="baixa",
                         sentimento="baixa", tempo="baixa")
        r = ServicePriorityClassificationService.classify(at)
        self.assertEqual(r.prioridade, Atendimento.Prioridade.P4)
        self.assertAlmostEqual(r.indice, 25.0, places=1)

    def test_23_solicitacao_de_novo_usuario_via_db(self):
        """U=B I=B S=M T=B no banco — pedido de cadastro, sem urgencia."""
        at = Atendimento.objects.create(nome="RH", email="rh@test.com")
        self._avaliar_db(at, urgencia="baixa", impacto="baixa",
                         sentimento="moderada", tempo="baixa")
        r = ServicePriorityClassificationService.classify(at)
        self.assertEqual(r.prioridade, Atendimento.Prioridade.P4)
        self.assertLess(r.indice, 35.0)

    # --- revisao_humana ---

    def test_24_criterio_ausente_no_banco_dispara_revisao(self):
        """Apenas 3 dos 4 criterios avaliados — criterio ausente gera revisao."""
        at = Atendimento.objects.create(nome="Sem Avaliacao Completa", email="parcial@test.com")
        # Avalia apenas 3 criterios (sem TEMPO_DE_ESPERA)
        for codigo in [CODIGO_URGENCIA, CODIGO_IMPACTO_NO_CLIENTE, CODIGO_SENTIMENTO_DO_CLIENTE]:
            AvaliacaoCriterioAtendimento.objects.create(
                atendimento=at,
                criterio=self.criterios[codigo],
                intensidade=self.intensidades[codigo]["moderada"],
                origem="manual",
            )
        r = ServicePriorityClassificationService.classify(at)
        self.assertTrue(r.revisao_humana)
        self.assertEqual(r.prioridade, Atendimento.Prioridade.REVISAO_HUMANA)

    # --- consistencia da auditoria ---

    def test_25_reclassificacao_gera_nova_auditoria_imutavel(self):
        """
        Persist → reclassifica → persist novamente.
        Deve existir 2 registros de AuditoriaClassificacao (append-only).
        """
        at = Atendimento.objects.create(nome="Reclassificado", email="reclass@test.com")

        # Primeira classificacao: todos moderada → P3
        self._avaliar_db(at, urgencia="moderada", impacto="moderada",
                         sentimento="moderada", tempo="moderada")
        r1 = ServicePriorityClassificationService.classify(at)
        self.assertEqual(r1.prioridade, Atendimento.Prioridade.P3)
        ServicePersistenceService.persist(at, r1, self.versao, user=self.user)

        at.refresh_from_db()
        self.assertEqual(at.prioridade, Atendimento.Prioridade.P3)

        # Muda as avaliacoes para todos critico → P1
        at.avaliacoes.all().delete()
        self._avaliar_db(at)
        r2 = ServicePriorityClassificationService.classify(at)
        self.assertEqual(r2.prioridade, Atendimento.Prioridade.P1)
        ServicePersistenceService.persist(at, r2, self.versao, user=self.user)

        at.refresh_from_db()
        self.assertEqual(at.prioridade, Atendimento.Prioridade.P1)

        # As duas auditorias devem existir (imutabilidade)
        auditorias = AuditoriaClassificacao.objects.filter(atendimento=at).order_by("criado_em")
        self.assertEqual(auditorias.count(), 2)
        self.assertEqual(auditorias[0].prioridade, Atendimento.Prioridade.P3)
        self.assertEqual(auditorias[1].prioridade, Atendimento.Prioridade.P1)


# ===========================================================================
# FONTE 3 — agente6_node (simula output do Agente 4 via state dict)
# ===========================================================================

class ChamadosSinteticosAgente6Tests(_AHPMixin, TestCase):
    """
    5 cenarios via agente6_node, simulando o state que chegaria do Agente 4
    no pipeline real de chat (LangGraph). TEMPO_DE_ESPERA e calculado
    deterministicamente por WaitingTimeService (atendimento recem-criado = baixa).
    """

    def setUp(self):
        self._setup_ahp()
        self.atendimento = Atendimento.objects.create(nome="Chat Cliente", email="chat@test.com")

    def _state(self, avaliacoes):
        return {
            "atendimento_id": self.atendimento.id,
            "agente4_resultado": {"avaliacoes": avaliacoes},
        }

    def _av(self, criterio, intensidade, confianca=1.0):
        return {"criterio_codigo": criterio, "intensidade_codigo": intensidade, "confianca": confianca}

    # --- test 26 ---

    def test_26_chat_todos_criticos_via_agente4_p1(self):
        """
        Agente 4 retorna critica em todos os 3 criterios interpretativos
        com confianca plena. TEMPO_DE_ESPERA = baixa (atendimento recente).
        Resultado esperado: P1, sem revisao.
        """
        avaliacoes = [
            self._av(CODIGO_URGENCIA, "critica"),
            self._av(CODIGO_IMPACTO_NO_CLIENTE, "critica"),
            self._av(CODIGO_SENTIMENTO_DO_CLIENTE, "critica"),
        ]
        resultado = agente6_node(self._state(avaliacoes))
        r = resultado["agente6_resultado"]

        self.assertEqual(resultado["erros"], [])
        self.assertFalse(r["revisao_humana"])
        self.assertEqual(r["prioridade"], Atendimento.Prioridade.P1)
        self.assertGreaterEqual(r["indice"], 80.0)

    # --- test 27 ---

    def test_27_chat_urgencia_moderada_impacto_alto_p2(self):
        """
        U=moderada I=critica S=moderada do Agente 4 + T=baixa (WaitingTime).
        indice ~ 61.7 → P2.
        """
        avaliacoes = [
            self._av(CODIGO_URGENCIA, "moderada"),
            self._av(CODIGO_IMPACTO_NO_CLIENTE, "critica"),
            self._av(CODIGO_SENTIMENTO_DO_CLIENTE, "moderada"),
        ]
        resultado = agente6_node(self._state(avaliacoes))
        r = resultado["agente6_resultado"]

        self.assertEqual(resultado["erros"], [])
        self.assertFalse(r["revisao_humana"])
        self.assertEqual(r["prioridade"], Atendimento.Prioridade.P2)

    # --- test 28 ---

    def test_28_chat_baixa_prioridade_todos_baixo_p4(self):
        """
        Todos os criterios interpretativos baixo + T=baixa (WaitingTime).
        indice = 25 → P4.
        """
        avaliacoes = [
            self._av(CODIGO_URGENCIA, "baixa"),
            self._av(CODIGO_IMPACTO_NO_CLIENTE, "baixa"),
            self._av(CODIGO_SENTIMENTO_DO_CLIENTE, "baixa"),
        ]
        resultado = agente6_node(self._state(avaliacoes))
        r = resultado["agente6_resultado"]

        self.assertEqual(resultado["erros"], [])
        self.assertFalse(r["revisao_humana"])
        self.assertEqual(r["prioridade"], Atendimento.Prioridade.P4)
        self.assertAlmostEqual(r["indice"], 25.0, places=1)

    # --- test 29 ---

    def test_29_chat_inconclusiva_do_agente4_dispara_revisao(self):
        """
        Agente 4 retornou inconclusiva para URGENCIA (dados insuficientes no chat).
        Agente 6 deve propagar revisao_humana sem crash.
        """
        avaliacoes = [
            self._av(CODIGO_URGENCIA, "inconclusiva"),
            self._av(CODIGO_IMPACTO_NO_CLIENTE, "moderada"),
            self._av(CODIGO_SENTIMENTO_DO_CLIENTE, "moderada"),
        ]
        resultado = agente6_node(self._state(avaliacoes))
        r = resultado["agente6_resultado"]

        self.assertTrue(r["revisao_humana"])
        self.assertEqual(r["prioridade"], Atendimento.Prioridade.REVISAO_HUMANA)
        self.assertIsNone(r["indice"])

    # --- test 30 ---

    def test_30_chat_confianca_zero_borda_p1p2_dispara_revisao_fuzzy(self):
        """
        Agente 4 avalia URGENCIA=critica mas com confianca=0.0 (muita incerteza).
        indice_m ~ 95 (P1), mas indice_l ~ 76 (P2) — cruzamento de banda.
        Agente 6 deve sinalizar revisao_humana por ambiguidade fuzzy.
        """
        avaliacoes = [
            self._av(CODIGO_URGENCIA, "critica", confianca=0.0),
            self._av(CODIGO_IMPACTO_NO_CLIENTE, "critica", confianca=1.0),
            self._av(CODIGO_SENTIMENTO_DO_CLIENTE, "critica", confianca=1.0),
        ]
        resultado = agente6_node(self._state(avaliacoes))
        r = resultado["agente6_resultado"]

        self.assertEqual(resultado["erros"], [])
        self.assertTrue(r["revisao_humana"])
        self.assertEqual(r["prioridade"], Atendimento.Prioridade.REVISAO_HUMANA)
        self.assertIsNotNone(r["indice_l"])
        self.assertIsNotNone(r["indice_u"])
        self.assertLess(r["indice_l"], 80.0)
        self.assertGreaterEqual(r["indice_u"], 80.0)
        self.assertTrue(
            any("fuzzy" in m.lower() or "ambig" in m.lower() for m in r["motivos_revisao_humana"])
        )
