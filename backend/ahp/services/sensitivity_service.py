"""
AHPSensitivityService: analise de sensibilidade minima sobre os pesos dos
criterios. Implementacao Fase 1: perturbar um peso e renormalizar os demais
proporcionalmente, mantendo a soma em 1. Sem endpoint exposto ainda.
"""


class AHPSensitivityService:
    @staticmethod
    def perturb_weight(pesos_criterios: dict, criterio_codigo: str, delta: float) -> dict:
        if criterio_codigo not in pesos_criterios:
            raise ValueError(f"Criterio '{criterio_codigo}' nao encontrado nos pesos informados.")

        novo_peso = pesos_criterios[criterio_codigo] + delta
        if not (0.0 <= novo_peso <= 1.0):
            raise ValueError("O peso perturbado precisa permanecer entre 0 e 1.")

        outros_codigos = [c for c in pesos_criterios if c != criterio_codigo]
        soma_outros = sum(pesos_criterios[c] for c in outros_codigos)
        restante = 1.0 - novo_peso

        resultado = {criterio_codigo: novo_peso}
        if soma_outros <= 0:
            for codigo in outros_codigos:
                resultado[codigo] = 0.0
        else:
            for codigo in outros_codigos:
                resultado[codigo] = pesos_criterios[codigo] / soma_outros * restante

        return resultado
