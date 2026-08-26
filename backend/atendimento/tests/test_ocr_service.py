import io
from unittest.mock import patch

from django.test import SimpleTestCase
from PIL import Image
from pytesseract.pytesseract import TesseractNotFoundError

from atendimento.services.ocr_service import OCRService


def _imagem_png_bytes(width=50, height=50):
    imagem = Image.new("RGB", (width, height), color=(255, 255, 255))
    buffer = io.BytesIO()
    imagem.save(buffer, format="PNG")
    return buffer.getvalue()


class OCRServiceTests(SimpleTestCase):
    @patch("pytesseract.image_to_data")
    def test_extracts_text_and_confidence_from_mocked_ocr(self, mock_image_to_data):
        mock_image_to_data.return_value = {
            "text": ["ERR_500", "", "Servidor", "indisponivel"],
            "conf": [95, -1, 88, 91],
        }

        resultado = OCRService.extract_text(_imagem_png_bytes())

        self.assertTrue(resultado["disponivel"])
        self.assertEqual(resultado["texto"], "ERR_500 Servidor indisponivel")
        self.assertAlmostEqual(resultado["confianca"], (95 + 88 + 91) / 3 / 100.0, places=4)
        self.assertIsNone(resultado["motivo"])

    @patch("pytesseract.image_to_data")
    def test_tesseract_not_found_degrades_gracefully(self, mock_image_to_data):
        mock_image_to_data.side_effect = TesseractNotFoundError()

        resultado = OCRService.extract_text(_imagem_png_bytes())

        self.assertFalse(resultado["disponivel"])
        self.assertEqual(resultado["texto"], "")
        self.assertIsNone(resultado["confianca"])
        self.assertIn("Tesseract", resultado["motivo"])

    @patch("pytesseract.image_to_data")
    def test_generic_exception_degrades_gracefully(self, mock_image_to_data):
        mock_image_to_data.side_effect = RuntimeError("falha inesperada qualquer")

        resultado = OCRService.extract_text(_imagem_png_bytes())

        self.assertFalse(resultado["disponivel"])
        self.assertEqual(resultado["motivo"], "falha inesperada qualquer")

    def test_invalid_image_bytes_never_raises(self):
        resultado = OCRService.extract_text(b"isso nao e uma imagem valida")
        self.assertFalse(resultado["disponivel"])
        self.assertIsNotNone(resultado["motivo"])

    @patch("pytesseract.image_to_data")
    def test_small_image_is_upscaled_before_ocr(self, mock_image_to_data):
        capturada = {}

        def _fake_image_to_data(imagem, lang=None, output_type=None):
            capturada["width"] = imagem.width
            return {"text": [], "conf": []}

        mock_image_to_data.side_effect = _fake_image_to_data

        OCRService.extract_text(_imagem_png_bytes(width=50, height=50))

        self.assertGreaterEqual(capturada["width"], 1000)

    @patch("pytesseract.image_to_data")
    def test_no_words_detected_confidence_is_none(self, mock_image_to_data):
        mock_image_to_data.return_value = {"text": ["", " "], "conf": [-1, -1]}

        resultado = OCRService.extract_text(_imagem_png_bytes())

        self.assertTrue(resultado["disponivel"])
        self.assertEqual(resultado["texto"], "")
        self.assertIsNone(resultado["confianca"])
