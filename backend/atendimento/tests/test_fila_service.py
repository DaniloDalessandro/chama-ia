from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from atendimento.models import Atendimento
from atendimento.services.fila_service import FilaService


def _set_criado_em(atendimento, quando):
    Atendimento.objects.filter(pk=atendimento.pk).update(criado_em=quando)


class FilaServiceOrderingTests(TestCase):
    def setUp(self):
        self.agora = timezone.now()

    def _criar(self, **kwargs):
        defaults = {"nome": "Cliente", "email": f"c{Atendimento.objects.count()}@test.com"}
        defaults.update(kwargs)
        atendimento = Atendimento.objects.create(**defaults)
        _set_criado_em(atendimento, self.agora)
        return atendimento

    def test_regra_critica_sorts_first_regardless_of_prioridade(self):
        p1_sem_regra = self._criar(prioridade=Atendimento.Prioridade.P1, indice_ahp=90)
        p4_com_regra = self._criar(prioridade=Atendimento.Prioridade.P4, indice_ahp=10, regra_critica_confirmada=True)

        fila = list(FilaService.get_fila_ordenada())

        self.assertEqual(fila[0].id, p4_com_regra.id)
        self.assertEqual(fila[1].id, p1_sem_regra.id)

    def test_prioridade_tiers_in_exact_order(self):
        p3 = self._criar(prioridade=Atendimento.Prioridade.P3)
        p1 = self._criar(prioridade=Atendimento.Prioridade.P1)
        nao_classificado = self._criar(prioridade=Atendimento.Prioridade.NAO_CLASSIFICADO)
        p2 = self._criar(prioridade=Atendimento.Prioridade.P2)
        revisao = self._criar(prioridade=Atendimento.Prioridade.REVISAO_HUMANA)
        p4 = self._criar(prioridade=Atendimento.Prioridade.P4)

        fila_ids = [a.id for a in FilaService.get_fila_ordenada()]

        self.assertEqual(fila_ids, [p1.id, p2.id, p3.id, p4.id, nao_classificado.id, revisao.id])

    def test_indice_ahp_tiebreak_within_same_prioridade(self):
        baixo = self._criar(prioridade=Atendimento.Prioridade.P1, indice_ahp=60.0)
        alto = self._criar(prioridade=Atendimento.Prioridade.P1, indice_ahp=95.0)
        nulo = self._criar(prioridade=Atendimento.Prioridade.P1, indice_ahp=None)

        fila_ids = [a.id for a in FilaService.get_fila_ordenada()]

        self.assertEqual(fila_ids, [alto.id, baixo.id, nulo.id])  # NULLS LAST

    def test_tempo_de_espera_tiebreak_when_prioridade_and_indice_tie(self):
        recente = self._criar(prioridade=Atendimento.Prioridade.P2, indice_ahp=70.0)
        _set_criado_em(recente, self.agora - timedelta(minutes=5))

        antigo = self._criar(prioridade=Atendimento.Prioridade.P2, indice_ahp=70.0)
        _set_criado_em(antigo, self.agora - timedelta(hours=3))

        fila_ids = [a.id for a in FilaService.get_fila_ordenada()]

        self.assertEqual(fila_ids, [antigo.id, recente.id])  # maior tempo de espera primeiro

    def test_resolvido_cancelado_encaminhado_never_appear_even_if_critical_p1(self):
        for status_ in [
            Atendimento.StatusAtendimento.RESOLVIDO,
            Atendimento.StatusAtendimento.CANCELADO,
            Atendimento.StatusAtendimento.ENCAMINHADO_PARA_CHAMADO,
        ]:
            self._criar(
                prioridade=Atendimento.Prioridade.P1, regra_critica_confirmada=True, status_atendimento=status_,
            )

        self.assertEqual(FilaService.get_fila_ordenada().count(), 0)

    def test_active_atendimentos_of_every_non_excluded_status_appear(self):
        for status_ in [
            Atendimento.StatusAtendimento.AGUARDANDO,
            Atendimento.StatusAtendimento.EM_ATENDIMENTO,
            Atendimento.StatusAtendimento.AGUARDANDO_CLIENTE,
        ]:
            self._criar(status_atendimento=status_)

        self.assertEqual(FilaService.get_fila_ordenada().count(), 3)
