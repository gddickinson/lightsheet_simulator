# Session log

## 2026-11-11 — Web interface, static GitHub Pages site, bug fixes (branch `web-interface`)

**Bugs fixed in existing code** (each its own commit, with a regression test in `tests/test_regressions.py`):
1. `utils.line_3d` doubled its error terms each step, so diagonal lines missed their end point (neuron dendrites
   pointed the wrong way). Replaced by a standard 3D Bresenham; the monolith imports it from `utils.py`.
2. Neuron dendrites ending outside the volume raised IndexError (or wrapped round when negative); now clipped.
3. The simulation form sent pixel size as (x, y, z) but the simulator reads (z, y, x); now (z, y, x) in both GUIs.
4. Epithelial / muscle cell masks came back as (z,1,1) / (z,y,1) arrays, so Simulate with nucleus/ER failed; now
   broadcast to the full volume. In the monolith these two types also raised UnboundLocalError; fixed.

**Refactor**: `sim_params.py` (form specs with units) and `structure_pipeline.py` (the viewer's Simulate logic) are
Qt-free modules the GUI imports back; checked offscreen that the viewer still generates data and runs Simulate.

**Web**: FastAPI app (`web/app.py`, port 8204), static site via `scripts/build_static.py` and
`.github/workflows/pages.yml`. The simulator runs in the browser: JS port of NumPy's legacy RandomState, scipy
gaussian_filter / binary_dilation, cell shapes, nucleus, ER, moving blobs and protein diffusion, plus a web-only
acquisition step (Gaussian blur in µm, additive Gaussian noise). Seeded volumes match Python voxel for voxel
(node test: 2022 checks; browser cross-check: 17/17 channel volumes at 30x100x100, rel. diff ~1e-14). Exports:
PNG of the XY view, ImageJ float32 TIFF with voxel size (verified with tifffile). Worker thread; default volume builds
in 0.1-0.6 s.

**Needs George's decision** (not changed):
- Nucleus radius: the viewer asks max(5, min(r, soma//2)), then `generate_nucleus` caps it at (min(size)//4)//3 = 2 at
  the default volume, so the form's nucleus radius barely matters, and `generate_er` excludes the uncapped radius.
- `simulate_angular_recording` rotates axes (1, 2); for the GUI's 5D (t, c, z, y, x) data that mixes channels with z.
  Which spatial axes the rotation should use is unclear (the 4D generators use mixed axis orders).
- `find_suitable_center` sorts candidates farthest-first (argsort of -distance), probably meant nearest-first;
  effect is small (candidates are within one voxel of the same radius).
- Units: the form's "Pixel Size" has no unit (web treats it as µm); radii are in physical units, axon/dendrite
  lengths in voxels, neuron membrane thickness in dilation steps.
- `gui/viewer.py` (964 lines) and `simulateLightSheetData.py` (~2900) exceed the 500-line rule (pre-existing).
