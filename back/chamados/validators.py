"""
Validadores de segurança para uploads de arquivos.
"""
import filetype
from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible


@deconstructible
class FileValidator:
    """
    Validador robusto para uploads de arquivos.

    Verifica:
    - Tamanho do arquivo
    - Tipo MIME real (não apenas extensão)
    - Extensão do arquivo
    """

    # Tamanhos em bytes
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
    MIN_FILE_SIZE = 100  # 100 bytes

    # Tipos MIME permitidos
    ALLOWED_MIME_TYPES = {
        'application/pdf',
        'image/jpeg',
        'image/jpg',
        'image/png',
        'image/webp',
    }

    # Extensões permitidas
    ALLOWED_EXTENSIONS = {
        '.pdf',
        '.jpg',
        '.jpeg',
        '.png',
        '.webp',
    }

    # Extensões perigosas (executáveis)
    DANGEROUS_EXTENSIONS = {
        '.exe', '.bat', '.cmd', '.com', '.pif', '.scr',
        '.vbs', '.js', '.jar', '.zip', '.rar', '.7z',
        '.sh', '.bash', '.py', '.php', '.asp', '.aspx',
    }

    def __init__(self, max_size=None, allowed_types=None):
        """
        Args:
            max_size: Tamanho máximo em bytes (opcional)
            allowed_types: Set de tipos MIME permitidos (opcional)
        """
        if max_size:
            self.MAX_FILE_SIZE = max_size
        if allowed_types:
            self.ALLOWED_MIME_TYPES = allowed_types

    def __call__(self, file):
        """Valida o arquivo."""
        self._validate_size(file)
        self._validate_extension(file.name)
        self._validate_mime_type(file)

    def _validate_size(self, file):
        """Valida o tamanho do arquivo."""
        file_size = file.size

        if file_size > self.MAX_FILE_SIZE:
            max_mb = self.MAX_FILE_SIZE / (1024 * 1024)
            raise ValidationError(
                f'Arquivo muito grande. Tamanho máximo: {max_mb:.1f}MB'
            )

        if file_size < self.MIN_FILE_SIZE:
            raise ValidationError(
                'Arquivo muito pequeno ou corrompido'
            )

    def _validate_extension(self, filename):
        """Valida a extensão do arquivo."""
        import os
        ext = os.path.splitext(filename)[1].lower()

        # Bloquear extensões perigosas
        if ext in self.DANGEROUS_EXTENSIONS:
            raise ValidationError(
                f'Tipo de arquivo não permitido: {ext}. '
                f'Arquivos executáveis não são aceitos.'
            )

        # Verificar se está na lista de permitidos
        if ext not in self.ALLOWED_EXTENSIONS:
            allowed = ', '.join(self.ALLOWED_EXTENSIONS)
            raise ValidationError(
                f'Extensão não permitida: {ext}. '
                f'Use: {allowed}'
            )

    def _validate_mime_type(self, file):
        """
        Valida o tipo MIME real do arquivo (não confia na extensão).

        Usa filetype para ler os bytes do arquivo e determinar
        o tipo real.
        """
        try:
            # Ler os primeiros 2048 bytes para identificar o tipo
            file.seek(0)
            file_head = file.read(2048)
            file.seek(0)

            # Detectar MIME type real
            mime = filetype.guess_mime(file_head)

            # Se não conseguiu detectar, rejeitar por segurança
            if mime is None:
                raise ValidationError(
                    'Não foi possível identificar o tipo do arquivo. '
                    'O arquivo pode estar corrompido ou em formato não suportado.'
                )

            if mime not in self.ALLOWED_MIME_TYPES:
                allowed = ', '.join(self.ALLOWED_MIME_TYPES)
                raise ValidationError(
                    f'Tipo de arquivo não permitido: {mime}. '
                    f'Tipos aceitos: {allowed}'
                )

        except ValidationError:
            # Re-raise ValidationErrors
            raise
        except Exception as e:
            # Se falhar a detecção por outro motivo, rejeitar por segurança
            raise ValidationError(
                'Não foi possível verificar o tipo do arquivo. '
                'O arquivo pode estar corrompido.'
            )


def validate_pdf(file):
    """Validador específico para PDFs."""
    validator = FileValidator(
        max_size=10 * 1024 * 1024,  # 10MB para PDFs
        allowed_types={'application/pdf'}
    )
    validator(file)


def validate_image(file):
    """Validador específico para imagens."""
    validator = FileValidator(
        max_size=5 * 1024 * 1024,  # 5MB para imagens
        allowed_types={'image/jpeg', 'image/jpg', 'image/png', 'image/webp'}
    )
    validator(file)
