"""FastAPI web app for the Lightsheet Simulator: serves the front end in static/ and the JSON API under /api.

Run with `python run_web.py` (http://127.0.0.1:8204, local only). `scripts/build_static.py` exports every path in
STATIC_ENDPOINTS to JSON for the GitHub Pages site, so keep that list in step with the GET routes below.

The simulator itself runs in the browser (static/pipeline.js, a port of web/pipeline.py). The API serves the parameter
specifications from sim_params.py, and Python reference results for the cross-check page.
"""
import logging
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from web.pipeline import MODES, build_sample, default_params, summary

import sim_params as sp  # noqa: E402  (web.pipeline put the repo root on sys.path)

logging.getLogger("simulator").setLevel(logging.WARNING)
STATIC = Path(__file__).resolve().parent / "static"
TITLE = "Lightsheet Simulator"
DESCRIPTION = ("A Python-based simulation tool for generating and visualizing 3D biological datasets, "
               "typically used in light-sheet microscopy.")

app = FastAPI(title=TITLE)
app.mount("/static", StaticFiles(directory=STATIC), name="static")

# Web-only controls: (min, max, step, default, unit, label). The rest come from sim_params.py (the desktop form).
WEB_SPECS = {
    "seed": (0, 9999, 1, 1, "", "Random seed (np.random.seed)"),
    "size_z": (8, 64, 1, sp.VOLUME_SIZE_ZYX[0], "voxels", "Volume depth z"),
    "size_yx": (20, 160, 2, sp.VOLUME_SIZE_ZYX[1], "voxels", "Volume height y and width x"),
    "blur_xy_um": (0, 5, 0.1, 0.5, "um", "Lateral blur sigma (x, y)"),
    "blur_z_um": (0, 8, 0.1, 1.5, "um", "Axial blur sigma (z, sheet thickness)"),
    "time_points": (1, 30, 1, sp.NUM_TIME_POINTS, "steps", "Time points"),
}

# Python reference runs for the cross-check page, at the desktop app's volume size.
CHECK_CASES = [
    {"mode": "cell", "seed": 1, "cell_type": "neuron"},
    {"mode": "cell", "seed": 2, "cell_type": "spherical", "voxel_um": [2.0, 0.5, 0.5], "cell_radius": 10},
    {"mode": "cell", "seed": 3, "cell_type": "epithelial"},
    {"mode": "cell", "seed": 4, "cell_type": "muscle", "cellular_structure": "Cell Membrane + Nucleus"},
    {"mode": "blobs", "seed": 5},
    {"mode": "diffusion", "seed": 6, "diffusion_coefficient": 0.5},
]


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/info")
def info():
    """Project summary and counts for the home page."""
    return {"title": TITLE, "version": "1", "description": DESCRIPTION, "cell_types": len(sp.CELL_TYPES),
            "structures": len(sp.STRUCTURES) - 1, "modes": len(MODES), "volume_zyx": list(sp.VOLUME_SIZE_ZYX),
            "voxels": int(sp.VOLUME_SIZE_ZYX[0] * sp.VOLUME_SIZE_ZYX[1] * sp.VOLUME_SIZE_ZYX[2])}


@app.get("/api/params")
def params():
    """Defaults, control specs (with units) and choices for the simulator page."""
    return {"defaults": default_params(), "modes": MODES, "cell_types": sp.CELL_TYPES,
            "structures": sp.STRUCTURES, "structure_specs": sp.spec_dict(sp.STRUCTURE_SPECS),
            "blob_specs": sp.spec_dict(sp.BLOB_SPECS), "dynamics_specs": sp.spec_dict(sp.DYNAMICS_SPECS),
            "web_specs": sp.spec_dict(WEB_SPECS),
            "blob": {"channels": sp.BLOB_CHANNELS, "intensity_range": sp.BLOB_INTENSITY_RANGE,
                     "sigma_range_voxels": sp.BLOB_SIGMA_RANGE}}


def _run(case):
    t = time.perf_counter()
    data, names, p = build_sample(case)
    return {"params": p, "shape": list(data.shape), "names": names, "summary": summary(data, names),
            "seconds": round(time.perf_counter() - t, 3)}


@app.get("/api/check")
def check():
    """Python reference results (per-channel sums, maxima, checksums) for the fixed cross-check cases."""
    return {"cases": [_run(c) for c in CHECK_CASES]}


@app.post("/api/check")
def check_custom(case: dict):
    """Python reference result for any parameter set (local app only; the static site has the fixed cases)."""
    if case.get("mode") not in MODES:
        raise HTTPException(400, f"mode must be one of {MODES}")
    size = case.get("size", sp.VOLUME_SIZE_ZYX)
    if len(size) != 3 or size[0] * size[1] * size[2] > 64 * 160 * 160:
        raise HTTPException(400, "size must be (z, y, x) with at most 64 x 160 x 160 voxels")
    try:
        return _run(case)
    except (ValueError, IndexError, KeyError) as e:
        raise HTTPException(400, str(e))


# GET paths (without the /api prefix) written to the static site as api/<path>.json.
STATIC_ENDPOINTS = ["/info", "/params", "/check"]
