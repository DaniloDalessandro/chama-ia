"""
Servico de ingestao de atendimentos via email (IMAP).

Espelha `chamados.services.email_ingestion.processar_emails()` (mesma forma
de retorno, mesma robustez -- nunca levanta excecao), mas cria `Atendimento`
em vez de `Chamado`: o email vira uma mensagem de cliente e atravessa o
mesmo pipeline de 7 agentes/AHP de qualquer atendimento via chat.

Reaproveita os parsers puros de `chamados.services.email_ingestion`
(`_get_imap_settings`, `_decode_header_value`, `_extract_text_body`,
`_get_attachments`, `_parse_sender`) via import direto -- sao funcoes
privadas mas puras/sem estado, e duplica-las arriscaria os dois fluxos
divergirem silenciosamente ao longo do tempo.
"""

import imaplib
import email
import logging

from chamados.services.email_ingestion import (
    _get_imap_settings,
    _decode_header_value,
    _extract_text_body,
    _get_attachments,
    _parse_sender,
)

logger = logging.getLogger(__name__)


def _criar_atendimento_de_email(message_id, assunto, nome, remetente, corpo):
    """Cria um Atendimento + primeira MensagemAtendimento a partir dos dados do email."""
    from atendimento.models import Atendimento, MensagemAtendimento

    if message_id and Atendimento.objects.filter(email_message_id=message_id).exists():
        logger.info(f"Email ja processado como atendimento (Message-ID: {message_id}), ignorando.")
        return None

    atendimento = Atendimento.objects.create(
        nome=nome[:255] if nome else "Desconhecido",
        email=remetente if remetente else "noreply@email.com",
        origem=Atendimento.Origem.EMAIL,
        email_message_id=message_id or "",
    )
    MensagemAtendimento.objects.create(
        atendimento=atendimento,
        remetente_tipo=MensagemAtendimento.RemetenteTipo.CLIENTE,
        conteudo=corpo or "(Sem corpo)",
    )

    logger.info(f"Atendimento #{atendimento.id} criado a partir do email de {remetente}")
    return atendimento


def _salvar_anexos_atendimento(atendimento, attachments):
    """
    Salva os anexos do email como AnexoAtendimento. Ao contrario do
    `_salvar_anexos` legado (chamados), seta `tamanho` (campo obrigatorio,
    sem default) e `mime_type` corretamente -- corrige um gap latente sem
    replica-lo aqui.
    """
    import filetype
    from django.core.files.base import ContentFile
    from atendimento.models import AnexoAtendimento

    for filename, content_type, data in attachments:
        try:
            arquivo = ContentFile(data, name=filename)
            mime_type = filetype.guess_mime(data) or content_type or ""
            AnexoAtendimento.objects.create(
                atendimento=atendimento,
                arquivo=arquivo,
                nome_original=filename[:255],
                tamanho=len(data),
                mime_type=mime_type[:100],
            )
            logger.info(f"Anexo '{filename}' salvo para atendimento #{atendimento.id}")
        except Exception as e:
            logger.warning(f"Falha ao salvar anexo '{filename}': {e}")


def processar_emails_atendimento():
    """
    Conecta ao IMAP, le emails nao lidos, cria atendimentos e marca como lidos.
    Nunca levanta excecao. Retorna dict com estatisticas do processamento,
    na mesma forma de `chamados.services.email_ingestion.processar_emails()`.
    """
    cfg = _get_imap_settings()

    if not cfg["enabled"]:
        logger.debug("Ingestao de email desativada (EMAIL_IMAP_ENABLED=False)")
        return {"enabled": False, "processados": 0, "erros": 0}

    if not cfg["host"]:
        logger.warning("EMAIL_IMAP_HOST nao configurado, ingestao de email ignorada.")
        return {"enabled": False, "processados": 0, "erros": 0}

    processados = 0
    erros = 0
    erro_msg = ""

    try:
        if cfg["use_ssl"]:
            conn = imaplib.IMAP4_SSL(cfg["host"], cfg["port"])
        else:
            conn = imaplib.IMAP4(cfg["host"], cfg["port"])

        conn.login(cfg["user"], cfg["password"])
        conn.select(cfg["folder"])

        status, data = conn.search(None, "UNSEEN")
        if status != "OK":
            logger.error("Falha ao buscar emails UNSEEN")
            conn.logout()
            return {"enabled": True, "processados": 0, "erros": 1}

        uids = data[0].split()
        logger.info(f"Encontrados {len(uids)} emails nao lidos em {cfg['folder']}")

        for uid in uids:
            try:
                status, msg_data = conn.fetch(uid, "(RFC822)")
                if status != "OK":
                    erros += 1
                    continue

                raw = msg_data[0][1]
                msg = email.message_from_bytes(raw)

                message_id = (msg.get("Message-ID") or "").strip()
                assunto = _decode_header_value(msg.get("Subject", ""))
                nome, remetente = _parse_sender(msg.get("From", ""))
                corpo = _extract_text_body(msg)
                attachments = _get_attachments(msg)

                atendimento = _criar_atendimento_de_email(message_id, assunto, nome, remetente, corpo)

                if atendimento:
                    if attachments:
                        _salvar_anexos_atendimento(atendimento, attachments)

                    try:
                        from atendimento.tasks import analisar_atendimento_ia_task
                        analisar_atendimento_ia_task.delay(atendimento.id)
                    except Exception:
                        pass  # IA opcional -- atendimento ja foi criado com sucesso

                    processados += 1

                conn.store(uid, "+FLAGS", "\\Seen")

            except Exception as e:
                logger.error(f"Erro ao processar email UID {uid}: {e}", exc_info=True)
                erros += 1

        conn.logout()

    except imaplib.IMAP4.error as e:
        erro_msg = f"Erro de autenticacao/conexao IMAP: {e}"
        logger.error(erro_msg)
        erros += 1
    except Exception as e:
        erro_msg = f"Erro inesperado na ingestao de email: {e}"
        logger.error(erro_msg, exc_info=True)
        erros += 1

    if cfg.get("db_config"):
        try:
            cfg["db_config"].registrar_verificacao(processados, erro=erro_msg)
        except Exception:
            logger.exception("Falha ao registrar estatisticas da verificacao de email.")

    logger.info(f"Ingestao concluida: {processados} atendimentos criados, {erros} erros")
    return {"enabled": True, "processados": processados, "erros": erros, "erro_msg": erro_msg}
