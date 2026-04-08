# Biological Light Sheet Data Simulator — Roadmap

## Current State
Functional PyQt5+pyqtgraph application for generating synthetic 3D biological datasets. The entire application lives in a single ~2700-line file (`simulateLightSheetData.py`) containing 4 classes and helper functions. Features include cell type simulation, organelle generation, calcium signaling, blob detection, and TIFF/NPY export. No tests, no packaging, no modular structure.

## Short-term Improvements
- [ ] **Critical**: Split `simulateLightSheetData.py` into modules — extract `BiologicalSimulator` into `simulator.py`, `BiologicalSimulationWidget`/`BiologicalSimulationWindow` into `gui/`, `LightsheetViewer` into `viewer.py`, and `line_3d()` into `utils.py`
- [ ] Remove commented-out imports (`#from data_generator import DataGenerator`, `#from volume_processor import VolumeProcessor`)
- [ ] Add `requirements.txt` listing numpy, scipy, matplotlib, scikit-image, tifffile, PyQt5, pyqtgraph, PyOpenGL
- [ ] Add `pyproject.toml` or `setup.py` for proper packaging
- [ ] Add input validation for simulation parameters (negative radii, zero dimensions)
- [ ] Add error handling around file I/O (TIFF export, NPY save)
- [ ] Add docstrings to all public methods in `BiologicalSimulator`

## Feature Enhancements
- [ ] Add batch simulation mode: generate multiple datasets with varying parameters for pipeline testing
- [ ] Add noise models: Poisson shot noise, Gaussian read noise, and stripe artifacts typical of light-sheet microscopy
- [ ] Add PSF simulation: convolve volumes with realistic point spread functions (Gaussian or Gibson-Lanni)
- [ ] Add multi-channel support: simulate co-localized fluorophores with spectral bleedthrough
- [ ] Add progress bars for long-running simulations (time-series generation)
- [ ] Add parameter presets for common biological scenarios (e.g., "calcium imaging", "membrane dynamics")
- [ ] Improve `LightsheetViewer`: add orthogonal slice views (XY, XZ, YZ) simultaneously

## Long-term Vision
- [ ] Integrate as a MicroView plugin (the `microview` project already has a lightsheet plugin framework)
- [ ] Add ground-truth export: save blob positions, track IDs, and diffusion coefficients alongside synthetic data for benchmarking
- [ ] Add realistic tissue simulation: multiple cells, extracellular space, scattering
- [ ] Support OME-TIFF and OME-Zarr output formats for compatibility with modern bio-imaging tools
- [ ] Add command-line interface for headless batch generation

## Technical Debt
- [ ] Single 2700-line file is the #1 priority to address — violates maintainability
- [ ] Scattered `import` statements (PyQt5 imports split across lines 9-17, 28-29) should be consolidated
- [ ] `hasattr` checks in `updateBlobVisualization` suggest missing proper initialization
- [ ] No separation between simulation logic and GUI — makes headless use impossible
- [ ] No tests whatsoever — at minimum, add tests for `BiologicalSimulator` core methods
- [ ] `line_3d` Bresenham function should use numpy vectorization for performance
