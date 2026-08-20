from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from datetime import timedelta
import secrets


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("O email é obrigatório")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        return self.create_user(email, password, **extra_fields)


class Direction(models.Model):
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "directions"

    def __str__(self):
        return self.name


class Management(models.Model):
    name = models.CharField(max_length=255)
    direction = models.ForeignKey(Direction, on_delete=models.CASCADE, related_name="managements")
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "managements"

    def __str__(self):
        return self.name


class Coordination(models.Model):
    name = models.CharField(max_length=255)
    management = models.ForeignKey(Management, on_delete=models.CASCADE, related_name="coordinations")
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "coordinations"

    def __str__(self):
        return self.name


class CustomUser(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        ADMIN = "admin", "Administrador"
        ATENDENTE = "atendente", "Atendente"
        CLIENTE = "cliente", "Cliente"

    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CLIENTE,
        verbose_name="Perfil",
    )
    cpf = models.CharField(max_length=14, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    avatar = models.URLField(blank=True, null=True)

    direction = models.ForeignKey(Direction, on_delete=models.SET_NULL, null=True, blank=True)
    management = models.ForeignKey(Management, on_delete=models.SET_NULL, null=True, blank=True)
    coordination = models.ForeignKey(Coordination, on_delete=models.SET_NULL, null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    class Meta:
        db_table = "users"

    def __str__(self):
        return self.email


class PasswordResetToken(models.Model):
    """
    Model para armazenar tokens de recuperação de senha.

    Regras:
    - Token único gerado com secrets.token_urlsafe(32)
    - Validade padrão: 1 hora
    - Token invalidado após uso
    - Log de IP e data para auditoria
    """

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="password_reset_tokens",
        verbose_name="Usuário"
    )
    token = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        verbose_name="Token"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Criado em"
    )
    expires_at = models.DateTimeField(
        verbose_name="Expira em"
    )
    is_used = models.BooleanField(
        default=False,
        verbose_name="Usado"
    )
    used_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Usado em"
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="Endereço IP"
    )

    class Meta:
        db_table = "password_reset_tokens"
        verbose_name = "Token de Recuperação de Senha"
        verbose_name_plural = "Tokens de Recuperação de Senha"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["token", "is_used", "expires_at"]),
            models.Index(fields=["user", "created_at"]),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.token[:8]}... - {'Usado' if self.is_used else 'Válido' if self.is_valid() else 'Expirado'}"

    @staticmethod
    def generate_token():
        """Gera um token seguro único."""
        return secrets.token_urlsafe(32)

    def is_valid(self):
        """Verifica se o token é válido (não usado e não expirado)."""
        if self.is_used:
            return False
        if timezone.now() > self.expires_at:
            return False
        return True

    def mark_as_used(self):
        """Marca o token como usado."""
        self.is_used = True
        self.used_at = timezone.now()
        self.save(update_fields=["is_used", "used_at"])

    @classmethod
    def create_for_user(cls, user, ip_address=None, validity_hours=1):
        """
        Cria um novo token de reset para o usuário.

        Args:
            user: Instância do CustomUser
            ip_address: IP da requisição (opcional)
            validity_hours: Horas de validade (padrão: 1 hora)

        Returns:
            Instância do PasswordResetToken
        """
        # Invalidar tokens anteriores não utilizados do mesmo usuário
        cls.objects.filter(
            user=user,
            is_used=False,
            expires_at__gt=timezone.now()
        ).update(is_used=True, used_at=timezone.now())

        # Criar novo token
        token = cls.generate_token()
        expires_at = timezone.now() + timedelta(hours=validity_hours)

        return cls.objects.create(
            user=user,
            token=token,
            expires_at=expires_at,
            ip_address=ip_address
        )
