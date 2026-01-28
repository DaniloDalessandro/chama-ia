from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


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
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255)
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
