"""
ConversationExtractionService: preparo deterministico (zero LLM) da conversa
de um atendimento antes de qualquer agente de IA le-la -- ordenacao
cronologica, deduplicacao de repeticoes consecutivas, separacao por
remetente e marcacao de mensagens automaticas irrelevantes.

Nada aqui interpreta o CONTEUDO semantico da conversa (isso e trabalho do
Agente 1) -- e puramente estrutural/deterministico.
"""

import hashlib
import re

_SISTEMA_MENSAGENS_IGNORADAS_PATTERNS = [
    re.compile(r"^atendimento iniciado", re.IGNORECASE),
    re.compile(r"^conectando ao chat", re.IGNORECASE),
    re.compile(r"^aguardando atendente", re.IGNORECASE),
    re.compile(r"^sess[aã]o (iniciada|encerrada)", re.IGNORECASE),
]


def _normalizar(texto: str) -> str:
    return " ".join(texto.strip().lower().split())


def _hash_mensagem(remetente_tipo: str, conteudo: str) -> str:
    chave = f"{remetente_tipo}:{_normalizar(conteudo)}"
    return hashlib.sha256(chave.encode("utf-8")).hexdigest()


class ConversationExtractionService:
    @staticmethod
    def get_historico_ordenado(atendimento) -> list:
        """
        Retorna a lista de mensagens do atendimento, ordenada cronologicamente,
        com deduplicacao de repeticoes consecutivas identicas e marcacao de
        mensagens de sistema irrelevantes. NENHUMA linha e descartada da lista
        retornada -- duplicatas/irrelevantes ficam marcadas, nao removidas.
        """
        mensagens = list(atendimento.mensagens.all().order_by("criado_em", "id"))

        resultado = []
        hash_anterior = None
        for mensagem in mensagens:
            hash_atual = _hash_mensagem(mensagem.remetente_tipo, mensagem.conteudo)
            duplicada = hash_atual == hash_anterior
            hash_anterior = hash_atual

            ignorada, motivo_ignorada = ConversationExtractionService._checar_irrelevante(mensagem)

            resultado.append({
                "mensagem_id": mensagem.id,
                "remetente_tipo": mensagem.remetente_tipo,
                "conteudo": mensagem.conteudo,
                "criado_em": mensagem.criado_em.isoformat(),
                "duplicada": duplicada,
                "ignorada": ignorada or duplicada,
                "motivo_ignorada": motivo_ignorada or ("repeticao consecutiva identica" if duplicada else None),
            })

        return resultado

    @staticmethod
    def _checar_irrelevante(mensagem) -> tuple:
        if mensagem.remetente_tipo != mensagem.RemetenteTipo.SISTEMA:
            return False, None

        for padrao in _SISTEMA_MENSAGENS_IGNORADAS_PATTERNS:
            if padrao.search(mensagem.conteudo.strip()):
                return True, "mensagem automatica de sistema sem relevancia para a analise"

        return False, None

    @staticmethod
    def split_por_remetente(historico_ordenado: list) -> dict:
        from ..models import MensagemAtendimento

        return {
            "cliente": [m for m in historico_ordenado if m["remetente_tipo"] == MensagemAtendimento.RemetenteTipo.CLIENTE],
            "atendente": [m for m in historico_ordenado if m["remetente_tipo"] == MensagemAtendimento.RemetenteTipo.ATENDENTE],
            "sistema": [m for m in historico_ordenado if m["remetente_tipo"] == MensagemAtendimento.RemetenteTipo.SISTEMA],
        }

    @staticmethod
    def get_mensagem_atual(historico_ordenado: list) -> dict:
        """Ultima mensagem do cliente nao marcada como ignorada -- proxy determinístico
        do 'estado mais recente do problema' entregue ao Agente 1 para sintese."""
        from ..models import MensagemAtendimento

        for mensagem in reversed(historico_ordenado):
            if mensagem["remetente_tipo"] == MensagemAtendimento.RemetenteTipo.CLIENTE and not mensagem["ignorada"]:
                return mensagem
        return {}
