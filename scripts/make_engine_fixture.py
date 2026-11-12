"""Reference numbers from the repo's Python code for the JS engine tests (web/static/engine.test.mjs).

Writes tests/fixtures/engine_fixture.json: NumPy RandomState draws, line_3d paths, scipy gaussian_filter and
binary_dilation outputs, and seeded samples built by web/pipeline.py (per-channel sums, checksums and sampled voxels).
tests/test_web.py recomputes it and checks the committed file is still current (with a tolerance, since libm differs
in the last digit between platforms).

Run: python scripts/make_engine_fixture.py [--check]
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy.ndimage import binary_dilation, gaussian_filter

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils import line_3d  # noqa: E402
from web.pipeline import build_sample, summary  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "engine_fixture.json"
SMALL = [12, 30, 30]
SAMPLE_CASES = [
    {"mode": "cell", "seed": 1, "cell_type": "spherical", "cell_radius": 8, "blur_xy_um": 0, "blur_z_um": 0, "noise": 0},
    {"mode": "cell", "seed": 2, "cell_type": "spherical", "cell_radius": 6, "membrane_thickness": 2,
     "voxel_um": [2.0, 0.5, 0.5], "blur_xy_um": 0, "blur_z_um": 0, "noise": 0},
    {"mode": "cell", "seed": 3, "cell_type": "neuron", "soma_radius": 4, "axon_length": 8, "axon_width": 2,
     "num_dendrites": 4, "dendrite_length": 9, "blur_xy_um": 0, "blur_z_um": 0, "noise": 0},
    {"mode": "cell", "seed": 11, "cell_type": "neuron", "soma_radius": 3, "axon_length": 10, "axon_width": 3,
     "num_dendrites": 6, "dendrite_length": 14, "membrane_thickness": 2, "voxel_um": [1.5, 1.0, 1.0],
     "blur_xy_um": 0.6, "blur_z_um": 2.0, "noise": 0.03},
    {"mode": "cell", "seed": 12, "cell_type": "neuron", "soma_radius": 3, "axon_length": 7, "axon_width": 2,
     "num_dendrites": 5, "dendrite_length": 8, "nucleus_radius": 2, "voxel_um": [2.0, 0.5, 0.6],
     "blur_xy_um": 0, "blur_z_um": 0, "noise": 0},
    {"mode": "cell", "seed": 4, "cell_type": "epithelial", "blur_xy_um": 0, "blur_z_um": 0, "noise": 0},
    {"mode": "cell", "seed": 5, "cell_type": "muscle", "cellular_structure": "Cell Membrane + Nucleus",
     "blur_xy_um": 1.0, "blur_z_um": 1.0, "noise": 0.02},
    {"mode": "blobs", "seed": 6, "num_volumes": 3, "num_blobs": 5, "movement_speed": 1.5,
     "blur_xy_um": 0.8, "blur_z_um": 1.2, "noise": 0.05},
    {"mode": "diffusion", "seed": 7, "time_points": 4, "diffusion_coefficient": 0.7,
     "blur_xy_um": 0.5, "blur_z_um": 1.0, "noise": 0.01},
]
PROBES = 40  # voxels sampled per channel volume


def probe_indices(n, k=PROBES):
    return [int(i) for i in np.linspace(0, n - 1, k).round()]


def sample_case(case):
    p = dict(case, size=case.get("size", SMALL))
    data, names, merged = build_sample(p)
    n = int(np.prod(data.shape[2:]))
    idx = probe_indices(n)
    probes = [[float(data[t, c].ravel()[i]) for i in idx] for t in range(data.shape[0]) for c in range(data.shape[1])]
    return {"params": merged, "shape": list(data.shape), "names": names, "summary": summary(data, names),
            "probe_index": idx, "probes": probes}


def make():
    np.random.seed(7)
    rng = {"seed": 7, "random": [float(v) for v in np.random.random_sample(8)],
           "randint": [int(np.random.randint(lo, hi)) for lo, hi in [(-3, 3), (0, 10), (-1, 1), (0, 1), (5, 6), (0, 1000)]],
           "uniform": [float(np.random.uniform(0, 2 * np.pi)) for _ in range(3)],
           "randn": [float(v) for v in np.random.randn(5)], "normal": [float(v) for v in np.random.normal(0, 0.5, 3)]}
    lines = [[list(c), [v.tolist() for v in line_3d(*c)]] for c in
             [(0, 0, 0, 10, 5, 0), (0, 0, 0, 10, 3, 7), (5, 5, 5, 0, 9, 1), (15, 50, 50, 27, 25, 50), (3, 3, 3, 3, 3, 3)]]
    np.random.seed(3)
    vol = np.random.rand(5, 6, 7)
    gauss = [{"sigma": s, "out": gaussian_filter(vol, s).ravel().tolist()} for s in [1.0, [0.5, 1.3, 2.2], [0, 0.7, 0], 3.0]]
    mask = np.zeros((5, 6, 7), bool)
    mask[2, 3, 3] = mask[0, 0, 6] = mask[4, 1, 2] = True
    dil = {"mask": mask.ravel().astype(int).tolist(),
           "out": {str(k): binary_dilation(mask, iterations=k).ravel().astype(int).tolist() for k in (1, 2, 3)}}
    return {"rng": rng, "lines": lines, "volume": {"dims": [5, 6, 7], "data": vol.ravel().tolist()},
            "gauss": gauss, "dilation": dil, "samples": [sample_case(c) for c in SAMPLE_CASES]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="compare with the committed fixture instead of writing")
    a = ap.parse_args()
    fx = make()
    if a.check:
        old = json.loads(FIXTURE.read_text())
        print("current" if np.allclose(_flat(old), _flat(fx), rtol=1e-9, atol=1e-12) else "STALE")
        return
    FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE.write_text(json.dumps(fx, separators=(",", ":")))
    print(f"wrote {FIXTURE} ({FIXTURE.stat().st_size / 1e3:.0f} kB)")


def _flat(obj):
    """All numbers in a nested JSON structure, in order (for tolerance comparisons)."""
    if isinstance(obj, bool):
        return [float(obj)]
    if isinstance(obj, (int, float)):
        return [float(obj)]
    if isinstance(obj, dict):
        return [x for k in sorted(obj) for x in _flat(obj[k])]
    if isinstance(obj, list):
        return [x for v in obj for x in _flat(v)]
    return []


if __name__ == "__main__":
    main()
