"""
AHPEigenvectorService: resolve A w = lambda_max * w para uma matriz reciproca
positiva, usando decomposicao exata de autovalores (numpy.linalg.eig) em vez
da aproximacao de Saaty (normalizar colunas + media das linhas).

Motivo da escolha (ver plano da Fase 1): as matrizes deste dominio sao
pequenas (n <= 7), o enunciado pede explicitamente resolver a equacao de
autovalor, e o CR calculado a partir de lambda_max bloqueia a ativacao de
versoes do AHP -- nao ha margem para erro de aproximacao nessa checagem.
"""

import numpy as np

_POSITIVITY_TOLERANCE = 1e-9


class AHPEigenvectorService:
    @staticmethod
    def compute(matrix: np.ndarray) -> tuple:
        """
        Retorna (weights, lambda_max):
        - weights: np.ndarray de pesos positivos que somam 1.
        - lambda_max: o maior autovalor real da matriz (Perron-Frobenius).

        Levanta ValueError se a matriz nao for quadrada, nao tiver diagonal 1
        ou contiver valores nao positivos.
        """
        AHPEigenvectorService._validate(matrix)

        eigenvalues, eigenvectors = np.linalg.eig(matrix)
        real_eigenvalues = eigenvalues.real
        idx_max = int(np.argmax(real_eigenvalues))
        lambda_max = float(real_eigenvalues[idx_max])

        principal_vector = eigenvectors[:, idx_max].real

        # O sinal do autovetor principal e arbitrario; para uma matriz reciproca
        # positiva o autovetor de Perron deve ser todo positivo (ou todo negativo).
        if principal_vector.sum() < 0:
            principal_vector = -principal_vector

        total = principal_vector.sum()
        if total <= 0:
            raise ValueError("Nao foi possivel normalizar o autovetor principal (soma <= 0).")

        weights = principal_vector / total

        if np.any(weights < -_POSITIVITY_TOLERANCE):
            raise ValueError("O autovetor principal produziu pesos negativos: matriz invalida.")

        weights = np.clip(weights, 0.0, None)
        weights = weights / weights.sum()

        return weights, lambda_max

    @staticmethod
    def _validate(matrix: np.ndarray) -> None:
        if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
            raise ValueError("A matriz de comparacao precisa ser quadrada.")

        n = matrix.shape[0]
        diagonal = np.diag(matrix)
        if not np.allclose(diagonal, 1.0):
            raise ValueError("A diagonal da matriz de comparacao precisa ser toda igual a 1.")

        if np.any(matrix <= 0):
            raise ValueError("Todos os valores da matriz de comparacao precisam ser positivos.")
