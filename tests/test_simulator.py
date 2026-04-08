"""
Smoke tests for the BiologicalSimulator and DataGenerator core classes.
These tests verify basic functionality without requiring a GUI.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pytest

from simulator import BiologicalSimulator
from data_generator import DataGenerator, VolumeProcessor
from utils import line_3d


class TestLine3D:
    def test_same_point(self):
        x, y, z = line_3d(5, 5, 5, 5, 5, 5)
        assert len(x) == 1
        assert x[0] == 5

    def test_straight_line(self):
        x, y, z = line_3d(0, 0, 0, 10, 0, 0)
        assert len(x) == 11
        assert x[0] == 0
        assert x[-1] == 10
        np.testing.assert_array_equal(y, np.zeros(11, dtype=int))

    def test_returns_numpy_arrays(self):
        x, y, z = line_3d(0, 0, 0, 3, 4, 5)
        assert isinstance(x, np.ndarray)
        assert isinstance(y, np.ndarray)
        assert isinstance(z, np.ndarray)


class TestBiologicalSimulator:
    def setup_method(self):
        self.sim = BiologicalSimulator(size=(20, 30, 30), num_time_points=3)

    def test_init(self):
        assert self.sim.size == (20, 30, 30)
        assert self.sim.num_time_points == 3

    def test_protein_diffusion_shape(self):
        ic = np.zeros((20, 30, 30))
        ic[10, 15, 15] = 1.0
        result = self.sim.simulate_protein_diffusion(D=0.5, initial_concentration=ic)
        assert result.shape == (3, 20, 30, 30)

    def test_protein_diffusion_shape_mismatch(self):
        ic = np.zeros((10, 10, 10))
        with pytest.raises(ValueError):
            self.sim.simulate_protein_diffusion(D=0.5, initial_concentration=ic)

    def test_active_transport_shape(self):
        cargo = np.random.rand(20, 30, 30)
        result = self.sim.simulate_active_transport((1, 0, 0), cargo)
        assert result.shape == (3, 20, 30, 30)

    def test_generate_cell_membrane(self):
        mem = self.sim.generate_cell_membrane(center=(10, 15, 15), radius=5, thickness=1)
        assert mem.shape == (20, 30, 30)
        assert np.any(mem > 0)

    def test_generate_cell_shape_spherical(self):
        shape, interior, membrane = self.sim.generate_cell_shape(
            "spherical", (20, 30, 30), cell_radius=8
        )
        assert shape.shape == (20, 30, 30)
        assert np.any(interior > 0)
        assert np.any(membrane > 0)

    def test_generate_cell_shape_unknown(self):
        with pytest.raises(ValueError):
            self.sim.generate_cell_shape("unknown_type", (20, 30, 30))


class TestDataGenerator:
    def setup_method(self):
        self.gen = DataGenerator()

    def test_generate_volume(self):
        vol = self.gen.generate_volume(size=(20, 20, 10), num_blobs=5)
        assert vol.shape == (20, 20, 10)
        assert vol.min() >= 0
        assert vol.max() <= 1

    def test_generate_multi_channel_volume(self):
        vol = self.gen.generate_multi_channel_volume(
            size=(20, 20, 10), num_channels=2, num_blobs=5
        )
        assert vol.shape == (2, 20, 20, 10)

    def test_generate_time_series(self):
        ts = self.gen.generate_time_series(
            num_volumes=3, size=(10, 10, 10), num_blobs=3
        )
        assert ts.shape == (3, 10, 10, 10)
        assert self.gen.data is not None

    def test_generate_multi_channel_time_series(self):
        ts = self.gen.generate_multi_channel_time_series(
            num_volumes=2, num_channels=2, size=(10, 20, 20), num_blobs=5
        )
        assert ts.shape == (2, 2, 10, 20, 20)

    def test_metadata(self):
        self.gen.generate_volume(size=(10, 10, 10))
        self.gen.data = self.gen.generate_volume(size=(10, 10, 10))
        meta = self.gen.get_metadata()
        assert "shape" in meta
        assert "mean" in meta

    def test_no_data_metadata(self):
        assert self.gen.get_metadata() == {}


class TestVolumeProcessor:
    def test_threshold(self):
        vp = VolumeProcessor()
        data = np.array([0.1, 0.5, 0.9])
        result = vp.apply_threshold(data, 0.4)
        np.testing.assert_array_equal(result, [0, 0.5, 0.9])

    def test_statistics(self):
        vp = VolumeProcessor()
        data = np.array([1.0, 2.0, 3.0])
        stats = vp.calculate_statistics(data)
        assert stats["mean"] == 2.0
        assert stats["min"] == 1.0
        assert stats["max"] == 3.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
