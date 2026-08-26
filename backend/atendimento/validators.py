"""
Validador de anexos de atendimento: estende o FileValidator de `chamados`
(PDF/JPEG/PNG/WEBP) para tambem aceitar DOCX/TXT/CSV, sem alterar a classe
base -- `chamados.AnexoChamado` continua usando o FileValidator original,
sem ganhar novos tipos permitidos por efeito colateral.
"""

import os

from django.core.exceptions import ValidationError

from chamados.validators import FileValidator

_TEXT_EXTENSIONS = {".txt", ".csv"}


class AtendimentoFileValidator(FileValidator):
    ALLOWED_MIME_TYPES = FileValidator.ALLOWED_MIME_TYPES | {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
        "text/plain",  # .txt
        "text/csv",  # .csv
    }
    ALLOWED_EXTENSIONS = FileValidator.ALLOWED_EXTENSIONS | {".docx", ".txt", ".csv"}

    def _validate_mime_type(self, file):
        """
        `filetype.guess_mime` nao consegue identificar formatos de texto puro
        (nao ha "magic bytes" para isso) -- para .txt/.csv, validamos que o
        conteudo decodifica como texto em vez de checar assinatura binaria.
        Para os demais tipos (incluindo .docx, detectavel pelo filetype por
        ser um arquivo zip com estrutura OOXML), reaproveita o comportamento
        estrito da classe base.
        """
        ext = os.path.splitext(file.name)[1].lower()
        if ext in _TEXT_EXTENSIONS:
            self._validate_text_content(file)
            return
        super()._validate_mime_type(file)

    def _validate_text_content(self, file):
        file.seek(0)
        amostra = file.read(8192)
        file.seek(0)

        for encoding in ("utf-8", "latin-1"):
            try:
                amostra.decode(encoding)
                return
            except UnicodeDecodeError:
                continue

        raise ValidationError(
            "Nao foi possivel identificar o tipo do arquivo como texto. "
            "O arquivo pode estar corrompido ou nao ser um arquivo de texto valido."
        )
