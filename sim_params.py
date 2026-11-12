"""
Parameter specifications for the biological simulation (Qt-free).

Single source of the ranges, steps and defaults shown by the desktop form
(gui/simulation_widgets.py) and the web interface (web/app.py). Each spec is
(min, max, step, default). Units follow how simulator.py uses each value:

- "um": micrometres; compared with distances computed as voxel offset x pixel
  size (membrane thickness is an exception for neurons, where it counts
  dilation steps, and epithelial cells, where it counts voxels along z).
- "voxels": used directly as voxel counts / indices.

Pixel (voxel) size is in micrometres, entered and passed in (z, y, x) order.

Also lists the volume size, cell types and structure choices of the desktop app.
"""

# Volume used by LightsheetViewer's BiologicalSimulator: (z, y, x) voxels.
VOLUME_SIZE_ZYX = (30, 100, 100)
PIXEL_SIZE_LABEL = "Pixel size (µm; z, y, x):"
NUM_TIME_POINTS = 10

CELL_TYPES = ["spherical", "neuron", "epithelial", "muscle"]
STRUCTURES = [
    "None", "Cell Membrane", "Nucleus",
    "Cell Membrane + Nucleus", "Cell Membrane + Nucleus + ER",
]
CALCIUM_SIGNALS = ["None", "Blip", "Puff", "Wave"]  # listed in the form; not implemented in simulator.py

# name: (min, max, step, default, unit, label)
STRUCTURE_SPECS = {
    "pixel_size": (0.1, 10, 0.1, 1, "um", "Pixel size"),
    "cell_radius": (5, 50, 1, 20, "um", "Cell radius"),
    "membrane_thickness": (1, 5, 1, 1, "um", "Membrane thickness"),
    "nucleus_radius": (1, 30, 1, 3, "um", "Nucleus radius"),
    "nucleus_thickness": (1, 3, 1, 1, "unused", "Nucleus thickness (shown in the form; not used by simulator.py)"),
    "er_density": (0.05, 0.2, 0.01, 0.1, "fraction", "ER density"),
    "soma_radius": (1, 20, 1, 5, "um", "Soma radius"),
    "axon_length": (10, 100, 1, 50, "um", "Axon length"),
    "axon_width": (1, 10, 1, 2, "um", "Axon width"),
    "num_dendrites": (1, 10, 1, 5, "count", "Number of dendrites"),
    "dendrite_length": (5, 50, 1, 25, "um", "Dendrite length"),
}

DYNAMICS_SPECS = {
    "diffusion_coefficient": (0, 100, 1, 1, "voxels^2/step", "Diffusion coefficient"),
    "transport_velocity": (-10, 10, 1, 1, "voxels/step", "Transport velocity"),
    "calcium_intensity": (0, 1, 0.1, 0.5, "a.u.", "Calcium signal intensity"),
    "calcium_duration": (1, 100, 1, 10, "frames", "Calcium signal duration"),
}

# LightsheetViewer "Data Generation" dock (moving-blob time series).
BLOB_SPECS = {
    "num_volumes": (1, 100, 1, 10, "volumes", "Number of volumes"),
    "num_blobs": (1, 100, 1, 30, "count", "Number of blobs"),
    "noise_level": (0, 1, 0.01, 0.02, "a.u.", "Noise level"),
    "movement_speed": (0, 10, 0.1, 0.5, "voxels/volume", "Movement speed"),
}
BLOB_INTENSITY_RANGE = (0.8, 1.0)
BLOB_SIGMA_RANGE = (2, 6)  # voxels
BLOB_CHANNELS = 2


def spec_dict(specs):
    """Specs as JSON-friendly dicts (for the web API)."""
    return {k: {"min": a, "max": b, "step": s, "default": d, "unit": u, "label": lab}
            for k, (a, b, s, d, u, lab) in specs.items()}
