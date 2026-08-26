"""
ChatSecurityService: primeira linha de defesa contra prompt injection.

Todo conteudo vindo do cliente (mensagem, historico, anexos, OCR) e tratado
como NAO CONFIAVEL. Este servico NUNCA bloqueia nem descarta uma mensagem --
"nenhuma mensagem pode ser perdida" e "deve existir possibilidade de
reprocessamento" argumentam contra qualquer hard-abort aqui.

A defesa REAL e estrutural: `wrap()` envolve todo texto de cliente em uma
tag delimitadora fixa, usada em TODOS os prompts dos agentes 1-5, com uma
instrucao de sistema explicita de que conteudo dentro da tag e DADO, nunca
COMANDO. A deteccao por regex em `detectar_padroes`/`analisar` e apenas
informativa (auditoria/testes) -- nunca usada para alterar pesos do AHP,
prioridade ou qualquer decisao de negocio.
"""

import re

DELIMITER_TAG = "mensagem_cliente"

_INJECTION_PATTERNS = [
    ("ignorar_instrucoes", re.compile(r"ignor[ea]\s+(as\s+|suas\s+)?(regras|instru[cç][oõ]es)", re.IGNORECASE)),
    ("esquecer_contexto", re.compile(r"esque[cç]a\s+(o\s+que\s+(eu\s+)?disse|as\s+regras)", re.IGNORECASE)),
    ("assumir_persona", re.compile(r"\b(aja|atue)\s+como\b", re.IGNORECASE)),
    ("voce_agora_e", re.compile(r"voc[eê]\s+(agora\s+)?[eé]\s+(um|uma|o|a)\b", re.IGNORECASE)),
    ("revelar_prompt", re.compile(r"system\s*prompt|prompt\s+(interno|do\s+sistema)", re.IGNORECASE)),
    ("forcar_classificacao", re.compile(r"classifiqu[ei]\s+(meu\s+|este\s+)?atendimento\s+como\s+p[1-4]", re.IGNORECASE)),
    ("alterar_pesos", re.compile(r"altere?\s+os?\s+pesos?", re.IGNORECASE)),
    ("executar_comando", re.compile(r"execut[ea]\s+(este|esse|o)\s+comando", re.IGNORECASE)),
]


class ChatSecurityService:
    @staticmethod
    def detectar_padroes(texto: str) -> list:
        if not texto:
            return []
        flags = []
        for nome, padrao in _INJECTION_PATTERNS:
            match = padrao.search(texto)
            if match:
                flags.append({"padrao_detectado": nome, "trecho": match.group(0)})
        return flags

    @staticmethod
    def analisar(atendimento) -> dict:
        """Roda a deteccao (informativa) sobre todo o historico do atendimento."""
        from .conversation_extraction_service import ConversationExtractionService

        historico = ConversationExtractionService.get_historico_ordenado(atendimento)
        flags_por_mensagem = []
        for mensagem in historico:
            flags = ChatSecurityService.detectar_padroes(mensagem["conteudo"])
            if flags:
                flags_por_mensagem.append({"mensagem_id": mensagem["mensagem_id"], "flags": flags})

        return {"flags_injecao": flags_por_mensagem, "delimitador_tag": DELIMITER_TAG}

    @staticmethod
    def wrap(texto: str, tag: str = DELIMITER_TAG) -> str:
        """
        Envolve `texto` em uma tag delimitadora fixa para uso em prompts.
        Remove ocorrencias literais da tag de fechamento no proprio texto,
        prevenindo que o conteudo do cliente "escape" do delimitador.
        """
        texto = texto or ""
        texto_seguro = texto.replace(f"</{tag}>", "").replace(f"<{tag}>", "")
        return f"<{tag}>{texto_seguro}</{tag}>"
