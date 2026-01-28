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
    direction_name = serializers.CharField(source="direction.name", read_only=True)
    management_name = serializers.CharField(source="management.name", read_only=True)
    coordination_name = serializers.CharField(source="coordination.name", read_only=True)

    class Meta:
        model = CustomUser
        fields = [
            "id", "email", "name", "cpf", "phone", "avatar",
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
