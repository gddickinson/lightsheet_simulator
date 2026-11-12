# Lightsheet Simulator - Interface Map

## Module Overview

| File | Purpose |
|------|---------|
| `simulateLightSheetData.py` | Original monolithic file (kept for backward compat); contains `main()` entry point |
| `utils.py` | Utility functions: `line_3d()` Bresenham 3D line algorithm |
| `sim_params.py` | Qt-free parameter specs (ranges, defaults, units), cell types, structure choices, volume size |
| `structure_pipeline.py` | Qt-free `simulate_structures()` (cell shape -> membrane / nucleus / ER channels), used by the viewer and the web |
| `simulator.py` | `BiologicalSimulator` class: cell shapes, organelles, diffusion, calcium signals |
| `data_generator.py` | `DataGenerator` (synthetic volume/time-series, I/O) and `VolumeProcessor` (filter, stats) |
| `blob_analysis.py` | `BlobAnalyzer` (statistics, colocalization) + Qt dialogs: `BlobAnalysisDialog`, `BlobResultsDialog`, `TimeSeriesDialog` |
| `gui/__init__.py` | GUI package re-exports |
| `gui/simulation_widgets.py` | `BiologicalSimulationWidget` (parameter form) + `BiologicalSimulationWindow` |
| `gui/roi.py` | `ROI3D` OpenGL mesh item |
| `gui/viewer.py` | `LightsheetViewer` main application window (docks, 2D/3D views, blob detection, playback) |
| `tests/test_simulator.py` | Smoke tests for `BiologicalSimulator`, `DataGenerator`, `VolumeProcessor`, `line_3d` |
| `tests/test_regressions.py` | Regression tests for fixed bugs (line_3d, dendrite bounds, pixel-size order, cell-shape broadcasting) |
| `tests/test_web.py` | Web API, static build, fixture currency, TIFF export round trip, node engine tests |
| `tests/fixtures/engine_fixture.json` | Python reference values for the JS engine (from `scripts/make_engine_fixture.py`) |
| `web/app.py` | FastAPI app: `/api/info`, `/api/params`, `/api/check` (GET + POST), `STATIC_ENDPOINTS` |
| `web/pipeline.py` | Seeded `build_sample()` (cell / blobs / diffusion) + `acquire()` (blur + noise), `summary()`, `checksum()` |
| `web/static/` | Front end (no build): `main.js`, `core.js`, pages `home.js` `sim.js` `check.js` `about.js`, `sim_controls.js`, `render.js` (ortho views, MIP), `tiff.js` (ImageJ TIFF writer), `worker.js` + `sample_runner.js` |
| `web/static/*engine*.js`, `np_random.js`, `ndimage.js`, `pipeline.js` | JS port: NumPy RandomState (MT19937), gaussian_filter / binary_dilation, cell shapes, blobs, diffusion; `engine.test.mjs` |
| `scripts/build_static.py`, `scripts/screenshots.py`, `scripts/make_engine_fixture.py` | Static export, browser smoke test / README images, fixture generator |
| `run_web.py` | Starts the web app on 127.0.0.1:8204 |

## Key Classes

- **`BiologicalSimulator`** (`simulator.py`): Generates cell shapes (spherical, neuron, epithelial, muscle), nucleus, ER, protein diffusion, calcium signals.
- **`DataGenerator`** (`data_generator.py`): Creates synthetic fluorescence volumes and multi-channel time-series with moving blobs. Handles TIFF/NPY I/O.
- **`VolumeProcessor`** (`data_generator.py`): Threshold, Gaussian filter, basic statistics.
- **`BlobAnalyzer`** (`blob_analysis.py`): Nearest-neighbor distances, density, colocalization (basic + Manders/Pearson).
- **`LightsheetViewer`** (`gui/viewer.py`): Main QMainWindow with XY/XZ/YZ slice views, 3D scatter view, blob detection, playback.

## Module Dependencies

```
simulateLightSheetData.py  (original monolith, standalone)

gui/viewer.py
  -> structure_pipeline.py, sim_params.py
  -> simulator.py -> utils.py
  -> data_generator.py
  -> blob_analysis.py
  -> gui/simulation_widgets.py
  -> gui/roi.py (not yet used in viewer, available for future use)

web/app.py -> web/pipeline.py -> structure_pipeline.py, data_generator.py, simulator.py, sim_params.py
web/static/pipeline.js -> np_random.js, ndimage.js, cells_engine.js, dynamics_engine.js  (mirror of web/pipeline.py)
```

Note: `simulateLightSheetData.py` keeps its own copies of the classes (it imports only `line_3d` from `utils.py`);
bug fixes are applied to both copies.
