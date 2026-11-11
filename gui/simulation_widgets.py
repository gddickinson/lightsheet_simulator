"""
Biological simulation parameter widgets.

Contains BiologicalSimulationWidget (parameter entry form) and
BiologicalSimulationWindow (wrapper QMainWindow).
"""

from PyQt5.QtWidgets import (
    QWidget, QMainWindow, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QSpinBox, QDoubleSpinBox, QComboBox, QCheckBox,
    QTabWidget, QFormLayout,
)
from PyQt5.QtCore import pyqtSignal

from sim_params import CALCIUM_SIGNALS, CELL_TYPES, DYNAMICS_SPECS, STRUCTURE_SPECS, STRUCTURES


def _spin(spec, double=False):
    """QSpinBox / QDoubleSpinBox from a (min, max, step, default, ...) spec in sim_params.py."""
    sb = QDoubleSpinBox() if double else QSpinBox()
    sb.setRange(spec[0], spec[1])
    sb.setSingleStep(spec[2])
    sb.setValue(spec[3])
    return sb


class BiologicalSimulationWidget(QWidget):
    """Form widget for configuring biological simulation parameters."""

    simulationRequested = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        self._create_protein_tab()
        self._create_structure_tab()
        self._create_calcium_tab()

        self.simulate_button = QPushButton("Simulate")
        self.simulate_button.clicked.connect(self._request_simulation)
        main_layout.addWidget(self.simulate_button)

    # ---- Protein tab ----
    def _create_protein_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        row = QHBoxLayout()
        row.addWidget(QLabel("Protein Diffusion:"))
        self.diffusion_checkbox = QCheckBox()
        row.addWidget(self.diffusion_checkbox)
        self.diffusion_coefficient = _spin(DYNAMICS_SPECS["diffusion_coefficient"], double=True)
        row.addWidget(self.diffusion_coefficient)
        layout.addLayout(row)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Active Transport:"))
        self.transport_checkbox = QCheckBox()
        row2.addWidget(self.transport_checkbox)
        self.transport_velocity = _spin(DYNAMICS_SPECS["transport_velocity"], double=True)
        row2.addWidget(self.transport_velocity)
        layout.addLayout(row2)

        self.tab_widget.addTab(tab, "Protein Dynamics")

    # ---- Structure tab ----
    def _create_structure_tab(self):
        tab = QWidget()
        main_layout = QVBoxLayout(tab)

        row = QHBoxLayout()
        row.addWidget(QLabel("Cellular Structure:"))
        self.structure_combo = QComboBox()
        self.structure_combo.addItems(STRUCTURES)
        row.addWidget(self.structure_combo)
        main_layout.addLayout(row)

        form = QFormLayout()

        self.cell_type_combo = QComboBox()
        self.cell_type_combo.addItems(CELL_TYPES)
        form.addRow("Cell Type:", self.cell_type_combo)

        self.pixel_size_x = _spin(STRUCTURE_SPECS["pixel_size"], double=True)
        self.pixel_size_y = _spin(STRUCTURE_SPECS["pixel_size"], double=True)
        self.pixel_size_z = _spin(STRUCTURE_SPECS["pixel_size"], double=True)
        px_layout = QHBoxLayout()
        px_layout.addWidget(self.pixel_size_x)
        px_layout.addWidget(self.pixel_size_y)
        px_layout.addWidget(self.pixel_size_z)
        form.addRow("Pixel Size (x, y, z):", px_layout)

        # Membrane options
        self.membrane_options = QWidget()
        ml = QFormLayout(self.membrane_options)
        self.cell_radius = _spin(STRUCTURE_SPECS["cell_radius"])
        ml.addRow("Cell Radius:", self.cell_radius)
        self.membrane_thickness = _spin(STRUCTURE_SPECS["membrane_thickness"])
        ml.addRow("Membrane Thickness:", self.membrane_thickness)
        form.addRow(self.membrane_options)

        # Nucleus options
        self.nucleus_options = QWidget()
        nl = QFormLayout(self.nucleus_options)
        self.nucleus_radius = _spin(STRUCTURE_SPECS["nucleus_radius"])
        nl.addRow("Nucleus Radius:", self.nucleus_radius)
        self.nucleus_thickness = _spin(STRUCTURE_SPECS["nucleus_thickness"])
        nl.addRow("Nucleus Thickness:", self.nucleus_thickness)
        form.addRow(self.nucleus_options)

        # ER options
        self.er_options = QWidget()
        el = QFormLayout(self.er_options)
        self.er_density = _spin(STRUCTURE_SPECS["er_density"], double=True)
        el.addRow("ER Density:", self.er_density)
        form.addRow(self.er_options)
        main_layout.addLayout(form)

        # Neuron options
        self.neuron_options = QWidget()
        nrl = QFormLayout(self.neuron_options)
        self.soma_radius = _spin(STRUCTURE_SPECS["soma_radius"])
        nrl.addRow("Soma Radius:", self.soma_radius)
        self.axon_length = _spin(STRUCTURE_SPECS["axon_length"])
        nrl.addRow("Axon Length:", self.axon_length)
        self.axon_width = _spin(STRUCTURE_SPECS["axon_width"])
        nrl.addRow("Axon Width:", self.axon_width)
        self.num_dendrites = _spin(STRUCTURE_SPECS["num_dendrites"])
        nrl.addRow("Number of Dendrites:", self.num_dendrites)
        self.dendrite_length = _spin(STRUCTURE_SPECS["dendrite_length"])
        nrl.addRow("Dendrite Length:", self.dendrite_length)
        form.addRow(self.neuron_options)

        self.structure_combo.currentTextChanged.connect(self._toggle_structure_options)
        self.tab_widget.addTab(tab, "Cellular Structures")

    def _toggle_structure_options(self, structure):
        self.membrane_options.setVisible("Cell Membrane" in structure)
        self.nucleus_options.setVisible("Nucleus" in structure)
        self.er_options.setVisible("ER" in structure)
        self.neuron_options.setVisible("neuron" in structure.lower())

    # ---- Calcium tab ----
    def _create_calcium_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        row = QHBoxLayout()
        row.addWidget(QLabel("Calcium Signal:"))
        self.calcium_combo = QComboBox()
        self.calcium_combo.addItems(CALCIUM_SIGNALS)
        row.addWidget(self.calcium_combo)
        layout.addLayout(row)

        irow = QHBoxLayout()
        irow.addWidget(QLabel("Signal Intensity:"))
        self.calcium_intensity = _spin(DYNAMICS_SPECS["calcium_intensity"], double=True)
        irow.addWidget(self.calcium_intensity)
        layout.addLayout(irow)

        drow = QHBoxLayout()
        drow.addWidget(QLabel("Signal Duration:"))
        self.calcium_duration = _spin(DYNAMICS_SPECS["calcium_duration"])
        drow.addWidget(self.calcium_duration)
        layout.addLayout(drow)

        self.tab_widget.addTab(tab, "Calcium Signaling")

    # ---- Signal emission ----
    def _request_simulation(self):
        params = {
            "protein_diffusion": {
                "enabled": self.diffusion_checkbox.isChecked(),
                "coefficient": self.diffusion_coefficient.value(),
            },
            "active_transport": {
                "enabled": self.transport_checkbox.isChecked(),
                "velocity": self.transport_velocity.value(),
            },
            "cellular_structure": self.structure_combo.currentText(),
            "cell_radius": self.cell_radius.value(),
            "membrane_thickness": self.membrane_thickness.value(),
            "nucleus_radius": self.nucleus_radius.value(),
            "nucleus_thickness": self.nucleus_thickness.value(),
            "er_density": self.er_density.value(),
            "cell_type": self.cell_type_combo.currentText(),
            # (z, y, x): the order BiologicalSimulator expects (the form shows x, y, z)
            "pixel_size": (
                self.pixel_size_z.value(),
                self.pixel_size_y.value(),
                self.pixel_size_x.value(),
            ),
            "soma_radius": self.soma_radius.value(),
            "axon_length": self.axon_length.value(),
            "axon_width": self.axon_width.value(),
            "num_dendrites": self.num_dendrites.value(),
            "dendrite_length": self.dendrite_length.value(),
            "calcium_signal": {
                "type": self.calcium_combo.currentText(),
                "intensity": self.calcium_intensity.value(),
                "duration": self.calcium_duration.value(),
            },
        }
        self.simulationRequested.emit(params)


class BiologicalSimulationWindow(QMainWindow):
    """Wrapper window for BiologicalSimulationWidget."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Biological Simulation")
        self.simulation_widget = BiologicalSimulationWidget()
        self.setCentralWidget(self.simulation_widget)
        self.resize(400, 300)
