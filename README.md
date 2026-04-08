# Biological Light Sheet Data Simulator

A Python application for generating and visualizing synthetic 3D biological datasets, designed for testing and validating light-sheet microscopy analysis pipelines. Features an interactive PyQt5 GUI with real-time 3D rendering via pyqtgraph OpenGL.

## Features

### Biological Simulation (`BiologicalSimulator`)
- **Protein diffusion**: Simulate diffusion using Gaussian filtering with configurable diffusion coefficients
- **Active transport**: Model cargo transport along a simulated cytoskeleton using 3D Bresenham line tracing
- **Cell types**: Generate spherical, neuronal, epithelial, and muscle cells in 3D
- **Organelles**: Create cell membranes, nuclei, and endoplasmic reticulum with adjustable density parameters
- **Calcium signaling**: Simulate dynamic calcium events -- blips, puffs, and propagating waves

### Data Generation
- **Synthetic volumes**: Create multi-channel 3D volumes and time-series with configurable moving intensity blobs
- **Light-sheet simulation**: Simulate angular recordings by rotating volumes and applying back-rotation correction
- **Blob analysis**: Detect blobs using Laplacian of Gaussian (scikit-image `blob_log`) with nearest-neighbor distance calculations via `scipy.spatial.cKDTree`
- **Volume processing**: Thresholding, statistical analysis, and distance transforms

### Interactive GUI
- **Parameter controls** (`BiologicalSimulationWidget`): Tabbed interface for adjusting simulation parameters in real time -- cell radius, axon length, ER density, diffusion coefficient, and more
- **3D rendering**: High-performance OpenGL visualization of generated volumes using `pyqtgraph.opengl`
- **Lightsheet viewer** (`LightsheetViewer`): Main window with 2D slice viewing, rotation controls, and blob detection overlay

### Export
- **TIFF stacks** (`.tif`): Multi-page stacks compatible with ImageJ/Fiji
- **NumPy arrays** (`.npy`): For fast loading in Python pipelines

## Architecture

The entire application lives in a single file (`simulateLightSheetData.py`, ~2700 lines) containing:

| Class | Purpose |
|---|---|
| `BiologicalSimulator` | Core simulation engine for diffusion, transport, and structure generation |
| `BiologicalSimulationWidget` | Tabbed QWidget for configuring simulation parameters |
| `BiologicalSimulationWindow` | QMainWindow wrapping the simulation widget with 3D OpenGL view |
| `LightsheetViewer` | QMainWindow for viewing generated data with 2D slices and analysis tools |

Helper functions:
- `line_3d()`: 3D Bresenham line algorithm for cytoskeleton path generation

## Requirements

- Python 3.x
- NumPy
- SciPy
- matplotlib
- scikit-image
- tifffile
- PyQt5
- pyqtgraph (with OpenGL support)

## Installation

```bash
pip install numpy scipy matplotlib scikit-image tifffile PyQt5 pyqtgraph PyOpenGL
```

## Usage

```bash
python simulateLightSheetData.py
```

This launches the simulation GUI where you can:

1. Select a cell type and configure structural parameters (radius, membrane thickness, etc.)
2. Set up dynamic simulations (diffusion coefficient, number of time points)
3. Generate synthetic 3D volumes and visualize them in the OpenGL viewer
4. Run blob detection and nearest-neighbor analysis on generated data
5. Export results as TIFF stacks or NumPy arrays

## GUI Framework

Built with **PyQt5** and **pyqtgraph.opengl** for 3D rendering.

## Key Dependencies

| Category | Libraries |
|---|---|
| GUI | PyQt5, pyqtgraph |
| Image processing | scikit-image, scipy.ndimage, tifffile |
| Spatial analysis | scipy.spatial (cKDTree), scipy.spatial.transform |
| Visualization | matplotlib (for 2D plots), pyqtgraph.opengl (for 3D) |
