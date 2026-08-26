"""
AHPMatrixService: construcao e validacao de matrizes reciprocas de comparacao
par-a-par (escala de Saaty), a partir de pares (i, j) com i < j.

Este servico e puro (sem ORM): trabalha sobre indices inteiros posicionais,
nao sobre instancias de model. O mapeamento indice <-> Criterio/Intensidade
e responsabilidade do chamador (ex: AHPComparisonService).
"""

import numpy as np

# Escala de Saaty: valores inteiros de 1 a 9 e seus reciprocos.
SAATY_VALUES = frozenset(list(range(1, 10)) + [1 / v for v in range(2, 10)])
_SAATY_TOLERANCE = 1e-9


class AHPMatrixService:
    @staticmethod
    def build_matrix(n: int, comparacoes: dict) -> np.ndarray:
        """
        Constroi uma matriz n x n reciproca a partir de um dict
        {(i, j): valor_saaty} contendo apenas pares com i < j (0-indexado).

        - diagonal = 1
        - a[j][i] = 1 / a[i][j]  (reciprocidade sempre derivada, nunca informada)

        Levanta ValueError se algum par estiver fora do triangulo superior,
        se houver pares repetidos/faltando, ou se `n` for invalido.
        """
        if n < 1:
            raise ValueError("A matriz precisa ter pelo menos 1 item (n >= 1).")

        missing = AHPMatrixService.validate_completeness(n, comparacoes)
        if missing:
            raise ValueError(
                "Matriz de comparacao incompleta. Pares faltando: " + ", ".join(missing)
            )

        matrix = np.ones((n, n), dtype=float)
        for (i, j), valor in comparacoes.items():
            if not (0 <= i < j < n):
                raise ValueError(
                    f"Par de comparacao invalido ({i}, {j}): apenas o triangulo "
                    "superior (i < j) deve ser informado."
                )
            matrix[i][j] = valor
            matrix[j][i] = 1.0 / valor

        return matrix

    @staticmethod
    def validate_completeness(n: int, comparacoes: dict) -> list:
        """
        Retorna a lista (como strings legiveis) dos pares (i, j), i < j, que
        estao faltando em `comparacoes`. Lista vazia = matriz completa, com
        exatamente n(n-1)/2 comparacoes.
        """
        esperados = {(i, j) for i in range(n) for j in range(i + 1, n)}
        informados = set(comparacoes.keys())

        extras = informados - esperados
        if extras:
            raise ValueError(
                "Comparacoes fora do triangulo superior esperado: "
                + ", ".join(f"({i},{j})" for i, j in sorted(extras))
            )

        faltando = esperados - informados
        return [f"({i},{j})" for i, j in sorted(faltando)]

    @staticmethod
    def validate_values(comparacoes: dict) -> list:
        """
        Retorna lista de mensagens de erro para valores fora da escala de Saaty
        (inteiros de 1 a 9 ou seus reciprocos 1/2..1/9). Lista vazia = tudo ok.
        """
        erros = []
        for (i, j), valor in comparacoes.items():
            if not any(abs(valor - saaty) < _SAATY_TOLERANCE for saaty in SAATY_VALUES):
                erros.append(
                    f"Valor {valor} do par ({i},{j}) nao pertence a escala de Saaty "
                    "(1-9 ou seus reciprocos)."
                )
        return erros

    @staticmethod
    def comparison_count(n: int) -> int:
        """Numero de comparacoes necessarias: n(n-1)/2."""
        return n * (n - 1) // 2
