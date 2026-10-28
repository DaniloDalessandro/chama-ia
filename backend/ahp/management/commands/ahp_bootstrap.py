"""
Bootstrap idempotente da hierarquia AHP para ambientes novos (ex.: producao).

Se ja existir uma VersaoAHP ATIVA, nao faz nada. Caso contrario:
  1. executa o seed dos criterios, intensidades e faixas de tempo;
  2. cria uma VersaoAHP em RASCUNHO com os julgamentos de referencia
     documentados no projeto (matriz de criterios e matriz de intensidades);
  3. ativa a versao pela maquina de estados oficial (CR <= 0,10 obrigatorio).

Os julgamentos usados aqui sao os da configuracao de referencia do Cham.IA
(Urgencia > Impacto > Sentimento > Tempo de espera). Para alterar os pesos,
crie uma nova versao pelo admin/API -- este comando so atua quando nao ha
nenhuma versao ativa.

Uso:
    python manage.py ahp_bootstrap [--user-email admin@chamaia.local]
"""

import os

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from ahp.models import (
    CODIGO_IMPACTO_NO_CLIENTE,
    CODIGO_SENTIMENTO_DO_CLIENTE,
    CODIGO_TEMPO_DE_ESPERA,
    CODIGO_URGENCIA,
    VersaoAHP,
)
from ahp.services.comparison_service import AHPComparisonService
from ahp.services.hierarchy_service import AHPHierarchyService
from ahp.services.intensity_service import AHPIntensityService
from ahp.services.version_service import AHPVersionService

User = get_user_model()

# Matriz de criterios (escala de Saaty), linha i vs coluna j, i < j.
ORDEM_CRITERIOS = [
    CODIGO_URGENCIA,
    CODIGO_IMPACTO_NO_CLIENTE,
    CODIGO_SENTIMENTO_DO_CLIENTE,
    CODIGO_TEMPO_DE_ESPERA,
]
JULGAMENTOS_CRITERIOS = {
    (0, 1): 3, (0, 2): 5, (0, 3): 7,
    (1, 2): 3, (1, 3): 5,
    (2, 3): 3,
}

# Matriz de intensidades (mesma para todos os criterios), em ordem crescente:
# muito_baixa, baixa, moderada, alta, critica. Valores < 1 indicam que a
# intensidade da linha e menos prioritaria que a da coluna. CR ~ 0,011.
ORDEM_INTENSIDADES = ["muito_baixa", "baixa", "moderada", "alta", "critica"]
JULGAMENTOS_INTENSIDADES = {
    (0, 1): 1 / 2, (0, 2): 1 / 4, (0, 3): 1 / 7, (0, 4): 1 / 8,
    (1, 2): 1 / 2, (1, 3): 1 / 4, (1, 4): 1 / 7,
    (2, 3): 1 / 2, (2, 4): 1 / 4,
    (3, 4): 1 / 2,
}


class Command(BaseCommand):
    help = "Cria e ativa (idempotente) a versao AHP de referencia quando nao ha versao ativa."

    def add_arguments(self, parser):
        parser.add_argument(
            "--user-email",
            default=os.environ.get("DJANGO_SUPERUSER_EMAIL", "admin@chamaia.local"),
            help="E-mail do usuario responsavel (padrao: DJANGO_SUPERUSER_EMAIL).",
        )

    def handle(self, *args, **options):
        ativa = AHPVersionService.get_versao_ativa()
        if ativa is not None:
            self.stdout.write(
                f"Ja existe versao AHP ativa (v{ativa.numero_versao}, CR={ativa.cr_criterios:.4f}). Nada a fazer."
            )
            return

        email = options["user_email"]
        user = User.objects.filter(email=email).first() or User.objects.filter(is_superuser=True).first()
        if user is None:
            raise CommandError("Nenhum usuario administrador encontrado para registrar a auditoria.")

        call_command("ahp_seed_criterios", user_email=user.email, stdout=self.stdout)

        criterios_ativos = {c.codigo: c for c in AHPHierarchyService.get_criterios_ativos()}
        faltando = [cod for cod in ORDEM_CRITERIOS if cod not in criterios_ativos]
        if faltando:
            raise CommandError(f"Criterios obrigatorios ausentes apos o seed: {faltando}")
        criterios = [criterios_ativos[cod] for cod in ORDEM_CRITERIOS]

        versao = AHPVersionService.create_rascunho(
            descricao="Versao de referencia criada automaticamente (ahp_bootstrap).", user=user
        )

        # As comparacoes sao gravadas na ordem em que o servico de versao le os
        # criterios/intensidades, para que os indices (i, j) correspondam.
        ordem_servico = list(AHPHierarchyService.get_criterios_ativos())
        valores_criterios = {}
        for (i, j), valor in JULGAMENTOS_CRITERIOS.items():
            a, b = criterios[i], criterios[j]
            ia, ib = ordem_servico.index(a), ordem_servico.index(b)
            if ia < ib:
                valores_criterios[(ia, ib)] = float(valor)
            else:
                valores_criterios[(ib, ia)] = 1.0 / float(valor)
        AHPComparisonService.save_comparacoes_criterios(versao, ordem_servico, valores_criterios, user=user)

        for criterio in criterios:
            intensidades = list(AHPIntensityService.get_comparable_intensidades(criterio))
            por_codigo = {it.codigo: it for it in intensidades}
            if set(por_codigo) != set(ORDEM_INTENSIDADES):
                raise CommandError(
                    f"[{criterio.codigo}] intensidades comparaveis inesperadas: {sorted(por_codigo)}"
                )
            valores_int = {}
            for (i, j), valor in JULGAMENTOS_INTENSIDADES.items():
                a, b = por_codigo[ORDEM_INTENSIDADES[i]], por_codigo[ORDEM_INTENSIDADES[j]]
                ia, ib = intensidades.index(a), intensidades.index(b)
                if ia < ib:
                    valores_int[(ia, ib)] = float(valor)
                else:
                    valores_int[(ib, ia)] = 1.0 / float(valor)
            AHPComparisonService.save_comparacoes_intensidades(versao, criterio, intensidades, valores_int, user=user)

        resultado = AHPVersionService.ativar(versao, user=user)
        if resultado.estado != VersaoAHP.Estado.ATIVA:
            raise CommandError(
                f"Versao {resultado.numero_versao} nao foi ativada (estado '{resultado.estado}'): "
                f"{resultado.mensagens_erro}"
            )

        pesos = ", ".join(f"{cod}={peso:.3f}" for cod, peso in resultado.pesos_criterios.items())
        self.stdout.write(self.style.SUCCESS(
            f"Versao AHP v{resultado.numero_versao} ativada. CR={resultado.cr_criterios:.4f}. Pesos: {pesos}"
        ))
