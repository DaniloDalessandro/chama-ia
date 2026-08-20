"""
Servico de ingestao de chamados via email (IMAP).

Conecta a uma caixa de entrada IMAP, le emails nao lidos,
cria chamados automaticamente e marca os emails como lidos.
"""

import imaplib
import email
import email.header
import email.utils
import logging
import re
import html
from email.policy import default as email_default_policy
from django.conf import settings

logger = logging.getLogger(__name__)


def _get_imap_settings():
    """
    Preferencia: configuracao cadastrada pelo admin na tela de
    Configuracoes (banco de dados). Se nao houver, cai para as
    variaveis de ambiente (.env).
    """
    try:
        from chamados.models import EmailIngestionConfig

        cfg = EmailIngestionConfig.objects.first()
        if cfg:
            return {
                "host": cfg.imap_host,
                "port": int(cfg.imap_port),
                "user": cfg.email,
                "password": cfg.get_password(),
                "folder": cfg.folder,
                "use_ssl": cfg.use_ssl,
                "enabled": cfg.is_active,
                "db_config": cfg,
            }
    except Exception:
        logger.exception("Falha ao carregar EmailIngestionConfig do banco, usando variaveis de ambiente.")

    return {
        "host": getattr(settings, "EMAIL_IMAP_HOST", ""),
        "port": int(getattr(settings, "EMAIL_IMAP_PORT", 993)),
        "user": getattr(settings, "EMAIL_IMAP_USER", settings.EMAIL_HOST_USER),
        "password": getattr(settings, "EMAIL_IMAP_PASSWORD", settings.EMAIL_HOST_PASSWORD),
        "folder": getattr(settings, "EMAIL_IMAP_FOLDER", "INBOX"),
        "use_ssl": getattr(settings, "EMAIL_IMAP_USE_SSL", True),
        "enabled": getattr(settings, "EMAIL_IMAP_ENABLED", False),
        "db_config": None,
    }


def _decode_header_value(value):
    """Decodifica valores de cabeçalho que podem estar em RFC2047."""
    if not value:
        return ""
    parts = email.header.decode_header(value)
    decoded = []
    for part, charset in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(part)
    return "".join(decoded).strip()


def _extract_text_body(msg):
    """Extrai o corpo de texto do email (text/plain preferido, fallback html)."""
    text_plain = []
    text_html = []

    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            cd = str(part.get("Content-Disposition", ""))
            if "attachment" in cd:
                continue
            charset = part.get_content_charset() or "utf-8"
            if ct == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    text_plain.append(payload.decode(charset, errors="replace"))
            elif ct == "text/html":
                payload = part.get_payload(decode=True)
                if payload:
                    text_html.append(payload.decode(charset, errors="replace"))
    else:
        charset = msg.get_content_charset() or "utf-8"
        payload = msg.get_payload(decode=True)
        if payload:
            ct = msg.get_content_type()
            if ct == "text/plain":
                text_plain.append(payload.decode(charset, errors="replace"))
            elif ct == "text/html":
                text_html.append(payload.decode(charset, errors="replace"))

    if text_plain:
        return "\n".join(text_plain).strip()

    if text_html:
        # Remove HTML tags simples
        raw = "\n".join(text_html)
        raw = html.unescape(raw)
        raw = re.sub(r"<br\s*/?>", "\n", raw, flags=re.IGNORECASE)
        raw = re.sub(r"<p[^>]*>", "\n", raw, flags=re.IGNORECASE)
        raw = re.sub(r"<[^>]+>", "", raw)
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        return raw.strip()

    return ""


def _get_attachments(msg):
    """Retorna lista de (filename, content_type, data) para anexos."""
    attachments = []
    if not msg.is_multipart():
        return attachments
    for part in msg.walk():
        cd = str(part.get("Content-Disposition", ""))
        if "attachment" not in cd:
            continue
        filename = part.get_filename()
        if not filename:
            continue
        filename = _decode_header_value(filename)
        data = part.get_payload(decode=True)
        ct = part.get_content_type()
        if data:
            attachments.append((filename, ct, data))
    return attachments


def _parse_sender(from_header):
    """Extrai nome e email do campo From."""
    name, addr = email.utils.parseaddr(from_header or "")
    name = _decode_header_value(name) if name else ""
    addr = addr.strip().lower() if addr else ""
    if not name and addr:
        name = addr.split("@")[0].replace(".", " ").title()
    return name or "Desconhecido", addr


def _criar_chamado_de_email(message_id, assunto, nome, remetente, corpo):
    """Cria um Chamado no banco de dados a partir dos dados do email."""
    from chamados.models import Chamado

    # Verificar duplicata pelo Message-ID
    if message_id and Chamado.objects.filter(email_message_id=message_id).exists():
        logger.info(f"Email ja processado (Message-ID: {message_id}), ignorando.")
        return None

    chamado = Chamado.objects.create(
        nome=nome[:255] if nome else "Desconhecido",
        email=remetente if remetente else "noreply@email.com",
        assunto=assunto[:255] if assunto else "(Sem assunto)",
        descricao=corpo or "(Sem corpo)",
        origem=Chamado.Origem.EMAIL,
        email_message_id=message_id or "",
    )

    logger.info(f"Chamado #{chamado.protocolo} criado a partir do email de {remetente}")
    return chamado


def _salvar_anexos(chamado, attachments):
    """Salva os anexos do email como AnexoChamado."""
    import io
    from django.core.files.base import ContentFile
    from chamados.models import AnexoChamado

    for filename, content_type, data in attachments:
        try:
            arquivo = ContentFile(data, name=filename)
            AnexoChamado.objects.create(
                chamado=chamado,
                arquivo=arquivo,
                nome_original=filename[:255],
            )
            logger.info(f"Anexo '{filename}' salvo para chamado #{chamado.protocolo}")
        except Exception as e:
            logger.warning(f"Falha ao salvar anexo '{filename}': {e}")


def processar_emails():
    """
    Conecta ao IMAP, le emails nao lidos, cria chamados e marca como lidos.
    Retorna dict com estatisticas do processamento.
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

        # Buscar emails nao lidos
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

                chamado = _criar_chamado_de_email(message_id, assunto, nome, remetente, corpo)

                if chamado:
                    if attachments:
                        _salvar_anexos(chamado, attachments)

                    # Disparar classificacao IA em background
                    try:
                        from chamados.tasks import processar_chamado_ia_task
                        processar_chamado_ia_task.delay(chamado.id)
                    except Exception:
                        pass  # IA opcional

                    processados += 1

                # Marcar como lido independente (mesmo se duplicata)
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

    logger.info(f"Ingestao concluida: {processados} chamados criados, {erros} erros")
    return {"enabled": True, "processados": processados, "erros": erros, "erro_msg": erro_msg}
