# Lightsheet Simulator - Interface Map

## Module Overview

| File | Purpose |
|------|---------|
| `simulateLightSheetData.py` | Original monolithic file (kept for backward compat); contains `main()` entry point |
| `utils.py` | Utility functions: `line_3d()` Bresenham 3D line algorithm |
| `simulator.py` | `BiologicalSimulator` class: cell shapes, organelles, diffusion, calcium signals |
| `data_generator.py` | `DataGenerator` (synthetic volume/time-series, I/O) and `VolumeProcessor` (filter, stats) |
| `blob_analysis.py` | `BlobAnalyzer` (statistics, colocalization) + Qt dialogs: `BlobAnalysisDialog`, `BlobResultsDialog`, `TimeSeriesDialog` |
| `gui/__init__.py` | GUI package re-exports |
| `gui/simulation_widgets.py` | `BiologicalSimulationWidget` (parameter form) + `BiologicalSimulationWindow` |
| `gui/roi.py` | `ROI3D` OpenGL mesh item |
| `gui/viewer.py` | `LightsheetViewer` main application window (docks, 2D/3D views, blob detection, playback) |
| `tests/test_simulator.py` | Smoke tests for `BiologicalSimulator`, `DataGenerator`, `VolumeProcessor`, `line_3d` |

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
  -> simulator.py -> utils.py
  -> data_generator.py
  -> blob_analysis.py
  -> gui/simulation_widgets.py
  -> gui/roi.py (not yet used in viewer, available for future use)
```
