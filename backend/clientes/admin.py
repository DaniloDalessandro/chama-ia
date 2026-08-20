from django.contrib import admin
from .models import Cliente


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    """
    Configuração do admin para Cliente.
    """
    list_display = [
        'nome',
        'nome_fantasia',
        'cnpj',
        'nome_responsavel',
        'ativo',
        'created_at'
    ]
    list_filter = ['ativo', 'created_at']
    search_fields = ['nome', 'nome_fantasia', 'cnpj', 'email', 'nome_responsavel']
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']

    fieldsets = (
        ('Informações Principais', {
            'fields': ('nome', 'nome_fantasia', 'cnpj', 'nome_responsavel')
        }),
        ('Contato', {
            'fields': ('email', 'telefone', 'endereco')
        }),
        ('Status', {
            'fields': ('ativo',)
        }),
        ('Auditoria', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
