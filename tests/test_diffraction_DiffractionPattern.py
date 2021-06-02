import matplotlib
import numpy as np
import numpy.testing as npt
import pytest
import rowan

import freud

matplotlib.use("agg")


class TestDiffractionPattern:
    def test_compute(self):
        dp = freud.diffraction.DiffractionPattern()
        box, positions = freud.data.UnitCell.fcc().generate_system(4)
        dp.compute((box, positions))

    @pytest.mark.parametrize("reset", [True, False])
    def test_reset(self, reset):
        dp_check = freud.diffraction.DiffractionPattern()
        dp_reference = freud.diffraction.DiffractionPattern()
        fcc = freud.data.UnitCell.fcc()
        box, positions = fcc.generate_system(4)

        for seed in range(2):
            # The check instance computes twice without resetting
            box, positions = fcc.generate_system(sigma_noise=1e-3, seed=seed)
            dp_check.compute((box, positions), reset=reset)

        # The reference instance computes once on the last system
        dp_reference.compute((box, positions))

        # If reset, then the data should be close. If not reset, the data
        # should be different.
        assert reset == np.allclose(dp_check.diffraction, dp_reference.diffraction)

    def test_attribute_access(self):
        grid_size = 234
        output_size = 123
        dp = freud.diffraction.DiffractionPattern(grid_size=grid_size)
        assert dp.grid_size == grid_size
        assert dp.output_size == grid_size
        dp = freud.diffraction.DiffractionPattern(
            grid_size=grid_size, output_size=output_size
        )
        assert dp.grid_size == grid_size
        assert dp.output_size == output_size

        box, positions = freud.data.UnitCell.fcc().generate_system(4)

        with pytest.raises(AttributeError):
            dp.diffraction
        with pytest.raises(AttributeError):
            dp.k_values
        with pytest.raises(AttributeError):
            dp.k_vectors
        with pytest.raises(AttributeError):
            dp.plot()

        dp.compute((box, positions), zoom=1, peak_width=4)
        diff = dp.diffraction
        vals = dp.k_values
        vecs = dp.k_vectors
        dp.plot()
        dp._repr_png_()

        # Make sure old data is not invalidated by new call to compute()
        box2, positions2 = freud.data.UnitCell.bcc().generate_system(3)
        dp.compute((box2, positions2), zoom=1, peak_width=4)
        assert not np.array_equal(dp.diffraction, diff)
        assert not np.array_equal(dp.k_values, vals)
        assert not np.array_equal(dp.k_vectors, vecs)

    def test_attribute_shapes(self):
        grid_size = 234
        output_size = 123
        dp = freud.diffraction.DiffractionPattern(
            grid_size=grid_size, output_size=output_size
        )
        box, positions = freud.data.UnitCell.fcc().generate_system(4)
        dp.compute((box, positions))

        assert dp.diffraction.shape == (output_size, output_size)
        assert dp.k_values.shape == (output_size,)
        assert dp.k_vectors.shape == (output_size, output_size, 3)
        assert dp.to_image().shape == (output_size, output_size, 4)

    def test_center_unordered(self):
        """Assert the center of the image is an intensity peak for an
        unordered system.
        """
        box, positions = freud.data.make_random_system(box_size=10, num_points=1000)

        # Test different parities (odd/even) of grid_size and output_size
        for grid_size in [255, 256]:
            for output_size in [255, 256]:
                dp = freud.diffraction.DiffractionPattern(
                    grid_size=grid_size, output_size=output_size
                )

                # Use a random view orientation and a random zoom
                for view_orientation in rowan.random.rand(10):
                    zoom = 1 + 10 * np.random.rand()
                    dp.compute(
                        system=(box, positions),
                        view_orientation=view_orientation,
                        zoom=zoom,
                    )

                    # Assert the pixel at the center (k=0) is the maximum value
                    diff = dp.diffraction
                    max_index = np.unravel_index(np.argmax(diff), diff.shape)
                    center_index = (output_size // 2, output_size // 2)
                    assert max_index == center_index

                    # The value at k=0 should be 1 because of normalization
                    # by (number of points)**2
                    npt.assert_allclose(dp.diffraction[center_index], 1)

    def test_center_ordered(self):
        """Assert the center of the image is an intensity peak for an ordered
        system.
        """
        box, positions = freud.data.UnitCell.bcc().generate_system(10)

        # Test different parities (odd/even) of grid_size and output_size
        for grid_size in [255, 256]:
            for output_size in [255, 256]:
                dp = freud.diffraction.DiffractionPattern(
                    grid_size=grid_size, output_size=output_size
                )
                # Use a random view orientation and a random zoom
                for view_orientation in rowan.random.rand(10):
                    zoom = 1 + 10 * np.random.rand()
                    dp.compute(
                        system=(box, positions),
                        view_orientation=view_orientation,
                        zoom=zoom,
                    )

                    # Assert the pixel at the center (k=0) is the maximum value
                    diff = dp.diffraction
                    max_index = np.unravel_index(np.argmax(diff), diff.shape)
                    center_index = (output_size // 2, output_size // 2)
                    assert max_index == center_index

                    # The value at k=0 should be 1 because of normalization
                    # by (number of points)**2
                    npt.assert_allclose(dp.diffraction[center_index], 1)

    def test_repr(self):
        dp = freud.diffraction.DiffractionPattern()
        assert str(dp) == str(eval(repr(dp)))

        # Use non-default arguments for all parameters
        dp = freud.diffraction.DiffractionPattern(grid_size=123, output_size=234)
        assert str(dp) == str(eval(repr(dp)))

    def test_k_values_and_k_vectors(self):
        dp = freud.diffraction.DiffractionPattern()

        for size in [2, 5, 10]:
            # TODO: npoints doesn't actually matter, just use one point.
            for npoints in [10, 20, 75]:
                # TODO: This isn't using the correct signature for
                # make_random_system. Flip npoints and size.
                box, positions = freud.data.make_random_system(npoints, size)
                dp.compute((box, positions))

                output_size = dp.output_size
                npt.assert_allclose(dp.k_values[output_size // 2], 0)
                center_index = (output_size // 2, output_size // 2)
                npt.assert_allclose(dp.k_vectors[center_index], [0, 0, 0])
                # Add tests for the left and right bins. Use the math for
                # fftfreq and the _k_scale_factor to write an expression for
                # the first and last bins' k-values and k-vectors.

    def test_cubic_system(self):
        box, positions = freud.data.UnitCell.sc().generate_system(10)
        dp = freud.diffraction.DiffractionPattern()
        dp.compute((box, positions))
        # Make sure that the peaks are where we expect them.
        # Identify the indices of the highest values in dp.diffraction
        # and test that k * R == 2*pi*N for some integer N, all peak vectors k,
        # and lattice vectors R. This will be inexact because of binning.
        # Perhaps try with a larger resolution like 1024.
        # Use npt.assert_allclose.

    def test_cubic_system_parameterized(self):
        pass
        # Second PR: Same as above test but with different grid_size,
        # output_size, and zoom values.
        for grid_size in (256, 1024):
            for output_size in (255, 256, 1023, 1024):
                for zoom in (1, 2.5, 4):
                    # Ensure that peaks are in the correct locations like above.
                    # Identify the indices of the highest values in
                    # dp.diffraction and test that k * R == 2*pi*N for some
                    # integer N, all peak vectors k, and lattice vectors R.
                    pass
