# Biological Light Sheet Data Simulator

A Python-based simulation tool for generating and visualizing 3D biological datasets, typically used for testing light-sheet microscopy analysis pipelines. This application features a graphical user interface (GUI) built with PyQt5 and provides tools for simulating protein dynamics, cellular structures, and calcium signaling events.

## Features

### 1. Biological Simulation

* **Protein Dynamics**: Simulate protein diffusion using Gaussian filters and active transport of cargo along a simulated cytoskeleton.
* **Cellular Structures**: Generate various 3D cell types including spherical, neuronal, epithelial, and muscle cells.
* **Organelle Generation**: Create detailed cellular components such as cell membranes, nuclei, and endoplasmic reticulum (ER) with adjustable densities.
* **Calcium Signaling**: Simulate dynamic events like calcium blips, puffs, and waves.

### 2. Data Generation & Processing

* **Synthetic Volume Generation**: Create multi-channel 3D volumes and time-series with moving "blobs" of intensity.
* **Light-Sheet Simulation**: Simulate angular recordings by rotating volumes and apply back-rotation for correction.
* **Analysis Tools**: Includes a `BlobAnalyzer` for nearest-neighbor distance calculations and a `VolumeProcessor` for thresholding and statistical analysis.

### 3. Interactive Visualization

* **GUI**: A PyQt5-based interface for adjusting simulation parameters in real-time.
* **3D Rendering**: Uses `pyqtgraph.opengl` for high-performance 3D visualization of generated volumes.

## Installation

### Prerequisites

Ensure you have Python 3.x installed. The project relies on several scientific and UI libraries:

```bash
pip install numpy scipy matplotlib scikit-image tifffile PyQt5 pyqtgraph

```

## Usage

To launch the simulation interface, run the main script:

```bash
python simulateLightSheetData.py

```

### Script Components

* **`BiologicalSimulator`**: The core engine for simulating diffusion, transport, and structural generation.
* **`DataGenerator`**: Handles the creation of synthetic TIFF stacks and NumPy arrays.
* **`BiologicalSimulationWidget`**: The tabbed UI component for configuring simulation parameters (e.g., cell radius, axon length, ER density).

## File Formats

The tool supports saving and loading data in the following formats:

* **TIFF (.tif)**: Multi-page stacks for compatibility with ImageJ/Fiji.
* **NumPy (.npy)**: Standard Python arrays for rapid processing.

---

### Key Dependencies in your code:

* **GUI**: `PyQt5`, `pyqtgraph`
* **Image Processing**: `scikit-image`, `scipy.ndimage`, `tifffile`
* **Calculations**: `numpy`, `scipy.spatial`