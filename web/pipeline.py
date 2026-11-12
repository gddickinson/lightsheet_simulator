"""Seeded sample + acquisition pipeline shared by the web API, the JS cross-check and the engine fixture.

build_sample(params) seeds NumPy's legacy global RNG, builds the sample with the repo's own code and then applies the
acquisition step. The browser engine (static/*_engine.js) reproduces this draw for draw, so the same seed gives the same
volume in Python and JavaScript.

Sample modes (all volumes are (z, y, x) voxels; voxel_um is the voxel size in micrometres, (z, y, x)):
- "cell":      structure_pipeline.simulate_structures (BiologicalSimulator cell shape + membrane / nucleus / ER), T = 1.
- "blobs":     DataGenerator.generate_multi_channel_time_series (moving Gaussian blobs, 2 channels), noise_level = 0
               here because noise is added in the acquisition step.
- "diffusion": BiologicalSimulator.simulate_protein_diffusion from a point source at the volume centre.

Acquisition (the web interface's own step, built from the repo's functions; the desktop app has no PSF model):
blur with VolumeProcessor.apply_gaussian_filter using sigma = blur_um / voxel_um per axis (a Gaussian stand-in for the
optical PSF; the axial sigma plays the role of light-sheet thickness), then DataGenerator's noise model: additive
Gaussian noise of standard deviation `noise` and clipping to [0, 1].
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data_generator import DataGenerator, VolumeProcessor  # noqa: E402
from sim_params import (BLOB_CHANNELS, BLOB_INTENSITY_RANGE, BLOB_SIGMA_RANGE, BLOB_SPECS,  # noqa: E402
                        STRUCTURE_SPECS, VOLUME_SIZE_ZYX)
from simulator import BiologicalSimulator  # noqa: E402
from structure_pipeline import simulate_structures  # noqa: E402

MODES = ["cell", "blobs", "diffusion"]


def default_params():
    """Defaults: the desktop app's volume and form values, voxel size 1 um, illustrative acquisition settings."""
    p = {"mode": "cell", "seed": 1, "size": list(VOLUME_SIZE_ZYX), "voxel_um": [1.0, 1.0, 1.0],
         "cell_type": "neuron", "cellular_structure": "Cell Membrane + Nucleus + ER",
         "blur_xy_um": 0.5, "blur_z_um": 1.5, "noise": BLOB_SPECS["noise_level"][3],
         "diffusion_coefficient": 1.0, "time_points": 10}
    p.update({k: v[3] for k, v in STRUCTURE_SPECS.items() if k != "pixel_size"})
    p.update({k: v[3] for k, v in BLOB_SPECS.items() if k != "noise_level"})
    return p


def make_sample(p):
    """Noise-free sample: (data (T, C, z, y, x) float64, channel names). Uses the already-seeded global RNG."""
    size = tuple(int(s) for s in p["size"])
    if p["mode"] == "cell":
        params = dict(p, pixel_size=tuple(p["voxel_um"]))
        channels = simulate_structures(BiologicalSimulator(size, 1), params)
        if not channels:
            return np.zeros((1, 0, *size)), []
        return np.stack([v for _, v in channels])[np.newaxis].astype(float), [n for n, _ in channels]
    if p["mode"] == "blobs":
        data = DataGenerator().generate_multi_channel_time_series(
            num_volumes=int(p["num_volumes"]), num_channels=BLOB_CHANNELS, size=size, num_blobs=int(p["num_blobs"]),
            intensity_range=BLOB_INTENSITY_RANGE, sigma_range=BLOB_SIGMA_RANGE, noise_level=0.0,
            movement_speed=float(p["movement_speed"]))
        return data, [f"blobs {c + 1}" for c in range(BLOB_CHANNELS)]
    if p["mode"] == "diffusion":
        sim = BiologicalSimulator(size, int(p["time_points"]))
        ic = np.zeros(size)
        ic[tuple(s // 2 for s in size)] = 1.0
        return sim.simulate_protein_diffusion(float(p["diffusion_coefficient"]), ic)[:, np.newaxis], ["protein"]
    raise ValueError(f"unknown mode {p['mode']!r}")


def blur_sigma_voxels(p):
    """Gaussian sigma per axis (z, y, x) in voxels from the blur widths in micrometres."""
    vz, vy, vx = (float(v) for v in p["voxel_um"])
    return (float(p["blur_z_um"]) / vz, float(p["blur_xy_um"]) / vy, float(p["blur_xy_um"]) / vx)


def acquire(data, p):
    """Blur each (z, y, x) volume, then add Gaussian noise and clip to [0, 1] (in place on a copy)."""
    out = data.copy()
    sig = blur_sigma_voxels(p)
    if max(sig) > 0:
        vp = VolumeProcessor()
        for t in range(out.shape[0]):
            for c in range(out.shape[1]):
                out[t, c] = vp.apply_gaussian_filter(out[t, c], sig)
    if float(p["noise"]) > 0:
        out += np.random.normal(0, float(p["noise"]), out.shape)
        out = np.clip(out, 0, 1)
    return out


def build_sample(params=None):
    """Seed, build the sample and acquire it. Returns (data (T, C, z, y, x), channel names, merged params)."""
    p = default_params()
    p.update(params or {})
    np.random.seed(int(p["seed"]))
    data, names = make_sample(p)
    return acquire(data, p), names, p


def checksum(vol):
    """Position-weighted sum used to compare volumes compactly: sum(v * (1 + flat_index % 97))."""
    flat = np.asarray(vol, float).ravel()
    return float(np.sum(flat * (1 + np.arange(flat.size) % 97)))


def summary(data, names):
    """Per-channel stats of the first and last time point (for the cross-check page)."""
    out = []
    for c, n in enumerate(names):
        for t in sorted({0, data.shape[0] - 1}):
            v = data[t, c]
            out.append({"channel": n, "t": t, "sum": float(v.sum()), "max": float(v.max()),
                        "nonzero": int(np.count_nonzero(v)), "checksum": checksum(v)})
    return out
