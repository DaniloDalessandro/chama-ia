from django.core.management.base import BaseCommand, CommandError

from ahp.models import VersaoAHP
from ahp.services.consistency_service import AHPConsistencyService


class Command(BaseCommand):
    help = "Exibe lambda_max/CI/RI/CR (somente leitura) de uma versao AHP, usando os valores ja calculados."

    def add_arguments(self, parser):
        parser.add_argument("--versao-id", type=int, required=True)

    def handle(self, *args, **options):
        try:
            versao = VersaoAHP.objects.get(pk=options["versao_id"])
        except VersaoAHP.DoesNotExist as exc:
            raise CommandError(f"Versao AHP {options['versao_id']} nao encontrada.") from exc

        if versao.cr_criterios is None:
            raise CommandError(
                f"Versao {versao.numero_versao} ainda nao possui numeros calculados "
                "(rode ahp_recalcular ou ahp_ativar_versao primeiro)."
            )

        self.stdout.write(f"Versao {versao.numero_versao} ({versao.estado})")
        self.stdout.write("")
        self.stdout.write("[Criterios]")
        self._print_linha(versao.lambda_max_criterios, versao.ci_criterios, versao.cr_criterios)

        self.stdout.write("")
        self.stdout.write("[Intensidades por criterio]")
        cr_por_criterio = versao.cr_intensidades or {}
        ci_por_criterio = versao.ci_intensidades or {}
        lambda_por_criterio = versao.lambda_max_intensidades or {}
        for codigo in cr_por_criterio:
            self.stdout.write(f"  {codigo}:")
            self._print_linha(
                lambda_por_criterio.get(codigo), ci_por_criterio.get(codigo), cr_por_criterio.get(codigo), indent="    "
            )

    def _print_linha(self, lambda_max, ci, cr, indent=""):
        consistente = AHPConsistencyService.is_consistent(cr)
        status_txt = self.style.SUCCESS("consistente") if consistente else self.style.ERROR("INCONSISTENTE")
        self.stdout.write(
            f"{indent}lambda_max={lambda_max:.6f}  CI={ci:.6f}  CR={cr:.6f}  ({status_txt})"
        )
