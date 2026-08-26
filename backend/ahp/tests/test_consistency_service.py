from django.test import SimpleTestCase

from ahp.services.consistency_service import RANDOM_INDEX, AHPConsistencyService


class RandomIndexTableTests(SimpleTestCase):
    def test_exact_saaty_table_values(self):
        expected = {
            1: 0.00, 2: 0.00, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32,
            8: 1.41, 9: 1.45, 10: 1.49, 11: 1.51, 12: 1.48, 13: 1.56,
            14: 1.57, 15: 1.59,
        }
        self.assertEqual(RANDOM_INDEX, expected)


class ComputeCiTests(SimpleTestCase):
    def test_formula(self):
        # lambda_max=3.1632345322678956, n=3 -> CI ~= 0.0816172661
        ci = AHPConsistencyService.compute_ci(3.1632345322678956, 3)
        self.assertAlmostEqual(ci, 0.0816172661, places=6)

    def test_perfectly_consistent_matrix_has_zero_ci(self):
        self.assertAlmostEqual(AHPConsistencyService.compute_ci(3.0, 3), 0.0, places=9)

    def test_n_less_or_equal_1_is_zero(self):
        self.assertEqual(AHPConsistencyService.compute_ci(5.0, 1), 0.0)


class ComputeCrTests(SimpleTestCase):
    def test_known_inconsistent_example(self):
        ci = 0.0816172661
        cr, ri = AHPConsistencyService.compute_cr(ci, 3)
        self.assertEqual(ri, 0.58)
        self.assertAlmostEqual(cr, 0.1407194244, places=6)

    def test_n_up_to_2_is_trivially_consistent(self):
        cr, ri = AHPConsistencyService.compute_cr(999.0, 2)
        self.assertEqual(ri, 0.0)
        self.assertEqual(cr, 0.0)

    def test_n_above_15_raises(self):
        with self.assertRaises(ValueError):
            AHPConsistencyService.compute_cr(0.1, 16)

    def test_n_below_1_raises(self):
        with self.assertRaises(ValueError):
            AHPConsistencyService.compute_cr(0.1, 0)


class IsConsistentBoundaryTests(SimpleTestCase):
    def test_exactly_at_threshold_passes(self):
        self.assertTrue(AHPConsistencyService.is_consistent(0.10))

    def test_just_above_threshold_fails(self):
        self.assertFalse(AHPConsistencyService.is_consistent(0.1000001))

    def test_well_below_threshold_passes(self):
        self.assertTrue(AHPConsistencyService.is_consistent(0.0))

    def test_known_inconsistent_example_fails(self):
        self.assertFalse(AHPConsistencyService.is_consistent(0.1407194244))
