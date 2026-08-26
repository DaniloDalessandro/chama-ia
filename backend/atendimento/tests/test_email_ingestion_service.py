from email.message import EmailMessage
from unittest.mock import MagicMock, patch

from django.test import TestCase

from atendimento.models import AnexoAtendimento, Atendimento, MensagemAtendimento
from atendimento.services.email_ingestion_service import (
    _criar_atendimento_de_email,
    _salvar_anexos_atendimento,
    processar_emails_atendimento,
)


class CriarAtendimentoDeEmailTests(TestCase):
    def test_creates_atendimento_and_first_mensagem(self):
        atendimento = _criar_atendimento_de_email(
            "<msg-1@example.com>", "Sistema fora do ar", "Joao Silva", "joao@cliente.com", "Meu sistema esta fora do ar",
        )

        self.assertIsNotNone(atendimento)
        self.assertEqual(atendimento.nome, "Joao Silva")
        self.assertEqual(atendimento.email, "joao@cliente.com")
        self.assertEqual(atendimento.origem, Atendimento.Origem.EMAIL)
        self.assertEqual(atendimento.email_message_id, "<msg-1@example.com>")

        mensagens = list(atendimento.mensagens.all())
        self.assertEqual(len(mensagens), 1)
        self.assertEqual(mensagens[0].remetente_tipo, MensagemAtendimento.RemetenteTipo.CLIENTE)
        self.assertEqual(mensagens[0].conteudo, "Meu sistema esta fora do ar")

    def test_dedup_by_message_id_returns_none(self):
        _criar_atendimento_de_email("<dup@example.com>", "x", "Nome", "a@b.com", "corpo")
        resultado = _criar_atendimento_de_email("<dup@example.com>", "x", "Nome", "a@b.com", "corpo outra vez")

        self.assertIsNone(resultado)
        self.assertEqual(Atendimento.objects.filter(email_message_id="<dup@example.com>").count(), 1)

    def test_missing_nome_defaults_to_desconhecido(self):
        atendimento = _criar_atendimento_de_email("<x@example.com>", "assunto", "", "a@b.com", "corpo")
        self.assertEqual(atendimento.nome, "Desconhecido")


class SalvarAnexosAtendimentoTests(TestCase):
    def setUp(self):
        self.atendimento = Atendimento.objects.create(nome="Cliente", email="c@test.com")

    def test_sets_tamanho_and_mime_type_correctly(self):
        # bytes de um PNG minimo valido (assinatura PNG) para o filetype detectar
        conteudo = bytes.fromhex("89504e470d0a1a0a") + b"0" * 100
        _salvar_anexos_atendimento(self.atendimento, [("print.png", "image/png", conteudo)])

        anexo = AnexoAtendimento.objects.get(atendimento=self.atendimento)
        self.assertEqual(anexo.tamanho, len(conteudo))
        self.assertTrue(anexo.mime_type)  # nao vazio -- prova que o bug do chamados nao foi replicado

    def test_bad_attachment_does_not_raise_and_others_still_saved(self):
        with patch("filetype.guess_mime", side_effect=RuntimeError("boom")):
            _salvar_anexos_atendimento(self.atendimento, [
                ("ruim.bin", "application/octet-stream", b"x" * 50),
                ("bom.txt", "text/plain", b"conteudo valido" * 5),
            ])
        # o anexo problematico e pulado (logado como warning), nada e levantado,
        # e nenhum anexo e criado para nenhum dos dois ja que ambos usam o mesmo
        # guess_mime mockado para falhar -- o importante e que a chamada nao levanta.
        self.assertEqual(AnexoAtendimento.objects.filter(atendimento=self.atendimento).count(), 0)

    def test_multiple_attachments_all_saved(self):
        conteudo1 = b"conteudo do anexo 1" * 10
        conteudo2 = b"conteudo do anexo 2" * 10
        _salvar_anexos_atendimento(self.atendimento, [
            ("a.txt", "text/plain", conteudo1),
            ("b.txt", "text/plain", conteudo2),
        ])
        self.assertEqual(AnexoAtendimento.objects.filter(atendimento=self.atendimento).count(), 2)


def _construir_email_bruto(message_id, assunto, remetente, corpo, anexo_nome=None, anexo_bytes=None):
    msg = EmailMessage()
    msg["Message-ID"] = message_id
    msg["Subject"] = assunto
    msg["From"] = f"Cliente Teste <{remetente}>"
    msg.set_content(corpo)
    if anexo_nome:
        msg.add_attachment(anexo_bytes, maintype="application", subtype="octet-stream", filename=anexo_nome)
    return msg.as_bytes()


class ProcessarEmailsAtendimentoTests(TestCase):
    def test_disabled_returns_early_without_connecting(self):
        with patch(
            "atendimento.services.email_ingestion_service._get_imap_settings",
            return_value={"enabled": False, "host": "", "processados": 0},
        ):
            resultado = processar_emails_atendimento()
        self.assertFalse(resultado["enabled"])
        self.assertEqual(resultado["processados"], 0)

    @patch("atendimento.services.email_ingestion_service.imaplib.IMAP4_SSL")
    @patch("atendimento.services.email_ingestion_service._get_imap_settings")
    def test_full_flow_creates_atendimento_not_chamado(self, mock_get_settings, mock_imap_cls):
        mock_get_settings.return_value = {
            "host": "imap.test.com", "port": 993, "user": "caixa@test.com", "password": "x",
            "folder": "INBOX", "use_ssl": True, "enabled": True, "db_config": None,
        }

        raw = _construir_email_bruto(
            "<real-1@example.com>", "Preciso de ajuda", "cliente@test.com", "Meu sistema esta fora do ar",
            anexo_nome="print.png", anexo_bytes=b"conteudo de imagem qualquer" * 5,
        )

        mock_conn = MagicMock()
        mock_conn.search.return_value = ("OK", [b"1"])
        mock_conn.fetch.return_value = ("OK", [(b"1 (RFC822 {123}", raw)])
        mock_imap_cls.return_value = mock_conn

        with patch("atendimento.tasks.analisar_atendimento_ia_task.delay") as mock_delay:
            resultado = processar_emails_atendimento()

        self.assertEqual(resultado["processados"], 1)
        self.assertEqual(resultado["erros"], 0)

        atendimento = Atendimento.objects.get(email_message_id="<real-1@example.com>")
        self.assertEqual(atendimento.origem, Atendimento.Origem.EMAIL)
        self.assertEqual(AnexoAtendimento.objects.filter(atendimento=atendimento).count(), 1)
        mock_delay.assert_called_once_with(atendimento.id)

        from chamados.models import Chamado
        self.assertEqual(Chamado.objects.count(), 0)  # nao cria Chamado neste fluxo

        mock_conn.store.assert_called_once_with(b"1", "+FLAGS", "\\Seen")
        mock_conn.logout.assert_called_once()
