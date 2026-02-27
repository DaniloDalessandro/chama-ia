"""
Serviço para gerenciamento de recuperação de senha.
Responsável por criar, validar e processar tokens de reset de senha.
"""

import logging
from typing import Optional, Dict, Any
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from accounts.models import CustomUser, PasswordResetToken

logger = logging.getLogger(__name__)


class PasswordResetService:
    """Serviço centralizado para recuperação de senha."""

    @staticmethod
    def request_password_reset(email: str, ip_address: Optional[str] = None) -> Dict[str, Any]:
        """
        Solicita recuperação de senha para um e-mail.

        IMPORTANTE: Por segurança, sempre retorna sucesso mesmo se o e-mail não existir.
        Isso evita vazamento de informação sobre usuários cadastrados.

        Args:
            email: E-mail do usuário
            ip_address: IP da requisição (para log de auditoria)

        Returns:
            Dict com success=True sempre (para não vazar se o usuário existe)
        """
        try:
            # Tentar buscar usuário
            try:
                user = CustomUser.objects.get(email=email, is_active=True)
            except CustomUser.DoesNotExist:
                # IMPORTANTE: Não revelar que o usuário não existe
                logger.warning(
                    f"Tentativa de reset de senha para e-mail não cadastrado: {email} (IP: {ip_address})"
                )
                # Retornar sucesso mesmo assim (segurança)
                return {
                    "success": True,
                    "message": "Se o e-mail estiver cadastrado, você receberá instruções para redefinir sua senha."
                }

            # Criar token de reset
            reset_token = PasswordResetToken.create_for_user(
                user=user,
                ip_address=ip_address,
                validity_hours=1  # Token válido por 1 hora
            )

            # Enviar e-mail
            success = PasswordResetService._send_reset_email(user, reset_token.token)

            if success:
                logger.info(
                    f"Token de reset criado para {user.email} (IP: {ip_address}). "
                    f"Token expira em 1 hora."
                )
            else:
                logger.error(f"Falha ao enviar e-mail de reset para {user.email}")

            # Sempre retornar sucesso (não vazar informação)
            return {
                "success": True,
                "message": "Se o e-mail estiver cadastrado, você receberá instruções para redefinir sua senha."
            }

        except Exception as e:
            logger.error(f"Erro ao processar reset de senha para {email}: {e}")
            # Mesmo em erro, retornar sucesso genérico
            return {
                "success": True,
                "message": "Se o e-mail estiver cadastrado, você receberá instruções para redefinir sua senha."
            }

    @staticmethod
    def validate_token(token: str) -> Dict[str, Any]:
        """
        Valida se um token de reset é válido.

        Args:
            token: Token de reset

        Returns:
            Dict com success e message
        """
        try:
            reset_token = PasswordResetToken.objects.get(token=token)

            if reset_token.is_valid():
                return {
                    "success": True,
                    "message": "Token válido",
                    "user_email": reset_token.user.email
                }
            elif reset_token.is_used:
                return {
                    "success": False,
                    "message": "Este link já foi utilizado. Solicite um novo link de recuperação."
                }
            else:
                return {
                    "success": False,
                    "message": "Este link expirou. Solicite um novo link de recuperação."
                }

        except PasswordResetToken.DoesNotExist:
            return {
                "success": False,
                "message": "Link inválido. Verifique se você copiou o link corretamente."
            }

    @staticmethod
    def reset_password(token: str, new_password: str) -> Dict[str, Any]:
        """
        Redefine a senha do usuário usando o token.

        Args:
            token: Token de reset válido
            new_password: Nova senha

        Returns:
            Dict com success e message
        """
        try:
            reset_token = PasswordResetToken.objects.get(token=token)

            # Validar token
            if not reset_token.is_valid():
                if reset_token.is_used:
                    return {
                        "success": False,
                        "message": "Este link já foi utilizado."
                    }
                else:
                    return {
                        "success": False,
                        "message": "Este link expirou."
                    }

            # Redefinir senha
            user = reset_token.user
            user.set_password(new_password)
            user.save(update_fields=["password"])

            # Marcar token como usado
            reset_token.mark_as_used()

            logger.info(f"Senha redefinida com sucesso para {user.email}")

            return {
                "success": True,
                "message": "Senha redefinida com sucesso! Você já pode fazer login."
            }

        except PasswordResetToken.DoesNotExist:
            return {
                "success": False,
                "message": "Link inválido."
            }
        except Exception as e:
            logger.error(f"Erro ao redefinir senha: {e}")
            return {
                "success": False,
                "message": "Erro ao redefinir senha. Tente novamente."
            }

    @staticmethod
    def _send_reset_email(user: CustomUser, token: str) -> bool:
        """
        Envia e-mail de recuperação de senha.

        Args:
            user: Usuário
            token: Token de reset

        Returns:
            bool: True se enviado com sucesso
        """
        try:
            # URL do frontend para reset de senha
            reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"

            # Renderizar template HTML
            html_message = render_to_string(
                "emails/password_reset.html",
                {
                    "user": user,
                    "reset_url": reset_url,
                    "validity_hours": 1,
                }
            )

            # Versão texto plano
            plain_message = strip_tags(html_message)

            # Enviar e-mail
            send_mail(
                subject="Recuperação de Senha - Chama IA",
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )

            return True

        except Exception as e:
            logger.error(f"Erro ao enviar e-mail de reset para {user.email}: {e}")
            return False

    @staticmethod
    def cleanup_expired_tokens():
        """
        Remove tokens expirados do banco de dados.
        Pode ser executado periodicamente via cron/celery beat.

        Returns:
            int: Quantidade de tokens removidos
        """
        from django.utils import timezone

        count = PasswordResetToken.objects.filter(
            expires_at__lt=timezone.now()
        ).delete()[0]

        logger.info(f"Removidos {count} tokens expirados")
        return count
