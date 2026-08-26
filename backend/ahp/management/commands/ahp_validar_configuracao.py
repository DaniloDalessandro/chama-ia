from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from ahp.models import VersaoAHP
from ahp.services.version_service import AHPVersionService

User = get_user_model()


class Command(BaseCommand):
    help = "Valida (somente leitura) uma versao AHP em RASCUNHO, sem ativa-la."

    def add_arguments(self, parser):
        parser.add_argument("--versao-id", type=int, required=True)
        parser.add_argument("--user-email", required=True, help="E-mail do usuario responsavel pela operacao.")

    def handle(self, *args, **options):
        self._resolve_user(options["user_email"])

        try:
            versao = VersaoAHP.objects.get(pk=options["versao_id"])
        except VersaoAHP.DoesNotExist as exc:
            raise CommandError(f"Versao AHP {options['versao_id']} nao encontrada.") from exc

        erros = AHPVersionService.validar(versao)

        if not erros:
            self.stdout.write(self.style.SUCCESS(f"Versao {versao.numero_versao}: configuracao valida."))
            return

        self.stdout.write(self.style.ERROR(f"Versao {versao.numero_versao}: {len(erros)} erro(s) encontrado(s):"))
        for erro in erros:
            self.stdout.write(f"  - {erro}")
        raise CommandError(f"Validacao falhou com {len(erros)} erro(s).")

    def _resolve_user(self, email):
        try:
            return User.objects.get(email=email)
        except User.DoesNotExist as exc:
            raise CommandError(f"Usuario com email '{email}' nao encontrado.") from exc
