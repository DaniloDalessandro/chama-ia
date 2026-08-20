"""
Decoradores de cache customizados para otimização de performance.
Usa Redis quando disponível, fallback para cache em memória.
"""

from functools import wraps
from django.core.cache import cache
from django.conf import settings
import hashlib
import json


def cache_response(timeout=300, key_prefix='view', vary_on=None):
    """
    Decorator para cachear respostas de views/actions.

    Args:
        timeout (int): Tempo em segundos (padrão: 5 minutos)
        key_prefix (str): Prefixo da chave de cache
        vary_on (list): Lista de parâmetros que invalidam o cache

    Exemplo:
        @cache_response(timeout=600, key_prefix='stats', vary_on=['user_id'])
        def stats(self, request):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extrair request do args (pode ser self, request ou apenas request)
            request = None
            for arg in args:
                if hasattr(arg, 'user') and hasattr(arg, 'META'):
                    request = arg
                    break

            if not request:
                # Se não encontrou request, executa sem cache
                return func(*args, **kwargs)

            # Construir chave de cache
            cache_key_parts = [key_prefix, func.__name__]

            # Adicionar user_id se estiver autenticado
            if request.user.is_authenticated:
                cache_key_parts.append(f'user_{request.user.id}')

            # Adicionar parâmetros variáveis
            if vary_on:
                for param in vary_on:
                    value = request.query_params.get(param) or request.GET.get(param)
                    if value:
                        cache_key_parts.append(f'{param}_{value}')

            # Hash dos query params para garantir unicidade
            query_hash = hashlib.md5(
                json.dumps(dict(request.query_params), sort_keys=True).encode()
            ).hexdigest()[:8]
            cache_key_parts.append(query_hash)

            cache_key = ':'.join(cache_key_parts)

            # Tentar buscar do cache
            cached_response = cache.get(cache_key)
            if cached_response is not None:
                return cached_response

            # Executar função e cachear resultado
            response = func(*args, **kwargs)
            cache.set(cache_key, response, timeout)

            return response

        return wrapper
    return decorator


def invalidate_cache(key_prefix, user_id=None):
    """
    Invalida cache baseado em prefixo.

    Args:
        key_prefix (str): Prefixo das chaves a invalidar
        user_id (int): ID do usuário (opcional)

    Exemplo:
        invalidate_cache('stats', user_id=request.user.id)
    """
    # Redis permite delete_pattern, mas cache genérico não
    # Por isso, usamos chaves específicas
    pattern = f'{key_prefix}:*'
    if user_id:
        pattern = f'{key_prefix}:*user_{user_id}*'

    # No Redis, podemos fazer pattern matching
    try:
        from django_redis import get_redis_connection
        redis_conn = get_redis_connection("default")
        keys = redis_conn.keys(pattern)
        if keys:
            redis_conn.delete(*keys)
    except Exception:
        # Fallback: invalidar cache genérico (não suporta pattern)
        pass


def cache_queryset(timeout=300, key_func=None):
    """
    Decorator para cachear resultados de querysets.

    Args:
        timeout (int): Tempo em segundos
        key_func (callable): Função para gerar chave customizada

    Exemplo:
        @cache_queryset(timeout=600, key_func=lambda: f'clientes_ativos')
        def get_clientes_ativos():
            return Cliente.objects.filter(ativo=True)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Gerar chave de cache
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f'queryset:{func.__name__}'

            # Buscar do cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            # Executar query e cachear
            result = func(*args, **kwargs)

            # Converter queryset para lista para serialização
            if hasattr(result, '__iter__') and hasattr(result, 'model'):
                result = list(result)

            cache.set(cache_key, result, timeout)
            return result

        return wrapper
    return decorator
