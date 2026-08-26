"""
Mixins de auditoria e exclusao logica reutilizados pelos apps `ahp` e `atendimento`.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone


class AuditModelMixin(models.Model):
    """Campos padrao de auditoria: quem/quando criou e atualizou pela ultima vez."""

    criado_em = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name="Criado por",
    )
    atualizado_em = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")
    atualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name="Atualizado por",
    )

    class Meta:
        abstract = True


class SoftDeleteModelMixin(models.Model):
    """Exclusao logica: o registro nunca e removido fisicamente do banco."""

    excluido_em = models.DateTimeField(null=True, blank=True, verbose_name="Excluido em")
    excluido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name="Excluido por",
    )

    class Meta:
        abstract = True

    @property
    def is_excluido(self) -> bool:
        return self.excluido_em is not None

    def soft_delete(self, user=None):
        self.excluido_em = timezone.now()
        self.excluido_por = user
        self.save(update_fields=["excluido_em", "excluido_por"])

    def restaurar(self):
        self.excluido_em = None
        self.excluido_por = None
        self.save(update_fields=["excluido_em", "excluido_por"])


class NotDeletedManager(models.Manager):
    """Manager padrao: exclui registros com exclusao logica aplicada."""

    def get_queryset(self):
        return super().get_queryset().filter(excluido_em__isnull=True)
