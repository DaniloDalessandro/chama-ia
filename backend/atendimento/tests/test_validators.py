from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase

from atendimento.validators import AtendimentoFileValidator


def _make_file(name, content: bytes, min_size=100):
    if len(content) < min_size:
        content = content + b" " * (min_size - len(content))
    return SimpleUploadedFile(name, content)


class AtendimentoFileValidatorTests(SimpleTestCase):
    def setUp(self):
        self.validator = AtendimentoFileValidator()

    def test_accepts_valid_utf8_txt(self):
        arquivo = _make_file("notas.txt", "Conteudo de texto valido em UTF-8 ç ã é".encode("utf-8"))
        self.validator(arquivo)  # nao deve levantar

    def test_accepts_latin1_txt(self):
        arquivo = _make_file("notas.txt", "texto em latin-1: caf\xe9".encode("latin-1"))
        self.validator(arquivo)

    def test_accepts_valid_csv(self):
        arquivo = _make_file("dados.csv", b"coluna1,coluna2\nvalor1,valor2\n")
        self.validator(arquivo)

    def test_rejects_dangerous_extension_even_with_txt_like_content(self):
        arquivo = _make_file("malicioso.exe", b"conteudo qualquer" * 10)
        with self.assertRaises(ValidationError):
            self.validator(arquivo)

    def test_rejects_extension_not_allowed(self):
        arquivo = _make_file("planilha.xlsx", b"conteudo qualquer" * 10)
        with self.assertRaises(ValidationError):
            self.validator(arquivo)

    def test_docx_extension_is_allowed_list(self):
        self.assertIn(".docx", AtendimentoFileValidator.ALLOWED_EXTENSIONS)
        self.assertIn("text/csv", AtendimentoFileValidator.ALLOWED_MIME_TYPES)

    def test_base_pdf_image_types_still_allowed(self):
        self.assertIn(".pdf", AtendimentoFileValidator.ALLOWED_EXTENSIONS)
        self.assertIn(".png", AtendimentoFileValidator.ALLOWED_EXTENSIONS)

    def test_too_small_file_rejected(self):
        arquivo = SimpleUploadedFile("pequeno.txt", b"oi")
        with self.assertRaises(ValidationError):
            self.validator(arquivo)
