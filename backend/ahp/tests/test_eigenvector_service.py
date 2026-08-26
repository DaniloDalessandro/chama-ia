import numpy as np
from django.test import SimpleTestCase

from ahp.services.eigenvector_service import AHPEigenvectorService
from ahp.services.matrix_service import AHPMatrixService


class ComputeTests(SimpleTestCase):
    def test_3x3_perfectly_consistent_matrix(self):
        # Matriz construida a partir da razao exata de pesos [4, 2, 1]:
        # a_ij = w_i / w_j. lambda_max deve ser exatamente n=3, CI=0.
        comparacoes = {(0, 1): 2.0, (0, 2): 4.0, (1, 2): 2.0}
        matrix = AHPMatrixService.build_matrix(3, comparacoes)

        weights, lambda_max = AHPEigenvectorService.compute(matrix)

        self.assertAlmostEqual(lambda_max, 3.0, places=6)
        np.testing.assert_allclose(weights, [4 / 7, 2 / 7, 1 / 7], atol=1e-6)
        self.assertAlmostEqual(weights.sum(), 1.0, places=9)

    def test_4x4_perfectly_consistent_matrix(self):
        # Pesos [8, 4, 2, 1], todas as razoes dentro da escala de Saaty (1-9).
        comparacoes = {
            (0, 1): 2.0, (0, 2): 4.0, (0, 3): 8.0,
            (1, 2): 2.0, (1, 3): 4.0,
            (2, 3): 2.0,
        }
        matrix = AHPMatrixService.build_matrix(4, comparacoes)

        weights, lambda_max = AHPEigenvectorService.compute(matrix)

        self.assertAlmostEqual(lambda_max, 4.0, places=6)
        np.testing.assert_allclose(weights, [8 / 15, 4 / 15, 2 / 15, 1 / 15], atol=1e-6)
        self.assertAlmostEqual(weights.sum(), 1.0, places=9)

    def test_weights_are_always_positive(self):
        comparacoes = {(0, 1): 5.0, (0, 2): 6.0, (1, 2): 4.0}
        matrix = AHPMatrixService.build_matrix(3, comparacoes)

        weights, _ = AHPEigenvectorService.compute(matrix)

        self.assertTrue(np.all(weights >= 0))
        self.assertAlmostEqual(weights.sum(), 1.0, places=9)

    def test_inconsistent_matrix_still_yields_valid_weight_vector(self):
        matrix = np.array([[1, 5, 6], [1 / 5, 1, 4], [1 / 6, 1 / 4, 1]])

        weights, lambda_max = AHPEigenvectorService.compute(matrix)

        self.assertGreater(lambda_max, 3.0)  # sempre >= n, so igual quando perfeitamente consistente
        self.assertAlmostEqual(weights.sum(), 1.0, places=9)

    def test_non_square_matrix_raises(self):
        with self.assertRaises(ValueError):
            AHPEigenvectorService.compute(np.array([[1, 2, 3], [0.5, 1, 2]]))

    def test_bad_diagonal_raises(self):
        with self.assertRaises(ValueError):
            AHPEigenvectorService.compute(np.array([[1, 2], [0.5, 2]]))

    def test_non_positive_value_raises(self):
        with self.assertRaises(ValueError):
            AHPEigenvectorService.compute(np.array([[1, -2], [-0.5, 1]]))
