from rest_framework import serializers
from .models import Cliente


class ClienteSerializer(serializers.ModelSerializer):
    """
    Serializer para o model Cliente.
    """
    created_by_name = serializers.CharField(
        source='created_by.get_full_name',
        read_only=True,
        allow_null=True
    )
    updated_by_name = serializers.CharField(
        source='updated_by.get_full_name',
        read_only=True,
        allow_null=True
    )

    class Meta:
        model = Cliente
        fields = [
            'id',
            'nome',
            'nome_fantasia',
            'cnpj',
            'nome_responsavel',
            'email',
            'telefone',
            'endereco',
            'ativo',
            'created_at',
            'updated_at',
            'created_by',
            'created_by_name',
            'updated_by',
            'updated_by_name',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by', 'updated_by']

    def validate_cnpj(self, value):
        """
        Validação básica de formato CNPJ.
        """
        # Remove caracteres não numéricos
        cnpj_numbers = ''.join(filter(str.isdigit, value))

        if len(cnpj_numbers) != 14:
            raise serializers.ValidationError("CNPJ deve conter 14 dígitos.")

        return value
