from django.db import models
from django.conf import settings


class Cliente(models.Model):
    """
    Model para cadastro de clientes da plataforma.
    """

    nome = models.CharField(max_length=255, verbose_name="Nome/Razão Social")
    nome_fantasia = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Nome Fantasia"
    )
    cnpj = models.CharField(
        max_length=18,
        unique=True,
        verbose_name="CNPJ",
        help_text="Formato: XX.XXX.XXX/XXXX-XX"
    )
    nome_responsavel = models.CharField(
        max_length=255,
        verbose_name="Nome do Responsável"
    )

    # Campos adicionais úteis
    email = models.EmailField(blank=True, verbose_name="E-mail Principal")
    telefone = models.CharField(max_length=20, blank=True, verbose_name="Telefone")
    endereco = models.TextField(blank=True, verbose_name="Endereço")

    # Status do cliente
    ativo = models.BooleanField(default=True, verbose_name="Ativo")

    # Campos de auditoria
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clientes_criados",
        verbose_name="Criado por"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clientes_atualizados",
        verbose_name="Atualizado por"
    )

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ["nome"]
        indexes = [
            models.Index(fields=["cnpj"]),
            models.Index(fields=["nome"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.nome_fantasia or self.nome} - {self.cnpj}"
