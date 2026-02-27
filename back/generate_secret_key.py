#!/usr/bin/env python
"""
Script para gerar uma SECRET_KEY segura para Django.
Uso: python generate_secret_key.py
"""
from django.core.management.utils import get_random_secret_key

if __name__ == "__main__":
    secret_key = get_random_secret_key()
    print("=" * 70)
    print("🔐 NOVA SECRET_KEY GERADA:")
    print("=" * 70)
    print(secret_key)
    print("=" * 70)
    print("\n📝 INSTRUÇÕES:")
    print("1. Copie a chave acima")
    print("2. Adicione no arquivo .env:")
    print(f"   SECRET_KEY={secret_key}")
    print("\n⚠️  NUNCA commite esta chave no git!")
    print("=" * 70)
