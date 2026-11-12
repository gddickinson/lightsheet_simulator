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


class TestPixelSizeOrder:
    """The simulation form sent pixel size as (x, y, z) but the simulator reads it as (z, y, x)."""

    @pytest.fixture(scope="class")
    def qapp(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        pytest.importorskip("PyQt5")
        from PyQt5.QtWidgets import QApplication
        return QApplication.instance() or QApplication([])

    @pytest.mark.parametrize("module", ["gui.simulation_widgets", "simulateLightSheetData"])
    def test_emitted_order_is_zyx(self, qapp, module):
        import importlib
        mod = importlib.import_module(module)
        w = mod.BiologicalSimulationWidget()
        w.pixel_size_x.setValue(0.3)
        w.pixel_size_y.setValue(0.4)
        w.pixel_size_z.setValue(2.0)
        got = []
        w.simulationRequested.connect(got.append)
        w.simulate_button.click()
        assert tuple(got[0]["pixel_size"]) == pytest.approx((2.0, 0.4, 0.3))


class TestCellShapesFillTheVolume:
    """Epithelial and muscle shapes came back as (z,1,1) / (z,y,1) arrays, so stacking them with the nucleus/ER
    channels failed ("all input arrays must have the same shape") and the desktop Simulate showed an error."""

    def _simulators(self):
        from simulator import BiologicalSimulator
        sims = [BiologicalSimulator]
        try:
            os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
            import simulateLightSheetData
            sims.append(simulateLightSheetData.BiologicalSimulator)
        except ImportError:
            pass
        return sims

    @pytest.mark.parametrize("cell_type", ["spherical", "neuron", "epithelial", "muscle"])
    def test_full_shape(self, cell_type):
        size = (12, 30, 30)
        for cls in self._simulators():
            np.random.seed(0)
            arrays = cls(size, 1).generate_cell_shape(cell_type, size, cell_radius=8, soma_radius=4,
                                                      axon_length=8, dendrite_length=9)
            for a in arrays:
                assert a.shape == size, (cls.__module__, cell_type, a.shape)

    def test_pipeline_stacks_all_structures(self):
        from simulator import BiologicalSimulator
        from structure_pipeline import simulate_structures, stack_channels
        params = {"cellular_structure": "Cell Membrane + Nucleus + ER", "cell_type": "epithelial",
                  "pixel_size": (1, 1, 1), "membrane_thickness": 1, "cell_radius": 8, "soma_radius": 5,
                  "axon_length": 10, "axon_width": 2, "num_dendrites": 3, "dendrite_length": 8,
                  "nucleus_radius": 3, "er_density": 0.1}
        np.random.seed(0)
        assert stack_channels(simulate_structures(BiologicalSimulator((12, 30, 30), 1), params), 2).shape == (2, 3, 12, 30, 30)


def _monolith():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        import simulateLightSheetData
        return simulateLightSheetData
    except ImportError:
        return None


def _struct_params(**kw):
    p = {"cellular_structure": "Cell Membrane + Nucleus", "cell_type": "spherical", "pixel_size": (1, 1, 1),
         "membrane_thickness": 1, "cell_radius": 20, "soma_radius": 5, "axon_length": 50, "axon_width": 2,
         "num_dendrites": 5, "dendrite_length": 25, "nucleus_radius": 3, "er_density": 0.1}
    p.update(kw)
    return p


class TestNucleusRadiusTakesEffect:
    """The nucleus radius was forced to max(5, min(r, soma_radius // 2)) by the viewer and then capped at
    (min(volume) // 4) // 3 = 2 by generate_nucleus, so the form value had almost no effect."""

    @pytest.mark.parametrize("r", [3, 6, 9])
    def test_radius_used(self, r):
        from simulator import BiologicalSimulator
        from structure_pipeline import nucleus_radius_used, simulate_structures
        assert nucleus_radius_used(_struct_params(nucleus_radius=r)) == r
        sims = [BiologicalSimulator] + ([_monolith().BiologicalSimulator] if _monolith() else [])
        for cls in sims:
            np.random.seed(0)
            ch = dict(simulate_structures(cls((30, 100, 100), 1), _struct_params(nucleus_radius=r)))
            vol = ch["nucleus"].sum()
            assert abs(vol - 4 / 3 * np.pi * r ** 3) < 0.35 * 4 / 3 * np.pi * r ** 3, (cls.__module__, r, vol)

    def test_limited_by_the_cell(self):
        from simulator import BiologicalSimulator
        size = (30, 100, 100)
        _, interior, _ = BiologicalSimulator(size, 1).generate_cell_shape("spherical", size, cell_radius=6)
        nuc, _ = BiologicalSimulator(size, 1).generate_nucleus(interior, (15, 50, 50), 30)
        assert nuc.sum() == interior.sum()  # a nucleus bigger than the cell fills the interior, never more

    def test_anisotropic_voxels_in_um(self):
        from simulator import BiologicalSimulator
        size = (30, 60, 60)
        sim = BiologicalSimulator(size, 1)
        px = (2.0, 0.5, 0.5)
        _, interior, _ = sim.generate_cell_shape("spherical", size, px, cell_radius=14)
        nuc, c = sim.generate_nucleus(interior, (15, 30, 30), 5, pixel_size=px)
        zz, yy, xx = np.nonzero(nuc)
        assert (zz.max() - zz.min() + 1) * 2.0 == pytest.approx(10, abs=2.1)   # 5 um radius along z (2 um voxels)
        assert (xx.max() - xx.min() + 1) * 0.5 == pytest.approx(10, abs=0.6)   # and along x (0.5 um voxels)


class TestAngularRecordingSpatialOnly:
    """simulate_angular_recording rotated axes (1, 2); for the GUI's (t, c, z, y, x) data that rotated the channel
    axis against z, mixing channels."""

    def _gens(self):
        from data_generator import DataGenerator
        gens = [DataGenerator]
        if _monolith():
            gens.append(_monolith().DataGenerator)
        return gens

    @pytest.mark.parametrize("method", ["simulate_angular_recording", "correct_angular_recording"])
    def test_channels_not_mixed(self, method):
        data = np.zeros((2, 2, 12, 16, 16))
        data[:, 0, 4:8, 6:10, 6:10] = 1.0  # channel 1 empty
        for cls in self._gens():
            g = cls()
            g.data = data
            out = getattr(g, method)(30)
            assert out.shape == data.shape
            assert np.abs(out[:, 1]).max() == 0, cls.__module__
            assert out[:, 0].sum() > 0

    def test_spatial_plane_and_4d_unchanged(self):
        from scipy.ndimage import rotate
        rng = np.random.default_rng(1)
        d5 = rng.random((2, 3, 8, 10, 12))
        d4 = d5[:, 0]
        for cls in self._gens():
            g = cls()
            g.data = d4
            np.testing.assert_allclose(g.simulate_angular_recording(20),
                                       rotate(d4, 20, axes=(1, 2), reshape=False, mode="constant", cval=0))
            g.data = d5
            out = g.simulate_angular_recording(20)
            for c in range(3):  # each channel rotated in the same (z, y) plane as 4D data
                np.testing.assert_allclose(out[:, c], rotate(d5[:, c], 20, axes=(1, 2), reshape=False,
                                                             mode="constant", cval=0))
