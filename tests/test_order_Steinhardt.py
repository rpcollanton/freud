import numpy as np
import numpy.testing as npt
import freud
import rowan
import unittest
import util

# Validated against manual calculation and pyboo
PERFECT_FCC_Q6 = 0.57452416
PERFECT_FCC_W6 = -0.00262604


class TestSteinhardt(unittest.TestCase):
    def test_shape(self):
        N = 1000
        L = 10

        box, positions = util.make_box_and_random_points(L, N)

        comp = freud.order.Steinhardt(6)
        comp.compute(box, positions, query_args={'r_max': 1.5})

        npt.assert_equal(comp.order.shape[0], N)

    def test_identical_environments_Ql(self):
        (box, positions) = util.make_fcc(4, 4, 4)
        r_max = 1.5
        test_set = util.make_raw_query_nlist_test_set(
            box, positions, positions, 'ball', r_max, 0, True)
        for ts in test_set:
            comp = freud.order.Steinhardt(6)
            comp.compute(box, ts[0], nlist=ts[1], query_args=ts[2])
            npt.assert_allclose(
                np.average(comp.order), PERFECT_FCC_Q6, atol=1e-5)
            npt.assert_allclose(comp.order, comp.order[0], atol=1e-5)
            self.assertAlmostEqual(comp.norm, PERFECT_FCC_Q6, delta=1e-5)

            comp = freud.order.Steinhardt(6, average=True)
            comp.compute(box, ts[0], nlist=ts[1], query_args=ts[2])
            npt.assert_allclose(
                np.average(comp.order), PERFECT_FCC_Q6, atol=1e-5)
            npt.assert_allclose(comp.order, comp.order[0], atol=1e-5)
            self.assertAlmostEqual(comp.norm, PERFECT_FCC_Q6, delta=1e-5)

    def test_identical_environments_Ql_near(self):
        (box, positions) = util.make_fcc(4, 4, 4)

        r_max = 1.5
        n = 12
        test_set = util.make_raw_query_nlist_test_set(
            box, positions, positions, 'nearest', r_max, n, True)
        for ts in test_set:
            comp = freud.order.Steinhardt(6)
            comp.compute(box, ts[0], nlist=ts[1], query_args=ts[2])
            npt.assert_allclose(
                np.average(comp.order), PERFECT_FCC_Q6, atol=1e-5)
            npt.assert_allclose(comp.order, comp.order[0], atol=1e-5)
            self.assertAlmostEqual(comp.norm, PERFECT_FCC_Q6, delta=1e-5)

            comp = freud.order.Steinhardt(6, average=True)
            comp.compute(box, ts[0], nlist=ts[1], query_args=ts[2])
            npt.assert_allclose(
                np.average(comp.order), PERFECT_FCC_Q6, atol=1e-5)
            npt.assert_allclose(comp.order, comp.order[0], atol=1e-5)
            self.assertAlmostEqual(comp.norm, PERFECT_FCC_Q6, delta=1e-5)

        # Perturb one position
        perturbed_positions = positions.copy()
        perturbed_positions[-1] += [0.1, 0, 0]

        test_set = util.make_raw_query_nlist_test_set(
            box, perturbed_positions, perturbed_positions,
            'nearest', r_max, n, True)
        # Ensure exactly 13 values change for the perturbed system
        for ts in test_set:
            comp = freud.order.Steinhardt(6)
            comp.compute(box, ts[0], nlist=ts[1], query_args=ts[2])
            self.assertEqual(
                sum(~np.isclose(comp.Ql, PERFECT_FCC_Q6, rtol=1e-6)), 13)

            # More than 13 particles should change for
            # Ql averaged over neighbors
            comp = freud.order.Steinhardt(6, average=True)
            comp.compute(box, ts[0], nlist=ts[1], query_args=ts[2])
            self.assertGreater(
                sum(~np.isclose(comp.order, PERFECT_FCC_Q6, rtol=1e-6)), 13)

    def test_identical_environments_Wl(self):
        (box, positions) = util.make_fcc(4, 4, 4)

        r_max = 1.5
        test_set = util.make_raw_query_nlist_test_set(
            box, positions, positions, 'ball', r_max, 0, True)
        for ts in test_set:
            comp = freud.order.Steinhardt(6, Wl=True)
            comp.compute(box, ts[0], nlist=ts[1], query_args=ts[2])
            npt.assert_allclose(
                np.average(comp.order), PERFECT_FCC_W6, atol=1e-5)
            npt.assert_allclose(comp.order, comp.order[0], atol=1e-5)
            self.assertAlmostEqual(comp.norm, PERFECT_FCC_W6, delta=1e-5)

            comp = freud.order.Steinhardt(6, Wl=True, average=True)
            comp.compute(box, ts[0], nlist=ts[1], query_args=ts[2])
            npt.assert_allclose(
                np.average(comp.order), PERFECT_FCC_W6, atol=1e-5)
            npt.assert_allclose(comp.order, comp.order[0], atol=1e-5)
            self.assertAlmostEqual(comp.norm, PERFECT_FCC_W6, delta=1e-5)

        self.assertEqual(len(positions), comp.num_particles)

    def test_identical_environments_Wl_near(self):
        (box, positions) = util.make_fcc(4, 4, 4)
        r_max = 1.5
        n = 12
        test_set = util.make_raw_query_nlist_test_set(
            box, positions, positions, 'nearest', r_max, n, True)
        for ts in test_set:
            comp = freud.order.Steinhardt(6, Wl=True)
            comp.compute(box, ts[0], nlist=ts[1], query_args=ts[2])
            npt.assert_allclose(
                np.real(np.average(comp.order)), PERFECT_FCC_W6, atol=1e-5)
            npt.assert_allclose(comp.order, comp.order[0], atol=1e-5)
            self.assertAlmostEqual(
                np.real(comp.norm), PERFECT_FCC_W6, delta=1e-5)

            comp = freud.order.Steinhardt(6, Wl=True, average=True)
            comp.compute(box, ts[0], nlist=ts[1], query_args=ts[2])
            npt.assert_allclose(
                np.real(np.average(comp.order)), PERFECT_FCC_W6, atol=1e-5)
            npt.assert_allclose(comp.order, comp.order[0], atol=1e-5)
            self.assertAlmostEqual(
                np.real(comp.norm), PERFECT_FCC_W6, delta=1e-5)

            self.assertEqual(len(positions), comp.num_particles)

    def test_weighted(self):
        (box, positions) = util.make_fcc(4, 4, 4)
        r_max = 1.5
        n = 12
        test_set = util.make_raw_query_nlist_test_set(
            box, positions, positions, 'nearest', r_max, n, True)

        # Skip test sets without an explicit neighbor list
        for ts in filter(lambda ts: ts[1] is not None, test_set):
            nlist = ts[1]

            for wt in [0, 0.1, 0.9, 1.1, 10, 1e6]:
                # Change the weight of the first bond for each particle
                weights = nlist.weights.copy()
                weights[nlist.segments] = wt
                weighted_nlist = freud.locality.NeighborList.from_arrays(
                    len(positions), len(positions),
                    nlist.query_point_index,
                    nlist.point_index,
                    nlist.distances,
                    weights)

                comp = freud.order.Steinhardt(6, weighted=True)
                comp.compute(box, ts[0], nlist=weighted_nlist)

                # Unequal neighbor weighting in a perfect FCC structure
                # appears to increase the Q6 order parameter
                npt.assert_array_less(PERFECT_FCC_Q6, comp.order)
                npt.assert_allclose(comp.order, comp.order[0], atol=1e-5)
                npt.assert_array_less(PERFECT_FCC_Q6, comp.norm)

                # Ensure that W6 values are altered by changing the weights
                comp = freud.order.Steinhardt(6, Wl=True, weighted=True)
                comp.compute(box, ts[0], nlist=weighted_nlist)
                with self.assertRaises(AssertionError):
                    npt.assert_allclose(
                        np.real(np.average(comp.order)),
                        PERFECT_FCC_W6, rtol=1e-5)
                with self.assertRaises(AssertionError):
                    npt.assert_allclose(
                        np.real(comp.norm), PERFECT_FCC_W6, rtol=1e-5)

            self.assertEqual(len(positions), comp.num_particles)

    def test_attribute_access(self):
        comp = freud.order.Steinhardt(6)

        with self.assertRaises(AttributeError):
            comp.norm
        with self.assertRaises(AttributeError):
            comp.order

        (box, positions) = util.make_fcc(4, 4, 4)
        comp.compute(box, positions, query_args={'r_max': 1.5})

        comp.norm
        comp.order

    def test_compute_twice_norm(self):
        """Test that computing norm twice works as expected."""
        L = 5
        num_points = 100
        box, points = util.make_box_and_random_points(L, num_points, seed=0)

        st = freud.order.Steinhardt(6)
        first_result = st.compute(box, points, query_args={'r_max': 1.5}).norm
        second_result = st.compute(box, points, query_args={'r_max': 1.5}).norm

        npt.assert_array_almost_equal(first_result, second_result)

    def test_rotational_invariance(self):
        box = freud.box.Box.cube(10)
        positions = np.array([[0, 0, 0],
                              [-1, -1, 0],
                              [-1, 1, 0],
                              [1, -1, 0],
                              [1, 1, 0],
                              [-1, 0, -1],
                              [-1, 0, 1],
                              [1, 0, -1],
                              [1, 0, 1],
                              [0, -1, -1],
                              [0, -1, 1],
                              [0, 1, -1],
                              [0, 1, 1]])
        query_point_index = np.zeros(12)
        point_index = np.arange(1, 13)
        nlist = freud.locality.NeighborList.from_arrays(
            13, 13, query_point_index, point_index, np.full(12, np.sqrt(2)))

        q6 = freud.order.Steinhardt(6)
        w6 = freud.order.Steinhardt(6, Wl=True)

        q6.compute(box, positions, nlist=nlist)
        q6_unrotated_order = q6.order[0]
        w6.compute(box, positions, nlist=nlist)
        w6_unrotated_order = w6.order[0]

        for i in range(10):
            np.random.seed(i)
            quat = rowan.random.rand()
            positions_rotated = rowan.rotate(quat, positions)

            # Ensure Q6 is rotationally invariant
            q6.compute(box, positions_rotated, nlist=nlist)
            npt.assert_allclose(q6.order[0], q6_unrotated_order, rtol=1e-5)
            npt.assert_allclose(q6.order[0], PERFECT_FCC_Q6, rtol=1e-5)

            # Ensure W6 is rotationally invariant
            w6.compute(box, positions_rotated, nlist=nlist)
            npt.assert_allclose(w6.order[0], w6_unrotated_order, rtol=1e-5)
            npt.assert_allclose(w6.order[0], PERFECT_FCC_W6, rtol=1e-5)

    def test_repr(self):
        comp = freud.order.Steinhardt(6)
        self.assertEqual(str(comp), str(eval(repr(comp))))
        # Use non-default arguments for all parameters
        comp = freud.order.Steinhardt(6, average=True, Wl=True, weighted=True)
        self.assertEqual(str(comp), str(eval(repr(comp))))


if __name__ == '__main__':
    unittest.main()
