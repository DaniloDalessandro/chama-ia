from django.db import IntegrityError, transaction
from django.test import TestCase

from ahp.models import Comparacao, Criterio, Intensidade, Termo, VersaoAHP


class CriterioSoftDeleteTests(TestCase):
    def test_soft_delete_hides_from_default_manager_but_row_persists(self):
        criterio = Criterio.objects.create(nome="Urgencia", codigo="URGENCIA")

        criterio.soft_delete()

        self.assertFalse(Criterio.objects.filter(pk=criterio.pk).exists())
        self.assertTrue(Criterio.all_objects.filter(pk=criterio.pk).exists())
        criterio.refresh_from_db()
        self.assertIsNotNone(criterio.excluido_em)


class IntensidadeConstraintTests(TestCase):
    def test_unique_codigo_per_criterio(self):
        criterio = Criterio.objects.create(nome="Urgencia", codigo="URGENCIA")
        Intensidade.objects.create(criterio=criterio, nome="Baixa", codigo=Intensidade.Codigo.BAIXA)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Intensidade.objects.create(criterio=criterio, nome="Baixa de novo", codigo=Intensidade.Codigo.BAIXA)


class TermoDefaultsTests(TestCase):
    def test_default_status_aprovacao_is_aprovado(self):
        criterio = Criterio.objects.create(nome="Urgencia", codigo="URGENCIA")
        intensidade = Intensidade.objects.create(criterio=criterio, nome="Alta", codigo=Intensidade.Codigo.ALTA)

        termo = Termo.objects.create(criterio=criterio, termo="vence hoje", intensidade_base=intensidade)

        self.assertEqual(termo.status_aprovacao, Termo.StatusAprovacao.APROVADO)
        self.assertTrue(termo.considerar_mensagem_atual)


class ComparacaoCheckConstraintTests(TestCase):
    def setUp(self):
        self.versao = VersaoAHP.objects.create()
        self.c1 = Criterio.objects.create(nome="Urgencia", codigo="URGENCIA", ordem=1)
        self.c2 = Criterio.objects.create(nome="Impacto", codigo="IMPACTO_NO_CLIENTE", ordem=2)
        self.i1 = Intensidade.objects.create(criterio=self.c1, nome="Baixa", codigo=Intensidade.Codigo.BAIXA)
        self.i2 = Intensidade.objects.create(criterio=self.c1, nome="Alta", codigo=Intensidade.Codigo.ALTA)

    def test_criterios_type_accepts_only_criterio_fields(self):
        Comparacao.objects.create(
            versao_ahp=self.versao, tipo=Comparacao.Tipo.CRITERIOS,
            criterio_linha=self.c1, criterio_coluna=self.c2, valor_saaty=2.0,
        )

    def test_criterios_type_rejects_mixed_intensidade_fields(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Comparacao.objects.create(
                    versao_ahp=self.versao, tipo=Comparacao.Tipo.CRITERIOS,
                    criterio_linha=self.c1, criterio_coluna=self.c2,
                    intensidade_linha=self.i1, valor_saaty=2.0,
                )

    def test_intensidades_type_requires_contexto(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Comparacao.objects.create(
                    versao_ahp=self.versao, tipo=Comparacao.Tipo.INTENSIDADES,
                    intensidade_linha=self.i1, intensidade_coluna=self.i2, valor_saaty=2.0,
                )

    def test_intensidades_type_accepts_valid_row(self):
        Comparacao.objects.create(
            versao_ahp=self.versao, tipo=Comparacao.Tipo.INTENSIDADES, criterio_contexto=self.c1,
            intensidade_linha=self.i1, intensidade_coluna=self.i2, valor_saaty=2.0,
        )
