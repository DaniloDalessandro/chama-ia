"""
OCRService: wrapper deterministico (zero LLM) sobre o binario Tesseract OCR
via pytesseract, usado pelo Agente 2 (Analise Visual) quando o modelo de IA
configurado nao tem visao (caso deste projeto -- DEEPSEEK_MODEL e texto).

Degrada graciosamente: se o binario Tesseract nao estiver instalado, ou
qualquer outro erro ocorrer, registra a limitacao em vez de derrubar a
analise do atendimento -- espelha o mesmo idioma de `IAClassifierService`
quando a chave de API nao esta configurada.
"""

import logging

logger = logging.getLogger(__name__)

_IDIOMAS = "por+eng"
_LARGURA_MINIMA_UPSCALE = 1000


class OCRService:
    @staticmethod
    def extract_text(imagem_bytes: bytes) -> dict:
        """
        Retorna {"disponivel": bool, "texto": str, "confianca": float | None, "motivo": str | None}.
        `confianca` e a media das confiancas por palavra (0.0-1.0), quando disponivel.
        """
        try:
            import pytesseract
            from PIL import Image
        except ImportError as exc:
            return {"disponivel": False, "texto": "", "confianca": None, "motivo": f"pytesseract/Pillow nao instalado: {exc}"}

        try:
            import io

            imagem = Image.open(io.BytesIO(imagem_bytes))
            imagem = OCRService._preprocessar(imagem)

            dados = pytesseract.image_to_data(imagem, lang=_IDIOMAS, output_type=pytesseract.Output.DICT)
            texto = " ".join(palavra for palavra in dados.get("text", []) if palavra.strip())
            confiancas = [c for c in dados.get("conf", []) if isinstance(c, (int, float)) and c >= 0]
            confianca = (sum(confiancas) / len(confiancas) / 100.0) if confiancas else None

            return {"disponivel": True, "texto": texto, "confianca": confianca, "motivo": None}
        except pytesseract.pytesseract.TesseractNotFoundError as exc:
            logger.warning("Tesseract OCR nao encontrado no ambiente: %s", exc)
            return {"disponivel": False, "texto": "", "confianca": None, "motivo": f"Binario Tesseract nao encontrado: {exc}"}
        except Exception as exc:  # noqa: BLE001 - falha de OCR nunca deve derrubar a analise
            logger.error("Erro ao processar OCR: %s", exc)
            return {"disponivel": False, "texto": "", "confianca": None, "motivo": str(exc)}

    @staticmethod
    def _preprocessar(imagem):
        from PIL import Image as PILImage

        imagem = imagem.convert("L")  # grayscale -- melhora contraste para OCR

        if imagem.width < _LARGURA_MINIMA_UPSCALE:
            fator = _LARGURA_MINIMA_UPSCALE / imagem.width
            nova_dimensao = (int(imagem.width * fator), int(imagem.height * fator))
            imagem = imagem.resize(nova_dimensao, PILImage.LANCZOS)

        return imagem
