"""
Wrapper do serviço de emails para integração com as tasks.
"""
from chamados.emails import EmailService


def enviar_email_confirmacao_chamado(chamado):
    """Envia email de confirmação para o cliente."""
    return EmailService.enviar_confirmacao_chamado(chamado)


def enviar_email_atualizacao_status(chamado, status_anterior, usuario=None):
    """Envia email de atualização de status."""
    return EmailService.enviar_atualizacao_status(chamado, status_anterior, usuario)


def enviar_email_atribuicao(chamado, atendente):
    """Envia email de atribuição para o atendente."""
    return EmailService.enviar_atribuicao_atendente(chamado, atendente)


def enviar_email_novo_comentario(chamado, comentario):
    """Envia email de novo comentário."""
    return EmailService.enviar_novo_comentario(chamado, comentario)


def enviar_email_chamado_concluido(chamado, atendente=None):
    """Envia email de chamado concluído."""
    return EmailService.enviar_chamado_concluido(chamado, atendente)
