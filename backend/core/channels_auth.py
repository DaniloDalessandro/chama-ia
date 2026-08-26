"""
JWTAuthMiddleware: resolve `scope["user"]` a partir de um token JWT (SimpleJWT)
passado na query string do WebSocket (`?token=...`).

Gap real do projeto: a stack padrao do Channels (`AuthMiddlewareStack`) e
baseada em cookie de sessao Django, mas este projeto usa SOMENTE JWT Bearer
(`DEFAULT_AUTHENTICATION_CLASSES` em `core/settings.py` nao inclui
`SessionAuthentication`). Ou seja, um atendente autenticado via SPA (sem
cookie de sessao) nunca teria `scope["user"]` populado corretamente pela
stack padrao. Este middleware roda ANTES do `AuthMiddlewareStack` existente
(complementa, nao substitui) e da a mesma prioridade que o resto do projeto
ja da ao JWT.
"""

import logging
from urllib.parse import parse_qs

from channels.db import database_sync_to_async

logger = logging.getLogger(__name__)


@database_sync_to_async
def _resolve_user_from_jwt(token: str):
    from rest_framework_simplejwt.authentication import JWTAuthentication
    from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

    try:
        auth = JWTAuthentication()
        validated_token = auth.get_validated_token(token)
        return auth.get_user(validated_token)
    except (InvalidToken, TokenError):
        return None
    except Exception:  # noqa: BLE001 - token invalido/malformado nunca deve derrubar a conexao
        logger.debug("JWTAuthMiddleware: falha ao validar token JWT (ignorado).", exc_info=True)
        return None


class JWTAuthMiddleware:
    """Middleware ASGI que tenta resolver `scope["user"]` via JWT antes de delegar ao `inner`."""

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode()
        token = parse_qs(query_string).get("token", [None])[0]

        if token:
            user = await _resolve_user_from_jwt(token)
            if user is not None:
                scope = dict(scope)
                scope["user"] = user

        return await self.inner(scope, receive, send)
