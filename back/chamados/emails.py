"""
Sistema de envio de emails para notificações de chamados.
"""
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class EmailService:
    """Serviço centralizado para envio de emails."""

    @staticmethod
    def enviar_confirmacao_chamado(chamado):
        """
        Envia email de confirmação ao cliente após criar chamado.

        Args:
            chamado: Instância do modelo Chamado

        Returns:
            bool: True se enviado com sucesso, False caso contrário
        """
        try:
            assunto = f"Chamado #{chamado.protocolo} - Recebido com Sucesso"

            # Contexto para o template
            contexto = {
                'protocolo': chamado.protocolo,
                'nome': chamado.nome,
                'assunto': chamado.assunto,
                'descricao': chamado.descricao,
                'tipo': chamado.get_tipo_display(),
                'status': chamado.get_status_display(),
                'data_criacao': chamado.created_at,
                'frontend_url': settings.FRONTEND_URL,
            }

            # Renderizar templates
            html_content = render_to_string('emails/chamado_criado.html', contexto)
            text_content = render_to_string('emails/chamado_criado.txt', contexto)

            # Criar email
            email = EmailMultiAlternatives(
                subject=assunto,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[chamado.email]
            )
            email.attach_alternative(html_content, "text/html")

            # Enviar
            email.send()

            logger.info(f"Email de confirmação enviado para {chamado.email} - Protocolo {chamado.protocolo}")
            return True

        except Exception as e:
            logger.error(f"Erro ao enviar email de confirmação: {str(e)}")
            return False

    @staticmethod
    def enviar_atualizacao_status(chamado, status_anterior, usuario=None):
        """
        Envia email ao cliente informando mudança de status.

        Args:
            chamado: Instância do modelo Chamado
            status_anterior: Status anterior do chamado
            usuario: Usuário que alterou o status (opcional)

        Returns:
            bool: True se enviado com sucesso, False caso contrário
        """
        try:
            assunto = f"Chamado #{chamado.protocolo} - Status Atualizado"

            contexto = {
                'protocolo': chamado.protocolo,
                'nome': chamado.nome,
                'assunto_chamado': chamado.assunto,
                'status_anterior': status_anterior,
                'status_novo': chamado.get_status_display(),
                'atendente': usuario.name if usuario else 'Sistema',
                'data_atualizacao': chamado.updated_at,
                'frontend_url': settings.FRONTEND_URL,
            }

            html_content = render_to_string('emails/status_atualizado.html', contexto)
            text_content = render_to_string('emails/status_atualizado.txt', contexto)

            email = EmailMultiAlternatives(
                subject=assunto,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[chamado.email]
            )
            email.attach_alternative(html_content, "text/html")
            email.send()

            logger.info(f"Email de atualização enviado para {chamado.email} - Protocolo {chamado.protocolo}")
            return True

        except Exception as e:
            logger.error(f"Erro ao enviar email de atualização: {str(e)}")
            return False

    @staticmethod
    def enviar_atribuicao_atendente(chamado, atendente):
        """
        Envia email ao atendente informando nova atribuição.

        Args:
            chamado: Instância do modelo Chamado
            atendente: Usuário atendente

        Returns:
            bool: True se enviado com sucesso, False caso contrário
        """
        try:
            assunto = f"Novo Chamado Atribuído - #{chamado.protocolo}"

            contexto = {
                'protocolo': chamado.protocolo,
                'atendente_nome': atendente.name,
                'cliente_nome': chamado.nome,
                'assunto': chamado.assunto,
                'descricao': chamado.descricao,
                'tipo': chamado.get_tipo_display(),
                'prioridade': chamado.get_prioridade_display(),
                'status': chamado.get_status_display(),
                'data_criacao': chamado.created_at,
                'frontend_url': settings.FRONTEND_URL,
            }

            html_content = render_to_string('emails/atendente_atribuido.html', contexto)
            text_content = render_to_string('emails/atendente_atribuido.txt', contexto)

            email = EmailMultiAlternatives(
                subject=assunto,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[atendente.email]
            )
            email.attach_alternative(html_content, "text/html")
            email.send()

            logger.info(f"Email de atribuição enviado para {atendente.email} - Protocolo {chamado.protocolo}")
            return True

        except Exception as e:
            logger.error(f"Erro ao enviar email de atribuição: {str(e)}")
            return False

    @staticmethod
    def enviar_novo_comentario(chamado, comentario):
        """
        Envia email ao cliente informando novo comentário.

        Args:
            chamado: Instância do modelo Chamado
            comentario: Instância do modelo ComentarioChamado

        Returns:
            bool: True se enviado com sucesso, False caso contrário
        """
        try:
            # Não enviar se comentário for interno
            if comentario.tipo == 'interno':
                return True

            assunto = f"Chamado #{chamado.protocolo} - Nova Resposta"

            contexto = {
                'protocolo': chamado.protocolo,
                'nome': chamado.nome,
                'assunto_chamado': chamado.assunto,
                'comentario': comentario.conteudo,
                'autor': comentario.autor.name if comentario.autor else comentario.autor_nome,
                'data_comentario': comentario.created_at,
                'frontend_url': settings.FRONTEND_URL,
            }

            html_content = render_to_string('emails/novo_comentario.html', contexto)
            text_content = render_to_string('emails/novo_comentario.txt', contexto)

            email = EmailMultiAlternatives(
                subject=assunto,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[chamado.email]
            )
            email.attach_alternative(html_content, "text/html")
            email.send()

            logger.info(f"Email de comentário enviado para {chamado.email} - Protocolo {chamado.protocolo}")
            return True

        except Exception as e:
            logger.error(f"Erro ao enviar email de comentário: {str(e)}")
            return False

    @staticmethod
    def enviar_chamado_concluido(chamado, atendente=None):
        """
        Envia email ao cliente informando que o chamado foi concluído.

        Args:
            chamado: Instância do modelo Chamado
            atendente: Usuário que concluiu o chamado (opcional)

        Returns:
            bool: True se enviado com sucesso, False caso contrário
        """
        try:
            assunto = f"Chamado #{chamado.protocolo} - Atendimento Concluído ✅"

            contexto = {
                'protocolo': chamado.protocolo,
                'nome': chamado.nome,
                'assunto_chamado': chamado.assunto,
                'descricao': chamado.descricao,
                'tipo': chamado.get_tipo_display(),
                'status': chamado.get_status_display(),
                'atendente': atendente.name if atendente else 'Nossa equipe',
                'data_criacao': chamado.created_at,
                'data_conclusao': chamado.resolved_at or chamado.updated_at,
                'frontend_url': settings.FRONTEND_URL,
            }

            html_content = render_to_string('emails/chamado_concluido.html', contexto)
            text_content = render_to_string('emails/chamado_concluido.txt', contexto)

            email = EmailMultiAlternatives(
                subject=assunto,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[chamado.email]
            )
            email.attach_alternative(html_content, "text/html")
            email.send()

            logger.info(f"Email de conclusão enviado para {chamado.email} - Protocolo {chamado.protocolo}")
            return True

        except Exception as e:
            logger.error(f"Erro ao enviar email de conclusão: {str(e)}")
            return False
