"""Regression tests for bugs fixed in the existing code (one class per fix; see SESSION_LOG.md)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pytest

from utils import line_3d


class TestLine3DReachesEndpoint:
    """line_3d doubled its error terms every step, so diagonal lines missed their end point."""

    CASES = [(0, 0, 0, 10, 5, 0), (0, 0, 0, 10, 3, 7), (0, 0, 0, 3, 10, 2), (5, 5, 5, 0, 9, 1),
             (0, 0, 0, 2, 2, 10), (20, 3, 7, 1, 15, 2)]

    @pytest.mark.parametrize("case", CASES)
    def test_endpoints_and_steps(self, case):
        x0, y0, z0, x1, y1, z1 = case
        x, y, z = line_3d(*case)
        assert (x[0], y[0], z[0]) == (x0, y0, z0)
        assert (x[-1], y[-1], z[-1]) == (x1, y1, z1)
        assert len(x) == max(abs(x1 - x0), abs(y1 - y0), abs(z1 - z0)) + 1
        steps = np.abs(np.diff(np.stack([x, y, z]), axis=1))
        assert steps.max() <= 1  # 26-connected: never jumps a voxel

    @pytest.mark.parametrize("case", CASES)
    def test_close_to_ideal_line(self, case):
        p0, p1 = np.array(case[:3], float), np.array(case[3:], float)
        pts = np.stack(line_3d(*case), axis=1).astype(float)
        d = p1 - p0
        t = (pts - p0) @ d / (d @ d)
        dist = np.linalg.norm(pts - (p0 + t[:, None] * d), axis=1)
        assert dist.max() <= 1.0


class TestDendritesStayInVolume:
    """Dendrite end points outside the volume raised IndexError (or wrapped round to the far side if negative)."""

    @pytest.mark.parametrize("seed", range(12))
    def test_long_dendrites(self, seed):
        from simulator import BiologicalSimulator
        size = (30, 100, 100)
        np.random.seed(seed)
        shape, interior, _ = BiologicalSimulator(size, 1).generate_cell_shape("neuron", size, dendrite_length=48)
        assert shape.shape == size and interior.sum() > 0

    def test_no_wraparound(self, monkeypatch):
        from simulator import BiologicalSimulator
        size = (12, 40, 40)
        # one dendrite pointing straight down -y from the soma (y=20) with length 30: its far end is at y=-10
        monkeypatch.setattr(np.random, "uniform", lambda *a, **k: 1.5 * np.pi)
        np.random.seed(0)
        _, interior, _ = BiologicalSimulator(size, 1).generate_cell_shape(
            "neuron", size, soma_radius=3, axon_length=10, axon_width=2, num_dendrites=1, dendrite_length=30)
        assert interior[:, :3, 18:23].sum() > 0  # the dendrite reaches the y=0 edge
        assert interior[:, 26:, :].sum() == 0  # and does not wrap round to the far y edge
