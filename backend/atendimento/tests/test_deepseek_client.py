from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from atendimento.ai.deepseek_client import build_chain, build_deepseek_llm


class BuildDeepseekLlmTests(SimpleTestCase):
    @override_settings(DEEPSEEK_API_KEY=None)
    def test_returns_none_when_api_key_not_set(self):
        self.assertIsNone(build_deepseek_llm())

    @override_settings(
        DEEPSEEK_API_KEY="fake-key",
        DEEPSEEK_BASE_URL="https://api.deepseek.com",
        DEEPSEEK_MODEL="deepseek-chat",
        DEEPSEEK_TIMEOUT=60,
        DEEPSEEK_MAX_RETRIES=3,
    )
    @patch("langchain_openai.ChatOpenAI")
    def test_builds_chat_openai_with_deepseek_config(self, mock_chat_openai):
        mock_instance = MagicMock()
        mock_chat_openai.return_value = mock_instance

        resultado = build_deepseek_llm(temperature=0.2, max_tokens=555)

        self.assertIs(resultado, mock_instance)
        mock_chat_openai.assert_called_once_with(
            model="deepseek-chat",
            api_key="fake-key",
            base_url="https://api.deepseek.com",
            timeout=60,
            max_retries=3,
            temperature=0.2,
            max_tokens=555,
        )

    @override_settings(DEEPSEEK_API_KEY="fake-key")
    @patch("langchain_openai.ChatOpenAI", side_effect=RuntimeError("boom"))
    def test_construction_error_degrades_to_none(self, mock_chat_openai):
        self.assertIsNone(build_deepseek_llm())


class BuildChainTests(SimpleTestCase):
    def test_returns_none_when_llm_is_none(self):
        from pydantic import BaseModel

        class DummySchema(BaseModel):
            campo: str

        self.assertIsNone(build_chain(None, prompt=MagicMock(), output_schema=DummySchema))

    def test_composes_prompt_llm_parser(self):
        from pydantic import BaseModel

        class DummySchema(BaseModel):
            campo: str

        prompt = MagicMock()
        llm = MagicMock()
        composed_once = MagicMock()
        composed_twice = MagicMock()
        prompt.__or__ = MagicMock(return_value=composed_once)
        composed_once.__or__ = MagicMock(return_value=composed_twice)

        resultado = build_chain(llm, prompt, DummySchema)

        self.assertIs(resultado, composed_twice)
        prompt.__or__.assert_called_once_with(llm)
