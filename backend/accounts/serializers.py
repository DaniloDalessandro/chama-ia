from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import CustomUser


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = "email"

    def validate(self, attrs):
        data = super().validate(attrs)

        user = self.user
        data["user"] = {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "role_display": user.get_role_display(),
            "cpf": user.cpf,
            "phone": user.phone,
            "avatar": user.avatar,
            "direction_id": user.direction_id,
            "direction_name": user.direction.name if user.direction else None,
            "management_id": user.management_id,
            "management_name": user.management.name if user.management else None,
            "coordination_id": user.coordination_id,
            "coordination_name": user.coordination.name if user.coordination else None,
        }

        return data


class UserSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source="get_role_display", read_only=True)
    direction_name = serializers.CharField(source="direction.name", read_only=True)
    management_name = serializers.CharField(source="management.name", read_only=True)
    coordination_name = serializers.CharField(source="coordination.name", read_only=True)

    class Meta:
        model = CustomUser
        fields = [
            "id", "email", "name", "role", "role_display",
            "cpf", "phone", "avatar",
            "direction_id", "direction_name",
            "management_id", "management_name",
            "coordination_id", "coordination_name",
        ]
        read_only_fields = ["id", "email"]


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)


class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)


class PasswordResetConfirmSerializer(serializers.Serializer):
    uidb64 = serializers.CharField(required=True)
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)


class UserListSerializer(serializers.ModelSerializer):
    """Serializer para listagem de usuários (admin vê tudo)."""
    role_display = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = CustomUser
        fields = [
            "id",
            "email",
            "name",
            "role",
            "role_display",
            "cpf",
            "phone",
            "is_active",
            "is_staff",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class UserPublicSerializer(serializers.ModelSerializer):
    """
    Serializer para dados públicos de usuários.
    Usado quando um usuário comum visualiza outros usuários.
    Oculta informações sensíveis (e-mail completo, CPF, telefone).
    """
    role_display = serializers.CharField(source="get_role_display", read_only=True)
    email_domain = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            "id",
            "name",
            "role",
            "role_display",
            "email_domain",  # Apenas domínio, não e-mail completo
            "is_active",
        ]
        read_only_fields = fields

    def get_email_domain(self, obj):
        """Retorna apenas o domínio do e-mail, ocultando o usuário."""
        if obj.email:
            domain = obj.email.split('@')[-1]
            return f"***@{domain}"
        return None


class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer para criação de usuários."""
    password = serializers.CharField(write_only=True, required=True, min_length=6)
    password_confirm = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = CustomUser
        fields = [
            "email",
            "name",
            "role",
            "cpf",
            "phone",
            "password",
            "password_confirm",
            "is_active",
            "is_staff",
        ]

    def validate(self, attrs):
        if attrs.get('password') != attrs.get('password_confirm'):
            raise serializers.ValidationError({"password_confirm": "As senhas não coincidem"})
        attrs.pop('password_confirm')
        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = CustomUser.objects.create_user(password=password, **validated_data)
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer para atualização de usuários."""

    class Meta:
        model = CustomUser
        fields = [
            "name",
            "role",
            "cpf",
            "phone",
            "avatar",
            "is_active",
            "is_staff",
        ]


class UserResetPasswordSerializer(serializers.Serializer):
    """Serializer para resetar senha de um usuário (admin)."""
    new_password = serializers.CharField(required=True, min_length=6)


# ============================================
# Serializers de Recuperação de Senha
# ============================================

class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer para solicitar recuperação de senha."""
    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        """Normaliza o e-mail."""
        return value.lower().strip()


class PasswordResetValidateSerializer(serializers.Serializer):
    """Serializer para validar token de recuperação."""
    token = serializers.CharField(required=True, max_length=64)


class PasswordResetConfirmNewSerializer(serializers.Serializer):
    """Serializer para confirmar nova senha."""
    token = serializers.CharField(required=True, max_length=64)
    new_password = serializers.CharField(required=True, min_length=6)
    new_password_confirm = serializers.CharField(required=True, min_length=6)

    def validate(self, attrs):
        """Valida que as senhas coincidem."""
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                "new_password_confirm": "As senhas não coincidem."
            })
        return attrs
