"""
Comando "prova de conceito" da Fase 1: roda o pipeline deterministico
completo (intensidades -> sintese AHP -> indice -> P1-P4/REVISAO_HUMANA) sem
absolutamente nenhuma chamada de rede/LLM.

Uso:
  python manage.py ahp_testar_priorizacao --versao-id 1 --user-email admin@x.com \
      --intensidades URGENCIA=CRITICA,IMPACTO_NO_CLIENTE=ALTA,SENTIMENTO_DO_CLIENTE=BAIXA,TEMPO_DE_ESPERA=MODERADA \
      [--atendimento-id 42] [--regra-critica]

Sem --atendimento-id: apenas simula e imprime o resultado (nao persiste nada).
Com --atendimento-id: persiste uma AuditoriaClassificacao real, atribuida ao
usuario resolvido por --user-email.
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from ahp.models import VersaoAHP
from atendimento.models import Atendimento
from atendimento.services.classification_service import ServicePriorityClassificationService
from atendimento.services.persistence_service import ServicePersistenceService

User = get_user_model()


class Command(BaseCommand):
    help = "Executa o pipeline deterministico de priorizacao (AHP) para intensidades informadas manualmente, sem IA."

    def add_arguments(self, parser):
        parser.add_argument("--versao-id", type=int, required=True)
        parser.add_argument("--user-email", required=True)
        parser.add_argument(
            "--intensidades", required=True,
            help="Lista CRITERIO_CODIGO=INTENSIDADE_CODIGO separada por virgulas, ex: URGENCIA=CRITICA,TEMPO_DE_ESPERA=BAIXA",
        )
        parser.add_argument("--atendimento-id", type=int, default=None)
        parser.add_argument("--regra-critica", action="store_true", default=False)

    def handle(self, *args, **options):
        try:
            user = User.objects.get(email=options["user_email"])
        except User.DoesNotExist as exc:
            raise CommandError(f"Usuario com email '{options['user_email']}' nao encontrado.") from exc

        try:
            versao_ahp = VersaoAHP.objects.get(pk=options["versao_id"])
        except VersaoAHP.DoesNotExist as exc:
            raise CommandError(f"Versao AHP {options['versao_id']} nao encontrada.") from exc

        if not versao_ahp.pesos_criterios:
            raise CommandError(
                f"Versao {versao_ahp.numero_versao} ainda nao possui pesos calculados "
                "(rode ahp_recalcular ou ahp_ativar_versao primeiro)."
            )

        intensidades = self._parse_intensidades(options["intensidades"])

        resultado = ServicePriorityClassificationService.classify_from_intensidades(versao_ahp, intensidades)

        self._print_resultado(resultado, regra_critica=options["regra_critica"])

        atendimento_id = options["atendimento_id"]
        if atendimento_id is None:
            self.stdout.write(self.style.WARNING("SIMULACAO (nao persistido) -- use --atendimento-id para persistir."))
            return

        try:
            atendimento = Atendimento.objects.get(pk=atendimento_id)
        except Atendimento.DoesNotExist as exc:
            raise CommandError(f"Atendimento {atendimento_id} nao encontrado.") from exc

        if options["regra_critica"]:
            atendimento.regra_critica_confirmada = True
            atendimento.atualizado_por = user
            atendimento.save(update_fields=["regra_critica_confirmada", "atualizado_por", "atualizado_em"])

        auditoria = ServicePersistenceService.persist(atendimento, resultado, versao_ahp, user=user)
        self.stdout.write(self.style.SUCCESS(
            f"PERSISTIDO -- AuditoriaClassificacao #{auditoria.pk} criada para o atendimento #{atendimento.pk}."
        ))

    def _parse_intensidades(self, raw: str) -> dict:
        intensidades = {}
        for par in raw.split(","):
            par = par.strip()
            if not par:
                continue
            if "=" not in par:
                raise CommandError(f"Formato invalido em --intensidades: '{par}' (esperado CRITERIO=INTENSIDADE).")
            criterio_codigo, intensidade_codigo = par.split("=", 1)
            intensidades[criterio_codigo.strip().upper()] = intensidade_codigo.strip().lower()
        return intensidades

    def _print_resultado(self, resultado, regra_critica: bool):
        self.stdout.write(f"Intensidades: {resultado.intensidades}")
        if regra_critica:
            self.stdout.write(self.style.WARNING("Regra critica confirmada -- sobe ao topo da fila (nao altera o indice)."))

        if resultado.revisao_humana:
            self.stdout.write(self.style.WARNING(f"Prioridade: {resultado.prioridade}"))
            for motivo in resultado.motivos_revisao_humana:
                self.stdout.write(f"  - {motivo}")
            return

        self.stdout.write("Contribuicoes por criterio:")
        for codigo, contribuicao in resultado.contribuicoes.items():
            self.stdout.write(f"  {codigo}: {contribuicao:.4f}")
        self.stdout.write(f"P(a) = {resultado.p:.4f}   P_max = {resultado.p_max:.4f}")
        self.stdout.write(self.style.SUCCESS(f"Indice = {resultado.indice:.2f}   Prioridade = {resultado.prioridade}"))
