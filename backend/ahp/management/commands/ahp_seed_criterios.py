"""
Comando idempotente: cria (get_or_create) os 4 criterios obrigatorios da
hierarquia AHP, suas 7 intensidades cada e as faixas padrao de tempo de
espera. Nunca cria Comparacao/VersaoAHP -- julgamentos Saaty sao entrada
de negocio real, nao dado de seed.
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from ahp.models import (
    CODIGO_IMPACTO_NO_CLIENTE,
    CODIGO_SENTIMENTO_DO_CLIENTE,
    CODIGO_TEMPO_DE_ESPERA,
    CODIGO_URGENCIA,
    Criterio,
    FaixaTempoEspera,
    Intensidade,
)

User = get_user_model()

CRITERIOS_SEED = [
    {
        "codigo": CODIGO_URGENCIA,
        "nome": "Urgencia",
        "ordem": 1,
        "cor_identificacao": "#DC2626",
        "descricao": "Necessidade de rapidez na solucao do atendimento.",
    },
    {
        "codigo": CODIGO_IMPACTO_NO_CLIENTE,
        "nome": "Impacto no Cliente",
        "ordem": 2,
        "cor_identificacao": "#EA580C",
        "descricao": "Gravidade e abrangencia das consequencias para o cliente.",
    },
    {
        "codigo": CODIGO_SENTIMENTO_DO_CLIENTE,
        "nome": "Sentimento do Cliente",
        "ordem": 3,
        "cor_identificacao": "#CA8A04",
        "descricao": "Insatisfacao, ansiedade, frustracao ou escalada emocional do cliente.",
    },
    {
        "codigo": CODIGO_TEMPO_DE_ESPERA,
        "nome": "Tempo de Espera",
        "ordem": 4,
        "cor_identificacao": "#16A34A",
        "descricao": "Tempo decorrido desde a abertura do atendimento, calculado deterministicamente.",
    },
]

INTENSIDADES_SEED = [
    (Intensidade.Codigo.AUSENTE, "Ausente", 1),
    (Intensidade.Codigo.MUITO_BAIXA, "Muito Baixa", 2),
    (Intensidade.Codigo.BAIXA, "Baixa", 3),
    (Intensidade.Codigo.MODERADA, "Moderada", 4),
    (Intensidade.Codigo.ALTA, "Alta", 5),
    (Intensidade.Codigo.CRITICA, "Critica", 6),
    (Intensidade.Codigo.INCONCLUSIVA, "Inconclusiva", 7),
]

FAIXAS_TEMPO_SEED = [
    (0, 5, Intensidade.Codigo.BAIXA),
    (5, 15, Intensidade.Codigo.MODERADA),
    (15, 30, Intensidade.Codigo.ALTA),
    (30, 60, Intensidade.Codigo.CRITICA),
    (60, None, Intensidade.Codigo.CRITICA),
]


class Command(BaseCommand):
    help = "Cria (idempotente) os 4 criterios obrigatorios, suas intensidades e as faixas de tempo de espera."

    def add_arguments(self, parser):
        parser.add_argument("--user-email", required=True, help="E-mail do usuario responsavel pela operacao.")

    def handle(self, *args, **options):
        try:
            user = User.objects.get(email=options["user_email"])
        except User.DoesNotExist as exc:
            raise CommandError(f"Usuario com email '{options['user_email']}' nao encontrado.") from exc

        criados_criterios = 0
        criados_intensidades = 0
        criados_faixas = 0

        with transaction.atomic():
            intensidades_por_criterio = {}

            for dados in CRITERIOS_SEED:
                criterio, created = Criterio.objects.get_or_create(
                    codigo=dados["codigo"],
                    defaults={
                        "nome": dados["nome"],
                        "ordem": dados["ordem"],
                        "cor_identificacao": dados["cor_identificacao"],
                        "descricao": dados["descricao"],
                        "ativo": True,
                        "criado_por": user,
                        "atualizado_por": user,
                    },
                )
                criados_criterios += int(created)
                self.stdout.write(("Criado" if created else "Ja existia") + f": criterio {criterio.codigo}")

                intensidades_por_criterio[criterio.codigo] = {}
                for codigo_intensidade, nome, ordem in INTENSIDADES_SEED:
                    intensidade, created = Intensidade.objects.get_or_create(
                        criterio=criterio,
                        codigo=codigo_intensidade,
                        defaults={"nome": nome, "ordem": ordem, "criado_por": user, "atualizado_por": user},
                    )
                    criados_intensidades += int(created)
                    intensidades_por_criterio[criterio.codigo][codigo_intensidade] = intensidade

            criterio_tempo_codigo = CODIGO_TEMPO_DE_ESPERA
            for idx, (minutos_min, minutos_max, codigo_intensidade) in enumerate(FAIXAS_TEMPO_SEED, start=1):
                intensidade = intensidades_por_criterio[criterio_tempo_codigo][codigo_intensidade]
                criterio_tempo = Criterio.objects.get(codigo=criterio_tempo_codigo)
                _, created = FaixaTempoEspera.objects.get_or_create(
                    criterio=criterio_tempo,
                    minutos_min=minutos_min,
                    defaults={
                        "minutos_max": minutos_max,
                        "intensidade": intensidade,
                        "ordem": idx,
                        "criado_por": user,
                        "atualizado_por": user,
                    },
                )
                criados_faixas += int(created)

        self.stdout.write(self.style.SUCCESS(
            f"Seed concluido. Criterios criados: {criados_criterios}. "
            f"Intensidades criadas: {criados_intensidades}. Faixas criadas: {criados_faixas}."
        ))
