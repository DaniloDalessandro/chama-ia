from django.test import SimpleTestCase

from ahp.services.matrix_service import AHPMatrixService


class BuildMatrixTests(SimpleTestCase):
    def test_diagonal_is_one_and_reciprocal(self):
        comparacoes = {(0, 1): 2.0, (0, 2): 4.0, (1, 2): 2.0}
        matrix = AHPMatrixService.build_matrix(3, comparacoes)

        for i in range(3):
            self.assertEqual(matrix[i][i], 1.0)

        self.assertEqual(matrix[0][1], 2.0)
        self.assertAlmostEqual(matrix[1][0], 0.5)
        self.assertEqual(matrix[0][2], 4.0)
        self.assertAlmostEqual(matrix[2][0], 0.25)

    def test_matrix_is_square(self):
        comparacoes = {(0, 1): 3.0}
        matrix = AHPMatrixService.build_matrix(2, comparacoes)
        self.assertEqual(matrix.shape, (2, 2))

    def test_missing_pair_raises(self):
        comparacoes = {(0, 1): 2.0}  # falta (0,2) e (1,2) para n=3
        with self.assertRaises(ValueError):
            AHPMatrixService.build_matrix(3, comparacoes)

    def test_lower_triangle_pair_rejected(self):
        comparacoes = {(1, 0): 2.0, (0, 2): 3.0, (1, 2): 2.0}
        with self.assertRaises(ValueError):
            AHPMatrixService.build_matrix(3, comparacoes)


class ValidateCompletenessTests(SimpleTestCase):
    def test_comparison_count_n_times_n_minus_1_over_2(self):
        self.assertEqual(AHPMatrixService.comparison_count(4), 6)
        self.assertEqual(AHPMatrixService.comparison_count(3), 3)
        self.assertEqual(AHPMatrixService.comparison_count(1), 0)

    def test_reports_exact_missing_pairs(self):
        comparacoes = {(0, 1): 2.0}
        missing = AHPMatrixService.validate_completeness(3, comparacoes)
        self.assertEqual(sorted(missing), ["(0,2)", "(1,2)"])

    def test_complete_matrix_reports_no_missing_pairs(self):
        comparacoes = {(0, 1): 2.0, (0, 2): 4.0, (1, 2): 2.0}
        self.assertEqual(AHPMatrixService.validate_completeness(3, comparacoes), [])

    def test_extra_pair_outside_upper_triangle_raises(self):
        comparacoes = {(0, 1): 2.0, (1, 0): 0.5}
        with self.assertRaises(ValueError):
            AHPMatrixService.validate_completeness(2, comparacoes)


class ValidateValuesTests(SimpleTestCase):
    def test_valid_saaty_scale_values_pass(self):
        comparacoes = {(0, 1): 1, (0, 2): 9, (1, 2): 1 / 7}
        self.assertEqual(AHPMatrixService.validate_values(comparacoes), [])

    def test_out_of_scale_value_is_reported(self):
        comparacoes = {(0, 1): 10.0}
        erros = AHPMatrixService.validate_values(comparacoes)
        self.assertEqual(len(erros), 1)

    def test_arbitrary_float_not_on_saaty_scale_is_reported(self):
        comparacoes = {(0, 1): 2.5}
        erros = AHPMatrixService.validate_values(comparacoes)
        self.assertEqual(len(erros), 1)
