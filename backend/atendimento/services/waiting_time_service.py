"""
WaitingTimeService: tempo de espera calculado deterministicamente a partir de
timestamps -- nunca perguntado a um LLM, nunca inferido por linguagem natural
quando ha timestamps confiaveis.
"""

from django.utils import timezone

from ahp.models import CODIGO_TEMPO_DE_ESPERA, Criterio, Intensidade

from ..models import Atendimento


class WaitingTimeService:
    @staticmethod
    def compute_wait_minutes(atendimento: Atendimento, agora=None) -> float:
        agora = agora or timezone.now()
        delta = agora - atendimento.criado_em
        return max(0.0, delta.total_seconds() / 60.0)

    @staticmethod
    def get_intensidade_for_wait(minutos: float) -> Intensidade:
        """
        Retorna a Intensidade mapeada pela FaixaTempoEspera ativa que contem
        `minutos`. Levanta ValueError se nenhuma faixa cobrir o valor (config
        incompleta) -- nunca inventa uma intensidade default.
        """
        try:
            criterio_tempo = Criterio.objects.get(codigo=CODIGO_TEMPO_DE_ESPERA)
        except Criterio.DoesNotExist as exc:
            raise ValueError("Criterio TEMPO_DE_ESPERA nao esta cadastrado.") from exc

        faixas = criterio_tempo.faixas_tempo.filter(ativo=True).order_by("minutos_min")
        for faixa in faixas:
            if minutos < faixa.minutos_min:
                continue
            if faixa.minutos_max is None or minutos < faixa.minutos_max:
                return faixa.intensidade

        raise ValueError(f"Nenhuma faixa de tempo de espera cobre {minutos:.1f} minutos.")

    @staticmethod
    def get_intensidade_atual(atendimento: Atendimento, agora=None) -> Intensidade:
        minutos = WaitingTimeService.compute_wait_minutes(atendimento, agora=agora)
        return WaitingTimeService.get_intensidade_for_wait(minutos)
