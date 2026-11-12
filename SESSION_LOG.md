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

**Needs George's decision**: answered by George (2026-11-11, "fix ... any other problems"); see the next entry.

## 2026-11-11 (later) — follow-up fixes requested by George (branch `web-interface`)

Each in `simulator.py` / `data_generator.py`, the original monolith (which now shares these methods with the modules
instead of keeping its own copies) and the JS engine, with regression tests and a "Fix ..." commit:
1. Nucleus radius: the viewer's max(5, min(r, soma//2)) rule and generate_nucleus's (min(size)//4)//3 cap are gone;
   the form value (µm, range now 1-30) is used and the nucleus is clipped to the cell interior. find_suitable_center
   measures the fit in µm. (The monolith's own find_suitable_center also overwrote its search-distance map.)
2. simulate_angular_recording / correct_angular_recording rotate only spatial axes (first two of the last three);
   4-D data unchanged, 5-D channels no longer mixed with z. Not ported to JS (not part of the web simulator).
3. Neuron axon length/width and dendrite length are µm, converted with the voxel size; the form row reads
   "Pixel size (µm; z, y, x)" with boxes in that order, and radius/length fields show µm.
Fixture regenerated (new anisotropic neuron case): node test 2151 checks, pytest 75 passed, browser cross-check 17/17,
static and server smoke tests ok; both desktop apps run Simulate offscreen for every cell type.

Still open (not asked): membrane thickness is µm for spherical/muscle but dilation steps for neurons and voxels for
epithelial cells; find_suitable_center tries the farthest candidates first; gui/viewer.py (964 lines) and
simulateLightSheetData.py (~2650) exceed the 500-line rule.
