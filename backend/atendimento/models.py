"""
Modelos base do app `atendimento`: o contato inicial do cliente via chat,
suas mensagens/anexos, as avaliacoes de criterio (evidencia para o AHP),
regra critica, auditoria de classificacao e revisao humana.

Nesta fase (Fase 1) nao ha agentes de IA/LangGraph/DeepSeek envolvidos --
as avaliacoes de criterio sao inseridas manualmente (origem=MANUAL) apenas
para provar que o pipeline deterministico (AHP -> indice -> P1-P4) funciona
de ponta a ponta. As Fases seguintes populam esses mesmos campos via agentes,
sem precisar de nenhuma migracao nova.
"""

import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from ahp.mixins import AuditModelMixin

from .validators import AtendimentoFileValidator


class Atendimento(AuditModelMixin, models.Model):
    """
    O contato inicial do cliente via chat. Nunca e excluido -- apenas
    transiciona de status. E o objeto principal da priorizacao (nao o Chamado).
    """

    class StatusAtendimento(models.TextChoices):
        AGUARDANDO = "aguardando", "Aguardando"
        EM_ATENDIMENTO = "em_atendimento", "Em Atendimento"
        AGUARDANDO_CLIENTE = "aguardando_cliente", "Aguardando Cliente"
        RESOLVIDO = "resolvido", "Resolvido"
        CANCELADO = "cancelado", "Cancelado"
        ENCAMINHADO_PARA_CHAMADO = "encaminhado_para_chamado", "Encaminhado para Chamado"

    class Prioridade(models.TextChoices):
        NAO_CLASSIFICADO = "nao_classificado", "Nao Classificado"
        P1 = "p1", "P1 - Critica"
        P2 = "p2", "P2 - Alta"
        P3 = "p3", "P3 - Media"
        P4 = "p4", "P4 - Baixa"
        REVISAO_HUMANA = "revisao_humana", "Revisao Humana"

    class AnaliseIAStatus(models.TextChoices):
        PENDENTE = "pendente", "Pendente"
        PROCESSANDO = "processando", "Processando"
        CONCLUIDA = "concluida", "Concluida"
        ERRO = "erro", "Erro"

    class Origem(models.TextChoices):
        CHAT = "chat", "Chat"
        EMAIL = "email", "E-mail"

    session_token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        db_index=True,
        editable=False,
        verbose_name="Token de sessao (chat anonimo)",
        help_text="Prova de propriedade do atendimento para clientes anonimos -- nunca o pk numerico.",
    )
    origem = models.CharField(
        max_length=20, choices=Origem.choices, default=Origem.CHAT, verbose_name="Origem"
    )
    email_message_id = models.CharField(
        max_length=500, blank=True, db_index=True, verbose_name="Message-ID do Email"
    )
    assunto = models.CharField(max_length=255, blank=True, verbose_name="Assunto")
    resumo = models.TextField(blank=True, verbose_name="Resumo")
    servico_afetado = models.CharField(max_length=255, blank=True, verbose_name="Servico afetado")
    atendente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="atendimentos_atendidos",
        verbose_name="Atendente",
    )

    status_atendimento = models.CharField(
        max_length=30,
        choices=StatusAtendimento.choices,
        default=StatusAtendimento.AGUARDANDO,
        verbose_name="Status do atendimento",
    )
    prioridade = models.CharField(
        max_length=20,
        choices=Prioridade.choices,
        default=Prioridade.NAO_CLASSIFICADO,
        verbose_name="Prioridade",
    )
    analise_ia_status = models.CharField(
        max_length=15,
        choices=AnaliseIAStatus.choices,
        default=AnaliseIAStatus.PENDENTE,
        verbose_name="Status da analise de IA",
    )
    indice_ahp = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        verbose_name="Indice AHP",
    )
    regra_critica_confirmada = models.BooleanField(default=False, verbose_name="Regra critica confirmada")
    versao_ahp_utilizada = models.ForeignKey(
        "ahp.VersaoAHP",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="atendimentos",
        verbose_name="Versao AHP utilizada",
    )

    nome = models.CharField(max_length=255, verbose_name="Nome")
    email = models.EmailField(verbose_name="E-mail")
    telefone = models.CharField(max_length=20, blank=True, verbose_name="Telefone")
    cliente = models.ForeignKey(
        "clientes.Cliente",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="atendimentos",
        verbose_name="Cliente/Empresa",
    )

    class Meta:
        verbose_name = "Atendimento"
        verbose_name_plural = "Atendimentos"
        ordering = ["-criado_em"]
        indexes = [
            models.Index(fields=["status_atendimento"]),
            models.Index(fields=["prioridade"]),
            models.Index(fields=["criado_em"]),
        ]

    def __str__(self):
        return f"Atendimento #{self.pk} - {self.nome} ({self.get_status_atendimento_display()})"


class MensagemAtendimento(models.Model):
    """Mensagem trocada dentro de um atendimento (cliente, atendente ou sistema)."""

    class RemetenteTipo(models.TextChoices):
        CLIENTE = "cliente", "Cliente"
        ATENDENTE = "atendente", "Atendente"
        SISTEMA = "sistema", "Sistema"

    atendimento = models.ForeignKey(
        Atendimento, on_delete=models.CASCADE, related_name="mensagens", verbose_name="Atendimento"
    )
    remetente_tipo = models.CharField(max_length=15, choices=RemetenteTipo.choices, verbose_name="Remetente")
    conteudo = models.TextField(verbose_name="Conteudo")
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")

    class Meta:
        verbose_name = "Mensagem de Atendimento"
        verbose_name_plural = "Mensagens de Atendimento"
        ordering = ["criado_em"]

    def __str__(self):
        return f"[{self.atendimento_id}] {self.get_remetente_tipo_display()}: {self.conteudo[:50]}"


class AnexoAtendimento(models.Model):
    """Anexo enviado durante um atendimento (espelha AnexoChamado)."""

    class TipoArquivo(models.TextChoices):
        PDF = "pdf", "PDF"
        IMAGEM = "imagem", "Imagem"
        DOCUMENTO = "documento", "Documento"
        OUTRO = "outro", "Outro"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    atendimento = models.ForeignKey(
        Atendimento, on_delete=models.CASCADE, related_name="anexos", verbose_name="Atendimento"
    )
    arquivo = models.FileField(
        upload_to="atendimento/anexos/%Y/%m/", verbose_name="Arquivo", validators=[AtendimentoFileValidator()]
    )
    nome_original = models.CharField(max_length=255, verbose_name="Nome Original")
    tipo_arquivo = models.CharField(
        max_length=20, choices=TipoArquivo.choices, default=TipoArquivo.OUTRO, verbose_name="Tipo"
    )
    tamanho = models.PositiveIntegerField(verbose_name="Tamanho (bytes)")
    mime_type = models.CharField(max_length=100, blank=True, verbose_name="MIME Type")
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")

    class Meta:
        verbose_name = "Anexo de Atendimento"
        verbose_name_plural = "Anexos de Atendimento"
        ordering = ["criado_em"]

    def __str__(self):
        return f"{self.nome_original} (atendimento #{self.atendimento_id})"


class AvaliacaoCriterioAtendimento(AuditModelMixin, models.Model):
    """
    A intensidade escolhida para um criterio, com evidencia/justificativa.
    Uma linha por (atendimento, criterio) -- reavaliar atualiza a linha.
    """

    class Origem(models.TextChoices):
        MANUAL = "manual", "Manual"
        AGENTE_AVALIACAO = "agente_avaliacao", "Agente 4 - Avaliacao de Criterios"
        TEMPO_ESPERA_SERVICE = "tempo_espera_service", "WaitingTimeService (deterministico)"

    atendimento = models.ForeignKey(
        Atendimento, on_delete=models.CASCADE, related_name="avaliacoes", verbose_name="Atendimento"
    )
    criterio = models.ForeignKey("ahp.Criterio", on_delete=models.PROTECT, related_name="+", verbose_name="Criterio")
    intensidade = models.ForeignKey(
        "ahp.Intensidade", on_delete=models.PROTECT, related_name="+", verbose_name="Intensidade"
    )
    evidencia = models.TextField(blank=True, verbose_name="Evidencia")
    justificativa = models.TextField(blank=True, verbose_name="Justificativa")
    origem = models.CharField(max_length=20, choices=Origem.choices, default=Origem.MANUAL, verbose_name="Origem")
    confianca = models.FloatField(
        null=True, blank=True, validators=[MinValueValidator(0.0), MaxValueValidator(1.0)], verbose_name="Confianca"
    )
    dados_ausentes = models.BooleanField(default=False, verbose_name="Dados ausentes")

    class Meta:
        verbose_name = "Avaliacao de Criterio"
        verbose_name_plural = "Avaliacoes de Criterio"
        ordering = ["atendimento", "criterio__ordem"]
        constraints = [
            models.UniqueConstraint(fields=["atendimento", "criterio"], name="unique_avaliacao_por_atendimento_criterio")
        ]

    def __str__(self):
        return f"[{self.atendimento_id}] {self.criterio.codigo} = {self.intensidade.codigo}"


class RegraCriticaAtendimento(AuditModelMixin, models.Model):
    """Registro da checagem de regra critica (Agente 5, nas fases seguintes)."""

    class Origem(models.TextChoices):
        MANUAL = "manual", "Manual"
        AGENTE_VALIDACAO_CRITICA = "agente_validacao_critica", "Agente 5 - Validacao Critica"

    atendimento = models.OneToOneField(
        Atendimento, on_delete=models.CASCADE, related_name="regra_critica", verbose_name="Atendimento"
    )
    criterio_gatilho = models.ForeignKey(
        "ahp.Criterio", null=True, blank=True, on_delete=models.SET_NULL, related_name="+", verbose_name="Criterio gatilho"
    )
    termo_gatilho = models.ForeignKey(
        "ahp.Termo", null=True, blank=True, on_delete=models.SET_NULL, related_name="+", verbose_name="Termo gatilho"
    )
    confirmada = models.BooleanField(default=False, verbose_name="Confirmada")
    justificativa = models.TextField(blank=True, verbose_name="Justificativa")
    origem = models.CharField(max_length=30, choices=Origem.choices, default=Origem.MANUAL, verbose_name="Origem")

    class Meta:
        verbose_name = "Regra Critica de Atendimento"
        verbose_name_plural = "Regras Criticas de Atendimento"

    def __str__(self):
        return f"[{self.atendimento_id}] regra_critica={self.confirmada}"


class AuditoriaClassificacao(models.Model):
    """
    Registro imutavel (append-only) de uma classificacao AHP calculada para um
    atendimento. Nunca e editado -- uma reclassificacao gera uma nova linha.
    Mudancas futuras na configuracao do AHP NAO alteram registros ja gravados
    aqui, pois todos os valores usados no calculo ficam congelados nesta linha.
    """

    atendimento = models.ForeignKey(
        Atendimento, on_delete=models.CASCADE, related_name="auditorias", verbose_name="Atendimento"
    )
    versao_ahp = models.ForeignKey(
        "ahp.VersaoAHP", on_delete=models.PROTECT, related_name="auditorias", verbose_name="Versao AHP"
    )
    versao_hierarquia = models.PositiveIntegerField(verbose_name="Versao da hierarquia")
    versao_criterios = models.JSONField(default=dict, blank=True, verbose_name="Versao dos criterios")
    versao_termos = models.JSONField(default=dict, blank=True, verbose_name="Versao dos termos")
    versao_intensidades = models.JSONField(default=dict, blank=True, verbose_name="Versao das intensidades")
    versao_matriz_criterios = models.JSONField(verbose_name="Matriz de criterios (congelada)")
    versao_matriz_intensidades = models.JSONField(verbose_name="Matrizes de intensidades (congeladas)")
    versao_faixas = models.JSONField(default=dict, blank=True, verbose_name="Faixas de tempo de espera")

    pesos_criterios = models.JSONField(verbose_name="Pesos dos criterios")
    lambda_max = models.FloatField(verbose_name="Lambda max")
    ci = models.FloatField(verbose_name="CI")
    ri = models.FloatField(verbose_name="RI")
    cr = models.FloatField(verbose_name="CR")
    prioridades_locais = models.JSONField(verbose_name="Prioridades locais (intensidades)")
    intensidades = models.JSONField(verbose_name="Intensidades escolhidas")
    contribuicoes = models.JSONField(verbose_name="Contribuicoes por criterio")

    indice = models.FloatField(
        null=True, blank=True, verbose_name="Indice", help_text="Nulo quando a prioridade e REVISAO_HUMANA."
    )
    prioridade = models.CharField(max_length=20, verbose_name="Prioridade")
    classificacao_cor = models.CharField(max_length=7, verbose_name="Cor da classificacao")
    regra_critica = models.BooleanField(default=False, verbose_name="Regra critica aplicada")

    alteracoes_humanas = models.JSONField(default=list, blank=True, verbose_name="Alteracoes humanas")
    erros = models.JSONField(default=list, blank=True, verbose_name="Erros")

    modelo_deepseek = models.CharField(max_length=100, null=True, blank=True, verbose_name="Modelo DeepSeek")
    versao_prompt = models.CharField(max_length=50, null=True, blank=True, verbose_name="Versao do prompt")
    auditoria_ia = models.JSONField(
        default=dict, blank=True, verbose_name="Auditoria da IA",
        help_text="Saida do Agente 7 (checagens de consistencia), populado a partir da Fase 2.",
    )

    criado_em = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+", verbose_name="Criado por"
    )

    class Meta:
        verbose_name = "Auditoria de Classificacao"
        verbose_name_plural = "Auditorias de Classificacao"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"[{self.atendimento_id}] {self.prioridade} (indice={self.indice:.2f}) em {self.criado_em}"


class RevisaoHumanaAtendimento(AuditModelMixin, models.Model):
    """Alteracao manual de prioridade feita por um humano, com justificativa obrigatoria."""

    atendimento = models.ForeignKey(
        Atendimento, on_delete=models.CASCADE, related_name="revisoes", verbose_name="Atendimento"
    )
    prioridade_anterior = models.CharField(max_length=20, verbose_name="Prioridade anterior")
    nova_prioridade = models.CharField(max_length=20, verbose_name="Nova prioridade")
    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+", verbose_name="Responsavel"
    )
    justificativa = models.TextField(verbose_name="Justificativa")

    class Meta:
        verbose_name = "Revisao Humana de Atendimento"
        verbose_name_plural = "Revisoes Humanas de Atendimento"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"[{self.atendimento_id}] {self.prioridade_anterior} -> {self.nova_prioridade}"
