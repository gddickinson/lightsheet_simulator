"""
Cellular-structure pipeline (Qt-free): what "Simulate" does in the desktop app.

simulate_structures() runs BiologicalSimulator the way LightsheetViewer's
_run_biological_simulation does (cell shape, then membrane / nucleus / ER
channels) and returns the channels instead of writing them into the viewer.
Used by gui/viewer.py and by the web interface (web/), so both build the same
sample from the same parameters.
"""
import numpy as np


def nucleus_radius_used(params):
    """Nucleus radius (um) passed to generate_nucleus / generate_er: the form value (the nucleus is clipped to the
    cell interior, so a radius larger than the cell fills it)."""
    return params["nucleus_radius"]


def simulate_structures(simulator, params):
    """Return [(name, volume)] for the structures named by params["cellular_structure"].

    params uses the keys emitted by BiologicalSimulationWidget (cell_type, pixel_size as (z, y, x),
    membrane_thickness, cell_radius, soma_radius, axon_length, axon_width, num_dendrites,
    dendrite_length, nucleus_radius, er_density). Volumes are float arrays of simulator.size (z, y, x).
    The random draws (neuron terminals/dendrites, ER) use the global np.random state.
    """
    structure = params["cellular_structure"]
    if structure == "None":
        return []
    soma_center = tuple(s // 2 for s in simulator.size)
    px = params["pixel_size"]
    cell_shape, cell_interior, cell_membrane = simulator.generate_cell_shape(
        params["cell_type"], simulator.size, px,
        membrane_thickness=params["membrane_thickness"],
        cell_radius=params["cell_radius"],
        soma_radius=params["soma_radius"],
        axon_length=params["axon_length"],
        axon_width=params["axon_width"],
        num_dendrites=params["num_dendrites"],
        dendrite_length=params["dendrite_length"],
    )
    nuc_r = nucleus_radius_used(params)
    channels = []
    if "Cell Membrane" in structure:
        channels.append(("membrane", cell_membrane))
    if "Nucleus" in structure:
        nd, _ = simulator.generate_nucleus(cell_interior, soma_center, nuc_r, pixel_size=px)
        channels.append(("nucleus", nd))
    if "ER" in structure:
        er = simulator.generate_er(cell_shape, soma_center, nuc_r, params["er_density"], px)
        channels.append(("ER", er))
    return channels


def stack_channels(channels, num_time_points):
    """(name, volume) list -> array (time, channel, z, y, x), each volume repeated over time."""
    vols = np.stack([v for _, v in channels])
    return np.repeat(vols[np.newaxis], num_time_points, axis=0)
