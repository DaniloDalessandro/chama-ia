"""
Modelos do motor AHP (Analytic Hierarchy Process) por mensuracao absoluta.

Este app e deliberadamente livre de qualquer dependencia de LLM/LangChain.
Contem apenas: cadastro de criterios/termos/intensidades/faixas de tempo,
as comparacoes par-a-par (escala de Saaty) e o versionamento da hierarquia.
Toda a matematica (autovetor, autovalor, CI, CR, sintese) vive em `ahp/services/`.
"""

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models

from .mixins import AuditModelMixin, NotDeletedManager, SoftDeleteModelMixin

# Codigos fixos dos 4 criterios obrigatorios da hierarquia (secao 1 do escopo).
CODIGO_URGENCIA = "URGENCIA"
CODIGO_IMPACTO_NO_CLIENTE = "IMPACTO_NO_CLIENTE"
CODIGO_SENTIMENTO_DO_CLIENTE = "SENTIMENTO_DO_CLIENTE"
CODIGO_TEMPO_DE_ESPERA = "TEMPO_DE_ESPERA"

CODIGOS_CRITERIOS_OBRIGATORIOS = (
    CODIGO_URGENCIA,
    CODIGO_IMPACTO_NO_CLIENTE,
    CODIGO_SENTIMENTO_DO_CLIENTE,
    CODIGO_TEMPO_DE_ESPERA,
)

HEX_COLOR_VALIDATOR = RegexValidator(
    regex=r"^#[0-9A-Fa-f]{6}$",
    message="Informe uma cor hexadecimal no formato #RRGGBB.",
)


class Criterio(AuditModelMixin, SoftDeleteModelMixin, models.Model):
    """Um dos criterios da hierarquia AHP (ex: Urgencia, Impacto no Cliente)."""

    class Orientacao(models.TextChoices):
        POSITIVA = "positiva", "Positiva (intensidade maior = maior prioridade)"
        NEGATIVA = "negativa", "Negativa (intensidade maior = menor prioridade)"

    class ImportanciaNegocio(models.TextChoices):
        BAIXA = "baixa", "Baixa"
        MEDIA = "media", "Media"
        ALTA = "alta", "Alta"

    nome = models.CharField(max_length=150, verbose_name="Nome")
    codigo = models.CharField(max_length=50, unique=True, verbose_name="Codigo")
    descricao = models.TextField(blank=True, verbose_name="Descricao")
    orientacao = models.CharField(
        max_length=10,
        choices=Orientacao.choices,
        default=Orientacao.POSITIVA,
        verbose_name="Orientacao",
    )
    ordem = models.PositiveIntegerField(default=0, verbose_name="Ordem")
    ativo = models.BooleanField(default=True, verbose_name="Ativo")
    importancia_negocio = models.CharField(
        max_length=10,
        choices=ImportanciaNegocio.choices,
        default=ImportanciaNegocio.MEDIA,
        verbose_name="Importancia para o negocio",
    )
    regra_critica = models.BooleanField(
        default=False,
        verbose_name="Regra critica",
        help_text="Se este criterio pode disparar uma regra critica de seguranca.",
    )
    exige_revisao_humana = models.BooleanField(default=False, verbose_name="Exige revisao humana")
    permite_deteccao_semantica = models.BooleanField(default=True, verbose_name="Permite deteccao semantica")
    orientacoes_para_ia = models.TextField(blank=True, verbose_name="Orientacoes para a IA")
    exemplos_positivos = models.TextField(blank=True, verbose_name="Exemplos positivos")
    exemplos_negativos = models.TextField(blank=True, verbose_name="Exemplos negativos")
    cor_identificacao = models.CharField(
        max_length=7,
        default="#64748B",
        validators=[HEX_COLOR_VALIDATOR],
        verbose_name="Cor de identificacao",
    )
    icone = models.CharField(max_length=100, blank=True, verbose_name="Icone")

    objects = NotDeletedManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = "Criterio"
        verbose_name_plural = "Criterios"
        ordering = ["ordem", "nome"]

    def __str__(self):
        return f"{self.nome} ({self.codigo})"


class Intensidade(AuditModelMixin, SoftDeleteModelMixin, models.Model):
    """Um nivel de intensidade possivel para um criterio (escala fixa de 7 codigos)."""

    class Codigo(models.TextChoices):
        AUSENTE = "ausente", "Ausente"
        MUITO_BAIXA = "muito_baixa", "Muito Baixa"
        BAIXA = "baixa", "Baixa"
        MODERADA = "moderada", "Moderada"
        ALTA = "alta", "Alta"
        CRITICA = "critica", "Critica"
        INCONCLUSIVA = "inconclusiva", "Inconclusiva"

    criterio = models.ForeignKey(
        Criterio,
        on_delete=models.PROTECT,
        related_name="intensidades",
        verbose_name="Criterio",
    )
    nome = models.CharField(max_length=100, verbose_name="Nome")
    codigo = models.CharField(max_length=20, choices=Codigo.choices, verbose_name="Codigo")
    descricao = models.TextField(blank=True, verbose_name="Descricao")
    ordem = models.PositiveIntegerField(default=0, verbose_name="Ordem")
    orientacoes_para_ia = models.TextField(blank=True, verbose_name="Orientacoes para a IA")
    exemplo_positivo = models.TextField(blank=True, verbose_name="Exemplo positivo")
    exemplo_negativo = models.TextField(blank=True, verbose_name="Exemplo negativo")
    ativo = models.BooleanField(default=True, verbose_name="Ativo")

    objects = NotDeletedManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = "Intensidade"
        verbose_name_plural = "Intensidades"
        ordering = ["criterio__ordem", "ordem"]
        constraints = [
            models.UniqueConstraint(
                fields=["criterio", "codigo"],
                name="unique_intensidade_por_criterio",
            )
        ]

    def __str__(self):
        return f"{self.criterio.codigo} / {self.get_codigo_display()}"


class Termo(AuditModelMixin, SoftDeleteModelMixin, models.Model):
    """Termo/expressao cadastrada que serve de evidencia para um criterio."""

    class TipoCorrespondencia(models.TextChoices):
        EXATO = "exato", "Exato"
        CONTEM = "contem", "Contem"
        EXPRESSAO = "expressao", "Expressao"
        REGEX_SEGURA = "regex_segura", "Regex Segura"
        SEMANTICO = "semantico", "Semantico"

    class StatusAprovacao(models.TextChoices):
        PENDENTE_APROVACAO = "pendente_aprovacao", "Pendente de Aprovacao"
        APROVADO = "aprovado", "Aprovado"
        REJEITADO = "rejeitado", "Rejeitado"

    criterio = models.ForeignKey(
        Criterio,
        on_delete=models.PROTECT,
        related_name="termos",
        verbose_name="Criterio",
    )
    termo = models.CharField(max_length=255, verbose_name="Termo")
    descricao = models.TextField(blank=True, verbose_name="Descricao")
    tipo_correspondencia = models.CharField(
        max_length=20,
        choices=TipoCorrespondencia.choices,
        default=TipoCorrespondencia.CONTEM,
        verbose_name="Tipo de correspondencia",
    )
    intensidade_base = models.ForeignKey(
        Intensidade,
        on_delete=models.PROTECT,
        related_name="termos_base",
        verbose_name="Intensidade base",
    )
    exige_contexto = models.BooleanField(default=False, verbose_name="Exige contexto")
    regra_critica = models.BooleanField(default=False, verbose_name="Regra critica")
    considerar_mensagem_atual = models.BooleanField(default=True, verbose_name="Considerar mensagem atual")
    considerar_historico = models.BooleanField(default=False, verbose_name="Considerar historico")
    considerar_anexos = models.BooleanField(default=False, verbose_name="Considerar anexos")
    considerar_imagens = models.BooleanField(default=False, verbose_name="Considerar imagens")
    status_aprovacao = models.CharField(
        max_length=20,
        choices=StatusAprovacao.choices,
        default=StatusAprovacao.APROVADO,
        verbose_name="Status de aprovacao",
    )
    ativo = models.BooleanField(default=True, verbose_name="Ativo")

    objects = NotDeletedManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = "Termo"
        verbose_name_plural = "Termos"
        ordering = ["criterio__ordem", "termo"]

    def __str__(self):
        return f"{self.termo} -> {self.criterio.codigo}"


class FaixaTempoEspera(AuditModelMixin, models.Model):
    """Faixa configuravel de tempo de espera (em minutos) mapeada para uma intensidade."""

    criterio = models.ForeignKey(
        Criterio,
        on_delete=models.CASCADE,
        related_name="faixas_tempo",
        limit_choices_to={"codigo": CODIGO_TEMPO_DE_ESPERA},
        verbose_name="Criterio",
    )
    minutos_min = models.PositiveIntegerField(verbose_name="Minutos (min)")
    minutos_max = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Minutos (max)",
        help_text="Deixe em branco para uma faixa aberta (ex: mais de 60 minutos).",
    )
    intensidade = models.ForeignKey(
        Intensidade,
        on_delete=models.PROTECT,
        related_name="faixas_tempo",
        verbose_name="Intensidade",
    )
    ordem = models.PositiveIntegerField(default=0, verbose_name="Ordem")
    ativo = models.BooleanField(default=True, verbose_name="Ativo")

    class Meta:
        verbose_name = "Faixa de Tempo de Espera"
        verbose_name_plural = "Faixas de Tempo de Espera"
        ordering = ["criterio__ordem", "ordem", "minutos_min"]

    def __str__(self):
        limite = f"{self.minutos_max}min" if self.minutos_max is not None else "+"
        return f"{self.minutos_min}-{limite} -> {self.intensidade.get_codigo_display()}"


class VersaoAHP(AuditModelMixin, models.Model):
    """Uma versao versionada e imutavel-uma-vez-ativa da hierarquia AHP."""

    class Estado(models.TextChoices):
        PENDENTE_CONFIGURACAO = "pendente_configuracao", "Pendente de Configuracao"
        RASCUNHO = "rascunho", "Rascunho"
        PROCESSANDO = "processando", "Processando"
        VALIDA = "valida", "Valida"
        INCONSISTENTE = "inconsistente", "Inconsistente"
        ATIVA = "ativa", "Ativa"
        ARQUIVADA = "arquivada", "Arquivada"
        ERRO = "erro", "Erro"

    numero_versao = models.PositiveIntegerField(unique=True, editable=False, verbose_name="Numero da versao")
    estado = models.CharField(
        max_length=25,
        choices=Estado.choices,
        default=Estado.RASCUNHO,
        verbose_name="Estado",
    )
    descricao = models.TextField(blank=True, verbose_name="Descricao")

    # Resultados congelados, populados apenas ao final de AHPVersionService.ativar().
    pesos_criterios = models.JSONField(null=True, blank=True, verbose_name="Pesos dos criterios")
    lambda_max_criterios = models.FloatField(null=True, blank=True, verbose_name="Lambda max (criterios)")
    ci_criterios = models.FloatField(null=True, blank=True, verbose_name="CI (criterios)")
    cr_criterios = models.FloatField(null=True, blank=True, verbose_name="CR (criterios)")

    prioridades_intensidades = models.JSONField(null=True, blank=True, verbose_name="Prioridades das intensidades")
    lambda_max_intensidades = models.JSONField(null=True, blank=True, verbose_name="Lambda max (intensidades)")
    ci_intensidades = models.JSONField(null=True, blank=True, verbose_name="CI (intensidades)")
    cr_intensidades = models.JSONField(null=True, blank=True, verbose_name="CR (intensidades)")

    p_max = models.FloatField(null=True, blank=True, verbose_name="P maximo")

    ativada_em = models.DateTimeField(null=True, blank=True, verbose_name="Ativada em")
    ativada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name="Ativada por",
    )
    arquivada_em = models.DateTimeField(null=True, blank=True, verbose_name="Arquivada em")
    mensagens_erro = models.JSONField(default=list, blank=True, verbose_name="Mensagens de erro")

    class Meta:
        verbose_name = "Versao AHP"
        verbose_name_plural = "Versoes AHP"
        ordering = ["-numero_versao"]
        constraints = [
            models.UniqueConstraint(
                fields=["estado"],
                condition=models.Q(estado="ativa"),
                name="unique_versao_ahp_ativa",
            )
        ]

    def __str__(self):
        return f"Versao {self.numero_versao} ({self.get_estado_display()})"

    def save(self, *args, **kwargs):
        if self.numero_versao is None:
            ultimo = VersaoAHP.objects.aggregate(models.Max("numero_versao"))["numero_versao__max"] or 0
            self.numero_versao = ultimo + 1
        super().save(*args, **kwargs)


class Comparacao(AuditModelMixin, models.Model):
    """
    Uma linha de comparacao par-a-par (escala de Saaty), guardada apenas para o
    triangulo superior (i < j pela ordem dos itens). A matriz reciproca completa
    e reconstruida por AHPMatrixService a partir destas linhas.
    """

    class Tipo(models.TextChoices):
        CRITERIOS = "criterios", "Criterios"
        INTENSIDADES = "intensidades", "Intensidades"

    versao_ahp = models.ForeignKey(
        VersaoAHP,
        on_delete=models.CASCADE,
        related_name="comparacoes",
        verbose_name="Versao AHP",
    )
    tipo = models.CharField(max_length=20, choices=Tipo.choices, verbose_name="Tipo")

    criterio_contexto = models.ForeignKey(
        Criterio,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="comparacoes_intensidade",
        verbose_name="Criterio de contexto",
        help_text="Preenchido apenas quando tipo=INTENSIDADES: qual criterio esta tendo suas intensidades comparadas.",
    )
    criterio_linha = models.ForeignKey(
        Criterio, null=True, blank=True, on_delete=models.PROTECT, related_name="+", verbose_name="Criterio (linha)"
    )
    criterio_coluna = models.ForeignKey(
        Criterio, null=True, blank=True, on_delete=models.PROTECT, related_name="+", verbose_name="Criterio (coluna)"
    )
    intensidade_linha = models.ForeignKey(
        Intensidade, null=True, blank=True, on_delete=models.PROTECT, related_name="+", verbose_name="Intensidade (linha)"
    )
    intensidade_coluna = models.ForeignKey(
        Intensidade, null=True, blank=True, on_delete=models.PROTECT, related_name="+", verbose_name="Intensidade (coluna)"
    )
    valor_saaty = models.FloatField(verbose_name="Valor (escala de Saaty)")

    class Meta:
        verbose_name = "Comparacao"
        verbose_name_plural = "Comparacoes"
        ordering = ["versao_ahp", "tipo", "id"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(
                        tipo="criterios",
                        criterio_linha__isnull=False,
                        criterio_coluna__isnull=False,
                        intensidade_linha__isnull=True,
                        intensidade_coluna__isnull=True,
                    )
                    | models.Q(
                        tipo="intensidades",
                        intensidade_linha__isnull=False,
                        intensidade_coluna__isnull=False,
                        criterio_linha__isnull=True,
                        criterio_coluna__isnull=True,
                        criterio_contexto__isnull=False,
                    )
                ),
                name="comparacao_campos_consistentes_com_tipo",
            )
        ]

    def __str__(self):
        if self.tipo == self.Tipo.CRITERIOS:
            return f"[{self.versao_ahp}] {self.criterio_linha_id} x {self.criterio_coluna_id} = {self.valor_saaty}"
        return (
            f"[{self.versao_ahp}] ({self.criterio_contexto_id}) "
            f"{self.intensidade_linha_id} x {self.intensidade_coluna_id} = {self.valor_saaty}"
        )
