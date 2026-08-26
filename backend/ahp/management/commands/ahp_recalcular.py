from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from ahp.models import VersaoAHP
from ahp.services.version_service import AHPVersionService, InvalidStateTransitionError

User = get_user_model()


class Command(BaseCommand):
    help = "Recalcula pesos/CI/CR de uma versao AHP em RASCUNHO sem mudar seu estado."

    def add_arguments(self, parser):
        parser.add_argument("--versao-id", type=int, required=True)
        parser.add_argument("--user-email", required=True)

    def handle(self, *args, **options):
        try:
            user = User.objects.get(email=options["user_email"])
        except User.DoesNotExist as exc:
            raise CommandError(f"Usuario com email '{options['user_email']}' nao encontrado.") from exc

        try:
            versao = VersaoAHP.objects.get(pk=options["versao_id"])
        except VersaoAHP.DoesNotExist as exc:
            raise CommandError(f"Versao AHP {options['versao_id']} nao encontrada.") from exc

        try:
            resultado = AHPVersionService.recalcular(versao, user=user)
        except (InvalidStateTransitionError, ValueError) as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(self.style.SUCCESS(
            f"Versao {resultado.numero_versao} recalculada. "
            f"CR (criterios) = {resultado.cr_criterios:.4f}. Estado permanece '{resultado.estado}'."
        ))
