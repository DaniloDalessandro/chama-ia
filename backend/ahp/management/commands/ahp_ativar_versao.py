from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from ahp.models import VersaoAHP
from ahp.services.version_service import AHPVersionService, InvalidStateTransitionError

User = get_user_model()


class Command(BaseCommand):
    help = "Executa a maquina de estados completa de ativacao de uma versao AHP (RASCUNHO -> ATIVA)."

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
            resultado = AHPVersionService.ativar(versao, user=user)
        except InvalidStateTransitionError as exc:
            raise CommandError(str(exc)) from exc

        if resultado.estado == VersaoAHP.Estado.ATIVA:
            anterior = VersaoAHP.objects.filter(
                estado=VersaoAHP.Estado.ARQUIVADA, arquivada_em__isnull=False
            ).order_by("-arquivada_em").first()
            mensagem = f"Versao {resultado.numero_versao} ativada com sucesso."
            if anterior is not None:
                mensagem += f" Versao {anterior.numero_versao} foi arquivada."
            self.stdout.write(self.style.SUCCESS(mensagem))
            return

        self.stdout.write(self.style.ERROR(
            f"Versao {resultado.numero_versao} NAO foi ativada (estado final: '{resultado.estado}')."
        ))
        for erro in resultado.mensagens_erro:
            self.stdout.write(f"  - {erro}")
        raise CommandError(f"Ativacao bloqueada: versao terminou em estado '{resultado.estado}'.")
