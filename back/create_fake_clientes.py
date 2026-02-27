#!/usr/bin/env python
"""
Script para criar clientes fake no banco de dados
"""
import os
import django
import sys

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from clientes.models import Cliente

# Lista de clientes fake
clientes_fake = [
    {
        "nome": "Tech Solutions Brasil LTDA",
        "nome_fantasia": "Tech Solutions",
        "cnpj": "12.345.678/0001-90",
        "nome_responsavel": "João Silva Santos",
        "email": "contato@techsolutions.com.br",
        "telefone": "(11) 98765-4321",
        "endereco": "Av. Paulista, 1000 - São Paulo, SP",
        "ativo": True
    },
    {
        "nome": "Inovação Digital Serviços LTDA",
        "nome_fantasia": "Inovação Digital",
        "cnpj": "23.456.789/0001-01",
        "nome_responsavel": "Maria Oliveira Costa",
        "email": "comercial@inovacaodigital.com",
        "telefone": "(21) 97654-3210",
        "endereco": "Rua das Flores, 500 - Rio de Janeiro, RJ",
        "ativo": True
    },
    {
        "nome": "Consultoria Empresarial ABC S.A.",
        "nome_fantasia": "Consultoria ABC",
        "cnpj": "34.567.890/0001-12",
        "nome_responsavel": "Carlos Eduardo Pereira",
        "email": "contato@consultoriaabc.com.br",
        "telefone": "(31) 96543-2109",
        "endereco": "Rua Bahia, 300 - Belo Horizonte, MG",
        "ativo": True
    },
    {
        "nome": "Distribuidora Premium LTDA",
        "nome_fantasia": "Premium Distribuição",
        "cnpj": "45.678.901/0001-23",
        "nome_responsavel": "Ana Paula Rodrigues",
        "email": "vendas@premiumdist.com.br",
        "telefone": "(41) 95432-1098",
        "endereco": "Av. Sete de Setembro, 800 - Curitiba, PR",
        "ativo": True
    },
    {
        "nome": "Sistemas Integrados do Sul S.A.",
        "nome_fantasia": "SI Sul",
        "cnpj": "56.789.012/0001-34",
        "nome_responsavel": "Roberto Machado Lima",
        "email": "sistemas@sisul.com.br",
        "telefone": "(51) 94321-0987",
        "endereco": "Rua dos Andradas, 1500 - Porto Alegre, RS",
        "ativo": True
    },
    {
        "nome": "Comércio e Varejo Nacional LTDA",
        "nome_fantasia": "Varejo Nacional",
        "cnpj": "67.890.123/0001-45",
        "nome_responsavel": "Fernanda Costa Alves",
        "email": "comercial@varejonacional.com",
        "telefone": "(85) 93210-9876",
        "endereco": "Av. Beira Mar, 2000 - Fortaleza, CE",
        "ativo": False
    },
    {
        "nome": "Indústria e Comércio XYZ LTDA",
        "nome_fantasia": "Indústria XYZ",
        "cnpj": "78.901.234/0001-56",
        "nome_responsavel": "Pedro Henrique Santos",
        "email": "contato@industriaxyz.com.br",
        "telefone": "(71) 92109-8765",
        "endereco": "Rodovia BA-001, Km 15 - Salvador, BA",
        "ativo": True
    },
    {
        "nome": "Serviços Profissionais Brasil S.A.",
        "nome_fantasia": "SP Brasil",
        "cnpj": "89.012.345/0001-67",
        "nome_responsavel": "Juliana Martins Souza",
        "email": "atendimento@spbrasil.com",
        "telefone": "(61) 91098-7654",
        "endereco": "SCS Quadra 2, Bloco A - Brasília, DF",
        "ativo": True
    },
    {
        "nome": "Logística Express Transportes LTDA",
        "nome_fantasia": "Express Log",
        "cnpj": "90.123.456/0001-78",
        "nome_responsavel": "Marcos Vinícius Ribeiro",
        "email": "operacoes@expresslog.com.br",
        "telefone": "(81) 90987-6543",
        "endereco": "Av. Agamenon Magalhães, 3000 - Recife, PE",
        "ativo": True
    },
    {
        "nome": "Tecnologia Avançada do Brasil LTDA",
        "nome_fantasia": "Tech Avançada",
        "cnpj": "01.234.567/0001-89",
        "nome_responsavel": "Luciana Ferreira Dias",
        "email": "suporte@techavancada.com",
        "telefone": "(62) 89876-5432",
        "endereco": "Rua T-37, 1200 - Goiânia, GO",
        "ativo": False
    }
]

def criar_clientes():
    print("Criando clientes fake...")
    print("-" * 60)

    for cliente_data in clientes_fake:
        try:
            # Verificar se já existe pelo CNPJ
            if Cliente.objects.filter(cnpj=cliente_data['cnpj']).exists():
                print(f"[SKIP] Cliente {cliente_data['nome_fantasia']} ja existe (CNPJ: {cliente_data['cnpj']})")
                continue

            # Criar cliente
            cliente = Cliente.objects.create(**cliente_data)
            status = "[ATIVO]" if cliente.ativo else "[INATIVO]"
            print(f"{status} | {cliente.nome_fantasia:25} | {cliente.cnpj} | {cliente.nome_responsavel}")

        except Exception as e:
            print(f"[ERRO] Erro ao criar {cliente_data['nome_fantasia']}: {str(e)}")

    print("-" * 60)
    total = Cliente.objects.count()
    ativos = Cliente.objects.filter(ativo=True).count()
    print(f"\nTotal de clientes: {total}")
    print(f"Ativos: {ativos}")
    print(f"Inativos: {total - ativos}")
    print("\nClientes criados com sucesso!")

if __name__ == "__main__":
    criar_clientes()
