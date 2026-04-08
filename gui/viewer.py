"""
Main LightsheetViewer window for the lightsheet simulator.

This is the primary application window containing 2-D slice views (XY, XZ, YZ),
3-D scatter/surface views, data generation controls, blob detection, and
playback controls.
"""

import sys
import logging
import traceback

import numpy as np
import tifffile

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
    QPushButton, QSlider, QLabel, QSpinBox, QDoubleSpinBox,
    QComboBox, QFileDialog, QMessageBox, QCheckBox, QDockWidget,
    QSizePolicy, QTableWidget, QTableWidgetItem, QDialog,
    QGridLayout, QAction,
)
from PyQt5.QtCore import Qt, QTimer, QEvent, pyqtSlot
from PyQt5.QtGui import QVector3D, QImage

import pyqtgraph as pg
import pyqtgraph.opengl as gl
from matplotlib import pyplot as plt
from skimage.feature import blob_log

from simulator import BiologicalSimulator
from data_generator import DataGenerator, VolumeProcessor
from blob_analysis import BlobAnalyzer, BlobAnalysisDialog, BlobResultsDialog, TimeSeriesDialog
from gui.simulation_widgets import BiologicalSimulationWindow


class LightsheetViewer(QMainWindow):
    """Main application window for lightsheet microscopy data viewing and simulation."""

    def __init__(self):
        super().__init__()
        self._init_logging()
        self.volume_processor = VolumeProcessor()
        self.data = None
        self.lastPos = None
        self.data_generator = DataGenerator()

        self.channel_colors = [(1, 0, 0, 1), (0, 1, 0, 1), (0, 0, 1, 1)]
        self.biological_simulator = BiologicalSimulator(size=(30, 100, 100), num_time_points=10)
        self.biological_simulation_window = None

        self._setup_channel_controls_widget()
        self._init_ui()
        self._generate_data()

        self.playbackTimer = QTimer(self)
        self.playbackTimer.timeout.connect(self._advance_time_point)
        self.blob_results_dialog = BlobResultsDialog(self)
        self.showBlobResultsButton.setVisible(False)

    # ------------------------------------------------------------------
    # Initialization helpers
    # ------------------------------------------------------------------

    def _init_logging(self):
        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
        self.logger = logging.getLogger(__name__)

    def _init_ui(self):
        self.setWindowTitle("Lightsheet Microscopy Viewer")
        self.setGeometry(100, 100, 1600, 900)
        self.setCentralWidget(None)

        self._create_view_docks()
        self._create_data_generation_dock()
        self._create_3d_visualization_dock()
        self._create_visualization_control_dock()
        self._create_playback_control_dock()
        self._create_blob_visualization_dock()
        self._connect_view_events()
        self._create_menu_bar()

        self.setDockOptions(QMainWindow.AllowNestedDocks | QMainWindow.AllowTabbedDocks)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.dockXY)
        self.splitDockWidget(self.dockXY, self.dockXZ, Qt.Vertical)
        self.splitDockWidget(self.dockXZ, self.dockYZ, Qt.Vertical)
        self.addDockWidget(Qt.RightDockWidgetArea, self.dock3D)
        self.addDockWidget(Qt.RightDockWidgetArea, self.dockDataGeneration)
        self.addDockWidget(Qt.RightDockWidgetArea, self.dockVisualizationControl)
        self.addDockWidget(Qt.RightDockWidgetArea, self.dockPlaybackControl)
        self.splitDockWidget(self.dock3D, self.dockDataGeneration, Qt.Horizontal)
        self.tabifyDockWidget(self.dockDataGeneration, self.dockVisualizationControl)
        self.tabifyDockWidget(self.dockVisualizationControl, self.dockPlaybackControl)
        self.splitDockWidget(self.dock3D, self.dockBlobVisualization, Qt.Vertical)

        self.resizeDocks([self.dockXY, self.dockXZ, self.dockYZ], [200, 200, 200], Qt.Vertical)
        self.resizeDocks([self.dock3D, self.dockDataGeneration], [800, 300], Qt.Horizontal)
        self._check_view_state()

    # ------------------------------------------------------------------
    # Dock creation
    # ------------------------------------------------------------------

    def _create_view_docks(self):
        for name, attr_dock, attr_view in [
            ("XY View", "dockXY", "imageViewXY"),
            ("XZ View", "dockXZ", "imageViewXZ"),
            ("YZ View", "dockYZ", "imageViewYZ"),
        ]:
            dock = QDockWidget(name, self)
            iv = pg.ImageView()
            iv.ui.roiBtn.hide()
            iv.ui.menuBtn.hide()
            iv.setPredefinedGradient("viridis")
            iv.timeLine.sigPositionChanged.connect(self._update_markers_from_sliders)
            dock.setWidget(iv)
            self.addDockWidget(Qt.LeftDockWidgetArea, dock)
            setattr(self, attr_dock, dock)
            setattr(self, attr_view, iv)

        for view in [self.imageViewXY, self.imageViewXZ, self.imageViewYZ]:
            view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            view.setMinimumSize(200, 200)

    def _create_data_generation_dock(self):
        self.dockDataGeneration = QDockWidget("Data Generation", self)
        w = QWidget()
        layout = QVBoxLayout(w)

        layout.addWidget(QLabel("Number of Volumes:"))
        self.numVolumesSpinBox = QSpinBox()
        self.numVolumesSpinBox.setRange(1, 100)
        self.numVolumesSpinBox.setValue(10)
        layout.addWidget(self.numVolumesSpinBox)

        layout.addWidget(QLabel("Number of Blobs:"))
        self.numBlobsSpinBox = QSpinBox()
        self.numBlobsSpinBox.setRange(1, 100)
        self.numBlobsSpinBox.setValue(30)
        layout.addWidget(self.numBlobsSpinBox)

        layout.addWidget(QLabel("Noise Level:"))
        self.noiseLevelSpinBox = QDoubleSpinBox()
        self.noiseLevelSpinBox.setRange(0, 1)
        self.noiseLevelSpinBox.setSingleStep(0.01)
        self.noiseLevelSpinBox.setValue(0.02)
        layout.addWidget(self.noiseLevelSpinBox)

        layout.addWidget(QLabel("Movement Speed:"))
        self.movementSpeedSpinBox = QDoubleSpinBox()
        self.movementSpeedSpinBox.setRange(0, 10)
        self.movementSpeedSpinBox.setSingleStep(0.1)
        self.movementSpeedSpinBox.setValue(0.5)
        layout.addWidget(self.movementSpeedSpinBox)

        self.structuredDataCheck = QCheckBox("Generate Structured Data")
        self.structuredDataCheck.setChecked(False)
        layout.addWidget(self.structuredDataCheck)

        self.channelRangeWidgets = []
        for i in range(2):
            gl_layout = QGridLayout()
            gl_layout.addWidget(QLabel(f"Channel {i + 1} Range:"), 0, 0, 1, 6)
            spins = []
            for row_idx, (lbl_a, lbl_b) in enumerate(
                [("X min", "X max"), ("Y min", "Y max"), ("Z min", "Z max")], start=1
            ):
                gl_layout.addWidget(QLabel(lbl_a), row_idx, 0)
                s1 = QSpinBox(); s1.setRange(0, 100)
                gl_layout.addWidget(s1, row_idx, 1)
                gl_layout.addWidget(QLabel(lbl_b), row_idx, 2)
                s2 = QSpinBox(); s2.setRange(0, 100)
                gl_layout.addWidget(s2, row_idx, 3)
                spins.extend([s1, s2])
            self.channelRangeWidgets.append(tuple(spins))
            layout.addLayout(gl_layout)

        self.generateButton = QPushButton("Generate New Data")
        self.generateButton.clicked.connect(self._generate_data)
        layout.addWidget(self.generateButton)
        self.saveButton = QPushButton("Save Data")
        self.saveButton.clicked.connect(self._save_data)
        layout.addWidget(self.saveButton)
        self.loadButton = QPushButton("Load Data")
        self.loadButton.clicked.connect(self._load_data)
        layout.addWidget(self.loadButton)
        layout.addStretch(1)
        self.dockDataGeneration.setWidget(w)

    def _create_3d_visualization_dock(self):
        self.dock3D = QDockWidget("3D View", self)
        self.glView = gl.GLViewWidget()
        self.dock3D.setWidget(self.glView)
        self.addDockWidget(Qt.RightDockWidgetArea, self.dock3D)
        for Item in [gl.GLGridItem] * 3:
            g = Item()
            self.glView.addItem(g)
        self.data_items = []
        self.main_slice_marker_items = []
        self.glView.opts["fov"] = 60
        self.glView.opts["elevation"] = 30
        self.glView.opts["azimuth"] = 45
        self.glView.mousePressEvent = self._on_3d_mouse_press
        self.glView.mouseReleaseEvent = self._on_3d_mouse_release
        self.glView.mouseMoveEvent = self._on_3d_mouse_move
        self.glView.wheelEvent = self._on_3d_wheel

    def _create_visualization_control_dock(self):
        self.dockVisualizationControl = QDockWidget("Visualization Control", self)
        w = QWidget()
        layout = QVBoxLayout(w)

        self._setup_channel_controls_widget()
        layout.addWidget(self.channelControlsWidget)

        layout.addWidget(QLabel("Threshold:"))
        self.thresholdSpinBox = QDoubleSpinBox()
        self.thresholdSpinBox.setRange(0, 1)
        self.thresholdSpinBox.setSingleStep(0.1)
        self.thresholdSpinBox.setValue(0)
        self.thresholdSpinBox.valueChanged.connect(self._update_threshold)
        layout.addWidget(self.thresholdSpinBox)

        layout.addWidget(QLabel("Point Size"))
        self.scatterPointSizeSpinBox = QDoubleSpinBox()
        self.scatterPointSizeSpinBox.setRange(0, 100)
        self.scatterPointSizeSpinBox.setSingleStep(1)
        self.scatterPointSizeSpinBox.setValue(2)
        self.scatterPointSizeSpinBox.valueChanged.connect(self._update_scatter_size)
        layout.addWidget(self.scatterPointSizeSpinBox)

        layout.addWidget(QLabel("3D Rendering Mode:"))
        self.renderModeCombo = QComboBox()
        self.renderModeCombo.addItems(["Points", "Surface", "Wireframe"])
        self.renderModeCombo.currentTextChanged.connect(lambda: self._create_3d_visualization())
        layout.addWidget(self.renderModeCombo)

        layout.addWidget(QLabel("Color Map:"))
        self.colorMapCombo = QComboBox()
        self.colorMapCombo.addItems(["Viridis", "Plasma", "Inferno", "Magma", "Grayscale"])
        self.colorMapCombo.currentTextChanged.connect(lambda: self._create_3d_visualization())
        layout.addWidget(self.colorMapCombo)

        self.showSliceMarkersCheck = QCheckBox("Show Slice Markers")
        self.showSliceMarkersCheck.stateChanged.connect(self._toggle_slice_markers)
        layout.addWidget(self.showSliceMarkersCheck)

        layout.addWidget(QLabel("Clip Plane:"))
        self.clipSlider = QSlider(Qt.Horizontal)
        self.clipSlider.setMinimum(0)
        self.clipSlider.setMaximum(100)
        self.clipSlider.setValue(100)
        self.clipSlider.valueChanged.connect(self._update_clip_plane)
        layout.addWidget(self.clipSlider)

        self.syncViewsCheck = QCheckBox("Synchronize 3D Views")
        self.syncViewsCheck.setChecked(False)
        layout.addWidget(self.syncViewsCheck)

        self.autoScaleButton = QPushButton("Auto Scale Views")
        self.autoScaleButton.clicked.connect(self._auto_scale_views)
        layout.addWidget(self.autoScaleButton)

        for lbl, slot in [
            ("Top-Down View", self._set_top_down),
            ("Side View (XZ)", self._set_side),
            ("Front View (YZ)", self._set_front),
        ]:
            btn = QPushButton(lbl)
            btn.clicked.connect(slot)
            layout.addWidget(btn)

        # Blob detection controls
        layout.addWidget(QLabel("Blob Detection:"))
        blob_grid = QGridLayout()
        blob_grid.addWidget(QLabel("Max Sigma:"), 0, 0)
        self.maxSigmaSpinBox = QDoubleSpinBox()
        self.maxSigmaSpinBox.setRange(1, 100)
        self.maxSigmaSpinBox.setValue(30)
        blob_grid.addWidget(self.maxSigmaSpinBox, 0, 1)
        blob_grid.addWidget(QLabel("Num Sigma:"), 1, 0)
        self.numSigmaSpinBox = QSpinBox()
        self.numSigmaSpinBox.setRange(1, 20)
        self.numSigmaSpinBox.setValue(10)
        blob_grid.addWidget(self.numSigmaSpinBox, 1, 1)
        blob_grid.addWidget(QLabel("Threshold:"), 2, 0)
        self.blobThresholdSpinBox = QDoubleSpinBox()
        self.blobThresholdSpinBox.setRange(0, 1)
        self.blobThresholdSpinBox.setSingleStep(0.01)
        self.blobThresholdSpinBox.setValue(0.5)
        blob_grid.addWidget(self.blobThresholdSpinBox, 2, 1)
        self.blobThresholdSpinBox.valueChanged.connect(self._filter_blobs)

        self.showAllBlobsCheck = QCheckBox("Show All Blobs")
        self.showAllBlobsCheck.setChecked(False)
        self.showAllBlobsCheck.stateChanged.connect(self._update_blob_visualization)
        layout.addWidget(self.showAllBlobsCheck)
        layout.addLayout(blob_grid)

        self.blobDetectionButton = QPushButton("Detect Blobs")
        self.blobDetectionButton.clicked.connect(self._detect_blobs)
        layout.addWidget(self.blobDetectionButton)

        self.showBlobResultsButton = QPushButton("Show Blob Results")
        self.showBlobResultsButton.clicked.connect(self._toggle_blob_results)
        layout.addWidget(self.showBlobResultsButton)

        self.blobAnalysisButton = QPushButton("Analyze Blobs")
        self.blobAnalysisButton.clicked.connect(self._analyze_blobs)
        layout.addWidget(self.blobAnalysisButton)

        self.timeSeriesButton = QPushButton("Time Series Analysis")
        self.timeSeriesButton.clicked.connect(self._show_time_series)
        layout.addWidget(self.timeSeriesButton)

        layout.addStretch(1)
        self.dockVisualizationControl.setWidget(w)

    def _create_blob_visualization_dock(self):
        self.dockBlobVisualization = QDockWidget("Blob Visualization", self)
        self.blobGLView = gl.GLViewWidget()
        self.dockBlobVisualization.setWidget(self.blobGLView)
        self.addDockWidget(Qt.RightDockWidgetArea, self.dockBlobVisualization)
        for _ in range(3):
            self.blobGLView.addItem(gl.GLGridItem())
        self.blob_items = []
        self.slice_marker_items = []
        self.blobGLView.mousePressEvent = self._on_3d_mouse_press
        self.blobGLView.mouseReleaseEvent = self._on_3d_mouse_release
        self.blobGLView.mouseMoveEvent = self._on_3d_mouse_move
        self.blobGLView.wheelEvent = self._on_3d_wheel

    def _create_playback_control_dock(self):
        self.dockPlaybackControl = QDockWidget("Playback Control", self)
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(QLabel("Time:"))
        self.timeSlider = QSlider(Qt.Horizontal)
        self.timeSlider.setMinimum(0)
        self.timeSlider.valueChanged.connect(self._update_time_point)
        layout.addWidget(self.timeSlider)

        row = QHBoxLayout()
        self.playPauseButton = QPushButton("Play")
        self.playPauseButton.clicked.connect(self._toggle_playback)
        row.addWidget(self.playPauseButton)
        row.addWidget(QLabel("Speed:"))
        self.speedSpinBox = QDoubleSpinBox()
        self.speedSpinBox.setRange(0.1, 10)
        self.speedSpinBox.setSingleStep(0.1)
        self.speedSpinBox.setValue(1)
        self.speedSpinBox.valueChanged.connect(self._update_playback_speed)
        row.addWidget(self.speedSpinBox)
        self.loopCheckBox = QCheckBox("Loop")
        row.addWidget(self.loopCheckBox)
        layout.addLayout(row)
        layout.addStretch(1)
        self.dockPlaybackControl.setWidget(w)

    # ------------------------------------------------------------------
    # Menu bar
    # ------------------------------------------------------------------

    def _create_menu_bar(self):
        mb = self.menuBar()
        file_menu = mb.addMenu("&File")
        file_menu.addAction("&Load Data").triggered.connect(self._load_data)
        file_menu.addAction("&Save Data").triggered.connect(self._save_data)
        file_menu.addAction("&Quit").triggered.connect(self.close)

        view_menu = mb.addMenu("&View")
        for dock in [
            self.dockXY, self.dockXZ, self.dockYZ, self.dock3D,
            self.dockDataGeneration, self.dockVisualizationControl, self.dockPlaybackControl,
        ]:
            view_menu.addAction(dock.toggleViewAction())

        analysis_menu = mb.addMenu("&Analysis")
        analysis_menu.addAction("Time Series Analysis").triggered.connect(self._show_time_series)

        bio_menu = mb.addMenu("&Simulation")
        self.showBioSimAction = QAction("Biological Simulation", self, checkable=True)
        self.showBioSimAction.triggered.connect(self._toggle_bio_sim_window)
        bio_menu.addAction(self.showBioSimAction)

    # ------------------------------------------------------------------
    # Biological simulation
    # ------------------------------------------------------------------

    def _toggle_bio_sim_window(self, checked):
        if checked:
            if self.biological_simulation_window is None:
                self.biological_simulation_window = BiologicalSimulationWindow(self)
                self.biological_simulation_window.simulation_widget.simulationRequested.connect(
                    self._run_biological_simulation
                )
            self.biological_simulation_window.show()
        elif self.biological_simulation_window:
            self.biological_simulation_window.hide()

    def _run_biological_simulation(self, params):
        try:
            if params["protein_diffusion"]["enabled"]:
                coeff = params["protein_diffusion"]["coefficient"]
                if self.data is not None:
                    self.biological_simulator.num_time_points = self.data.shape[0]
                else:
                    self.biological_simulator.num_time_points = 10
                ic = np.zeros(self.biological_simulator.size)
                c = [s // 2 for s in self.biological_simulator.size]
                ic[c[0], c[1], c[2]] = 1.0
                dd = self.biological_simulator.simulate_protein_diffusion(coeff, ic)
                if self.data is None:
                    self.data = dd[:, np.newaxis]
                else:
                    self.data = np.concatenate((self.data, dd[:, np.newaxis]), axis=1)
                self.logger.info(f"Added protein diffusion data. Shape: {self.data.shape}")
                self._update_ui_for_new_data()

            if params["active_transport"]["enabled"]:
                self.logger.info("Active transport simulation not yet implemented")

            if params["cellular_structure"] != "None":
                soma_center = tuple(s // 2 for s in self.biological_simulator.size)
                px = params["pixel_size"]
                cell_shape, cell_interior, cell_membrane = self.biological_simulator.generate_cell_shape(
                    params["cell_type"], self.biological_simulator.size, px,
                    membrane_thickness=params["membrane_thickness"],
                    cell_radius=params["cell_radius"],
                    soma_radius=params["soma_radius"],
                    axon_length=params["axon_length"],
                    axon_width=params["axon_width"],
                    num_dendrites=params["num_dendrites"],
                    dendrite_length=params["dendrite_length"],
                )
                ntp = self.biological_simulator.num_time_points
                nuc_r = max(5, min(params["nucleus_radius"], params["soma_radius"] // 2))

                if "Cell Membrane" in params["cellular_structure"]:
                    ts = np.repeat(cell_membrane[np.newaxis, np.newaxis], ntp, axis=0)
                    self.data = ts

                if "Nucleus" in params["cellular_structure"]:
                    nd, _ = self.biological_simulator.generate_nucleus(
                        cell_interior, soma_center, nuc_r, pixel_size=px
                    )
                    ts = np.repeat(nd[np.newaxis, np.newaxis], ntp, axis=0)
                    self.data = ts if self.data is None else np.concatenate((self.data, ts), axis=1)

                if "ER" in params["cellular_structure"]:
                    er = self.biological_simulator.generate_er(
                        cell_shape, soma_center, nuc_r, params["er_density"], px
                    )
                    ts = np.repeat(er[np.newaxis, np.newaxis], ntp, axis=0)
                    self.data = ts if self.data is None else np.concatenate((self.data, ts), axis=1)

                self._update_ui_for_new_data()
                self._update_views()
                self._create_3d_visualization()

            if params["calcium_signal"]["type"] != "None":
                self.logger.info(f"Calcium signal not yet implemented")

            self._update_views()
            self._create_3d_visualization()

        except Exception as e:
            self.logger.error(f"Error in biological simulation: {str(e)}")
            QMessageBox.critical(self, "Simulation Error", str(e))

    # ------------------------------------------------------------------
    # Data generation / I-O
    # ------------------------------------------------------------------

    def _generate_data(self):
        try:
            nv = self.numVolumesSpinBox.value()
            nb = self.numBlobsSpinBox.value()
            nl = self.noiseLevelSpinBox.value()
            ms = self.movementSpeedSpinBox.value()
            nc = 2
            size = (30, 100, 100)

            if self.structuredDataCheck.isChecked():
                cr = []
                for widgets in self.channelRangeWidgets:
                    vals = [w.value() for w in widgets]
                    cr.append(((vals[0], vals[1]), (vals[2], vals[3]), (vals[4], vals[5])))
                while len(cr) < nc:
                    cr.append(((0, size[2]), (0, size[1]), (0, size[0])))
                self.data = self.data_generator.generate_structured_multi_channel_time_series(
                    num_volumes=nv, num_channels=nc, size=size, num_blobs=nb,
                    intensity_range=(0.8, 1.0), sigma_range=(2, 6),
                    noise_level=nl, movement_speed=ms, channel_ranges=cr,
                )
            else:
                self.data = self.data_generator.generate_multi_channel_time_series(
                    num_volumes=nv, num_channels=nc, size=size, num_blobs=nb,
                    intensity_range=(0.8, 1.0), sigma_range=(2, 6),
                    noise_level=nl, movement_speed=ms,
                )

            self.logger.info(f"Generated data shape: {self.data.shape}")
            self._update_ui_for_new_data()
            self.timeSlider.setMaximum(nv - 1)
            self._update_views()
            self._create_3d_visualization()
            self._auto_scale_views()
        except Exception as e:
            self.logger.error(f"Error in data generation: {traceback.format_exc()}")
            QMessageBox.critical(self, "Error", f"Failed to generate data: {str(e)}")

    def _save_data(self):
        try:
            fn, _ = QFileDialog.getSaveFileName(self, "Save Data", "", "TIFF Files (*.tiff);;NumPy Files (*.npy)")
            if fn:
                if fn.endswith(".tiff"):
                    self.data_generator.save_tiff(fn)
                elif fn.endswith(".npy"):
                    self.data_generator.save_numpy(fn)
                self.logger.info(f"Data saved to {fn}")
        except Exception as e:
            self.logger.error(f"Error saving data: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to save data: {str(e)}")

    def _load_data(self):
        try:
            fn, _ = QFileDialog.getOpenFileName(self, "Load Data", "", "TIFF Files (*.tiff);;NumPy Files (*.npy)")
            if fn:
                if fn.endswith(".tiff"):
                    self.data = self.data_generator.load_tiff(fn)
                elif fn.endswith(".npy"):
                    self.data = self.data_generator.load_numpy(fn)
                self.timeSlider.setMaximum(self.data.shape[0] - 1)
                self._update_views()
                self._create_3d_visualization()
                self._auto_scale_views()
                self.logger.info(f"Data loaded from {fn}")
                if self.playbackTimer.isActive():
                    self.playbackTimer.stop()
                    self.playPauseButton.setText("Play")
        except Exception as e:
            self.logger.error(f"Error loading data: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to load data: {str(e)}")

    # ------------------------------------------------------------------
    # View updates
    # ------------------------------------------------------------------

    def _update_views(self):
        if self.data is None:
            return
        t = self.timeSlider.value()
        threshold = self.thresholdSpinBox.value()
        num_channels = self.data.shape[1]
        depth, height, width = self.data.shape[2:]

        combined_xy = np.zeros((depth, height, width, 3))
        combined_xz = np.zeros((height, depth, width, 3))
        combined_yz = np.zeros((height, depth, width, 3))
        colors = [
            (1, 0, 0), (0, 1, 0), (0, 0, 1),
            (1, 1, 0), (1, 0, 1), (0, 1, 1),
            (0.5, 0.5, 0.5), (1, 0.5, 0),
        ]

        for c in range(num_channels):
            if c < len(self.channelControls) and self.channelControls[c][0].isChecked():
                opacity = self.channelControls[c][1].value() / 100
                cd = self.data[t, c]
                cd = (cd - cd.min()) / (cd.max() - cd.min() + 1e-8)
                cd[cd < threshold] = 0
                col = colors[c % len(colors)]
                colored = cd[:, :, :, np.newaxis] * col
                combined_xy += colored * opacity
                combined_xz += np.transpose(colored, (1, 0, 2, 3)) * opacity
                combined_yz += np.transpose(colored, (2, 0, 1, 3)) * opacity

        for arr, iv in [
            (combined_xy, self.imageViewXY),
            (combined_xz, self.imageViewXZ),
            (combined_yz, self.imageViewYZ),
        ]:
            iv.setImage(np.clip(arr, 0, 1), autoLevels=False, levels=[0, 1])
        self._update_slice_markers()

    def _create_3d_visualization(self):
        try:
            for item in self.data_items:
                self.glView.removeItem(item)
            self.data_items.clear()
            if self.data is None:
                return

            t = self.timeSlider.value()
            threshold = self.thresholdSpinBox.value()
            ch_colors = [(1, 0, 0, 1), (0, 1, 0, 1), (0, 0, 1, 1)]

            for c in range(self.data.shape[1]):
                if c < len(self.channelControls) and self.channelControls[c][0].isChecked():
                    opacity = self.channelControls[c][1].value() / 100
                    vd = self.data[t, c]
                    z, y, x = np.where(vd > threshold)
                    pos = np.column_stack((x, y, z))
                    if len(pos) > 0:
                        cols = np.tile(ch_colors[c % len(ch_colors)], (len(pos), 1))
                        cols[:, 3] = opacity * (vd[z, y, x] - vd.min()) / (vd.max() - vd.min() + 1e-8)
                        scatter = gl.GLScatterPlotItem(pos=pos, color=cols, size=self.scatterPointSizeSpinBox.value())
                        self.glView.addItem(scatter)
                        self.data_items.append(scatter)
            self.glView.update()
        except Exception as e:
            self.logger.error(f"Error in 3D visualization: {traceback.format_exc()}")
            QMessageBox.critical(self, "Error", str(e))

    def _update_markers_from_sliders(self):
        self._update_slice_markers()
        self._create_3d_visualization()

    def _update_slice_markers(self):
        if self.data is None:
            return
        for item in self.slice_marker_items:
            try:
                self.blobGLView.removeItem(item)
            except Exception:
                pass
        for item in self.main_slice_marker_items:
            try:
                self.glView.removeItem(item)
            except Exception:
                pass
        self.slice_marker_items.clear()
        self.main_slice_marker_items.clear()

        if self.showSliceMarkersCheck.isChecked():
            _, _, depth, height, width = self.data.shape
            zs = int(self.imageViewXY.currentIndex)
            ys = int(self.imageViewXZ.currentIndex)
            xs = int(self.imageViewYZ.currentIndex)

            for view, item_list in [(self.glView, self.main_slice_marker_items),
                                    (self.blobGLView, self.slice_marker_items)]:
                xm = gl.GLLinePlotItem(
                    pos=np.array([[xs, 0, 0], [xs, height, 0], [xs, height, depth], [xs, 0, depth]]),
                    color=(1, 0, 0, 1), width=2, mode="line_strip")
                ym = gl.GLLinePlotItem(
                    pos=np.array([[0, ys, 0], [width, ys, 0], [width, ys, depth], [0, ys, depth]]),
                    color=(0, 1, 0, 1), width=2, mode="line_strip")
                zm = gl.GLLinePlotItem(
                    pos=np.array([[0, 0, zs], [width, 0, zs], [width, height, zs], [0, height, zs]]),
                    color=(0, 0, 1, 1), width=2, mode="line_strip")
                view.addItem(xm)
                view.addItem(ym)
                view.addItem(zm)
                item_list.extend([xm, ym, zm])
            self.glView.update()
            self.blobGLView.update()

    # ------------------------------------------------------------------
    # Blob detection
    # ------------------------------------------------------------------

    def _detect_blobs(self):
        if self.data is None:
            return
        max_time = self.timeSlider.maximum() + 1
        nc = self.data.shape[1]
        max_sigma = self.maxSigmaSpinBox.value()
        num_sigma = self.numSigmaSpinBox.value()
        all_blobs = []
        for ch in range(nc):
            for t in range(max_time):
                vol = self.data[t, ch]
                blobs = blob_log(vol, max_sigma=max_sigma, num_sigma=num_sigma)
                for blob in blobs:
                    by, bx, bz, r = blob
                    iy, ix, iz = int(by), int(bx), int(bz)
                    ir = int(r)
                    region = vol[
                        max(0, iy - ir):min(vol.shape[0], iy + ir + 1),
                        max(0, ix - ir):min(vol.shape[1], ix + ir + 1),
                        max(0, iz - ir):min(vol.shape[2], iz + ir + 1),
                    ]
                    all_blobs.append([by, bx, bz, r, ch, t, np.mean(region)])
        all_blobs = np.array(all_blobs)
        self.original_blobs = all_blobs
        self._filter_blobs()
        self.logger.info(f"Detected {len(all_blobs)} blobs across all channels")
        self._display_blob_results(self.all_detected_blobs)
        self._update_blob_visualization()
        self.showBlobResultsButton.setVisible(True)
        self.showBlobResultsButton.setText("Show Blob Results")

    def _filter_blobs(self):
        if not hasattr(self, "original_blobs"):
            return
        thr = self.blobThresholdSpinBox.value()
        self.all_detected_blobs = self.original_blobs[self.original_blobs[:, 6] > thr]
        self._update_blob_visualization()

    def _display_blob_results(self, blobs):
        dlg = QDialog(self)
        dlg.setWindowTitle("Blob Detection Results")
        layout = QVBoxLayout(dlg)
        table = QTableWidget()
        table.setColumnCount(7)
        table.setHorizontalHeaderLabels(["X", "Y", "Z", "Size", "Channel", "Time", "Intensity"])
        table.setRowCount(len(blobs))
        for i, blob in enumerate(blobs):
            by, bx, bz, r, ch, t, intensity = blob
            for j, v in enumerate([f"{bx:.2f}", f"{by:.2f}", f"{bz:.2f}", f"{r:.2f}",
                                   f"{int(ch)}", f"{int(t)}", f"{intensity:.2f}"]):
                table.setItem(i, j, QTableWidgetItem(v))
        layout.addWidget(table)
        QPushButton("Close", clicked=dlg.close).setParent(dlg)
        layout.addWidget(QPushButton("Close", clicked=dlg.close))
        dlg.exec_()

    def _update_blob_visualization(self):
        if not hasattr(self, "all_detected_blobs") or self.all_detected_blobs is None:
            return
        for item in self.blob_items:
            self.blobGLView.removeItem(item)
        self.blob_items.clear()
        ct = self.timeSlider.value()
        blobs = self.all_detected_blobs if self.showAllBlobsCheck.isChecked() else \
            self.all_detected_blobs[self.all_detected_blobs[:, 5] == ct]
        self._visualize_blobs(blobs)

    def _visualize_blobs(self, blobs):
        for item in self.blob_items:
            self.blobGLView.removeItem(item)
        self.blob_items.clear()
        ct = self.timeSlider.value()
        ch_colors = [(1, 0, 0, 0.5), (0, 1, 0, 0.5), (0, 0, 1, 0.5),
                     (1, 1, 0, 0.5), (1, 0, 1, 0.5)]
        for blob in blobs:
            by, bx, bz, r, ch, t, intensity = blob
            mesh = gl.MeshData.sphere(rows=10, cols=20, radius=r)
            base = ch_colors[int(ch) % len(ch_colors)]
            color = base if t == ct else tuple(c * 0.5 for c in base[:3]) + (base[3] * 0.5,)
            item = gl.GLMeshItem(meshdata=mesh, smooth=True, color=color, shader="shaded")
            item.translate(bz, bx, by)
            self.blobGLView.addItem(item)
            self.blob_items.append(item)
        self.blobGLView.update()

    def _toggle_blob_results(self):
        if self.blob_results_dialog.isVisible():
            self.blob_results_dialog.hide()
            self.showBlobResultsButton.setText("Show Blob Results")
        else:
            if hasattr(self, "all_detected_blobs"):
                self.blob_results_dialog.update_results(self.all_detected_blobs)
            self.blob_results_dialog.show()
            self.showBlobResultsButton.setText("Hide Blob Results")

    def _analyze_blobs(self):
        if hasattr(self, "all_detected_blobs") and self.all_detected_blobs is not None:
            ba = BlobAnalyzer(self.all_detected_blobs)
            dlg = BlobAnalysisDialog(ba, self)
            dlg.show()
        else:
            QMessageBox.warning(self, "No Blobs Detected", "Please detect blobs before running analysis.")

    def _show_time_series(self):
        if hasattr(self, "all_detected_blobs") and self.all_detected_blobs is not None:
            TimeSeriesDialog(BlobAnalyzer(self.all_detected_blobs), self).exec_()
        else:
            QMessageBox.warning(self, "No Data", "Please detect blobs first.")

    # ------------------------------------------------------------------
    # Playback
    # ------------------------------------------------------------------

    def _advance_time_point(self):
        ct = self.timeSlider.value()
        if ct < self.timeSlider.maximum():
            self.timeSlider.setValue(ct + 1)
        elif self.loopCheckBox.isChecked():
            self.timeSlider.setValue(0)
        else:
            self.playbackTimer.stop()
            self.playPauseButton.setText("Play")

    def _update_time_point(self, value):
        if self.data is not None:
            self.currentTimePoint = value
            self._update_views()
            self._create_3d_visualization()
            self._update_blob_visualization()

    def _toggle_playback(self):
        if self.playbackTimer.isActive():
            self.playbackTimer.stop()
            self.playPauseButton.setText("Play")
        else:
            self.playbackTimer.start(int(1000 / self.speedSpinBox.value()))
            self.playPauseButton.setText("Pause")

    def _update_playback_speed(self, value):
        if self.playbackTimer.isActive():
            self.playbackTimer.setInterval(int(1000 / value))

    # ------------------------------------------------------------------
    # Misc UI
    # ------------------------------------------------------------------

    def _update_threshold(self, _value):
        if self.data is not None:
            self._update_views()
            self._create_3d_visualization()

    def _update_scatter_size(self, _value):
        self._update_views()
        self._create_3d_visualization()

    def _toggle_slice_markers(self, state):
        if state == Qt.Checked:
            self._update_slice_markers()
        else:
            for attr in ["x_marker", "y_marker", "z_marker"]:
                if hasattr(self, attr):
                    self.glView.removeItem(getattr(self, attr))
                    delattr(self, attr)
            self.glView.update()

    def _update_clip_plane(self, value):
        try:
            clip_pos = (value / 100) * 30
            mask = self.scatter.pos[:, 2] <= clip_pos
            self.scatter.setData(pos=self.scatter.pos[mask], color=self.scatter.color[mask])
        except Exception as e:
            self.logger.error(f"Error updating clip plane: {str(e)}")

    def _update_ui_for_new_data(self):
        if self.data is None:
            return
        self.timeSlider.setMaximum(self.data.shape[0] - 1)
        nc = self.data.shape[1]
        for i in reversed(range(self.channelControlsLayout.count())):
            self.channelControlsLayout.itemAt(i).widget().setParent(None)
        self.channelControls.clear()
        for i in range(nc):
            row_layout = QHBoxLayout()
            row_layout.addWidget(QLabel(f"Channel {i + 1}:"))
            vis = QCheckBox("Visible")
            vis.setChecked(True)
            vis.stateChanged.connect(lambda: (self._update_views(), self._create_3d_visualization()))
            row_layout.addWidget(vis)
            slider = QSlider(Qt.Horizontal)
            slider.setRange(0, 100)
            slider.setValue(100)
            slider.valueChanged.connect(lambda: (self._update_views(), self._create_3d_visualization()))
            row_layout.addWidget(slider)
            self.channelControls.append((vis, slider))
            cw = QWidget()
            cw.setLayout(row_layout)
            self.channelControlsLayout.addWidget(cw)
        self._update_views()
        self._create_3d_visualization()

    def _auto_scale_views(self):
        if self.data is None:
            return
        z, y, x = self.data.shape[2:]
        center = QVector3D(x / 2, y / 2, z / 2)
        diag = np.sqrt(x ** 2 + y ** 2 + z ** 2)
        for view in [self.glView, self.blobGLView]:
            view.setCameraPosition(pos=center, distance=diag * 1.2, elevation=30, azimuth=45)
            view.opts["center"] = center
            view.update()

    def _set_top_down(self):
        for v in [self.glView, self.blobGLView]:
            v.setCameraPosition(elevation=90, azimuth=0); v.update()

    def _set_side(self):
        for v in [self.glView, self.blobGLView]:
            v.setCameraPosition(elevation=0, azimuth=0); v.update()

    def _set_front(self):
        for v in [self.glView, self.blobGLView]:
            v.setCameraPosition(elevation=0, azimuth=90); v.update()

    def _setup_channel_controls_widget(self):
        self.channelControlsWidget = QWidget()
        self.channelControlsLayout = QVBoxLayout(self.channelControlsWidget)
        self.channelControls = []

    # ------------------------------------------------------------------
    # 3-D mouse interaction
    # ------------------------------------------------------------------

    def _connect_view_events(self):
        for view in [self.glView, self.blobGLView]:
            if view is not None:
                view.installEventFilter(self)

    def eventFilter(self, source, event):
        if source in [self.glView, self.blobGLView]:
            etype = event.type()
            if etype == QEvent.MouseButtonPress:
                self._on_3d_mouse_press(event, source); return True
            elif etype == QEvent.MouseButtonRelease:
                self._on_3d_mouse_release(event, source); return True
            elif etype == QEvent.MouseMove:
                self._on_3d_mouse_move(event, source); return True
            elif etype == QEvent.Wheel:
                self._on_3d_wheel(event, source); return True
        return super().eventFilter(source, event)

    def _on_3d_mouse_press(self, event, source=None):
        self.lastPos = event.pos()

    def _on_3d_mouse_release(self, event, source=None):
        self.lastPos = None

    def _on_3d_mouse_move(self, event, source=None):
        if self.lastPos is None:
            return
        diff = event.pos() - self.lastPos
        self.lastPos = event.pos()
        if event.buttons() == Qt.LeftButton:
            self._rotate_3d(diff.x(), diff.y(), source)
        elif event.buttons() == Qt.MidButton:
            self._pan_3d(diff.x(), diff.y(), source)

    def _on_3d_wheel(self, event, source=None):
        self._zoom_3d(event.angleDelta().y(), source)

    def _rotate_3d(self, dx, dy, active):
        views = [self.glView, self.blobGLView] if self.syncViewsCheck.isChecked() else [active]
        for v in views:
            if v and hasattr(v, "opts"):
                v.opts["elevation"] -= dy * 0.5
                v.opts["azimuth"] += dx * 0.5
                v.update()

    def _pan_3d(self, dx, dy, active):
        views = [self.glView, self.blobGLView] if self.syncViewsCheck.isChecked() else [active]
        for v in views:
            if v and hasattr(v, "pan"):
                v.pan(dx, dy, 0, relative="view")

    def _zoom_3d(self, delta, active):
        views = [self.glView, self.blobGLView] if self.syncViewsCheck.isChecked() else [active]
        for v in views:
            if v and hasattr(v, "opts"):
                v.opts["fov"] *= 0.999 ** delta
                v.update()

    def _check_view_state(self):
        self.logger.debug(f"glView: {self.glView}, blobGLView: {self.blobGLView}")

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def exportProcessedData(self):
        fn, _ = QFileDialog.getSaveFileName(self, "Export Processed Data", "", "TIFF Files (*.tiff);;NumPy Files (*.npy)")
        if fn:
            if fn.endswith(".tiff"):
                tifffile.imwrite(fn, self.data)
            elif fn.endswith(".npy"):
                np.save(fn, self.data)

    def exportScreenshot(self):
        fn, _ = QFileDialog.getSaveFileName(self, "Save Screenshot", "", "PNG Files (*.png)")
        if fn:
            QApplication.primaryScreen().grabWindow(self.winId()).save(fn, "png")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def closeEvent(self, event):
        if hasattr(self, "playbackTimer"):
            self.playbackTimer.stop()
        self.logger.info("Application closed")
        if self.biological_simulation_window:
            self.biological_simulation_window.close()
        super().closeEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w = self.width()
        lw = w // 3
        rw = w - lw
        self.resizeDocks([self.dockXY, self.dockXZ, self.dockYZ], [lw] * 3, Qt.Horizontal)
        cw = rw // 4
        self.resizeDocks([self.dock3D], [rw - cw], Qt.Horizontal)
        self.resizeDocks(
            [self.dockDataGeneration, self.dockVisualizationControl, self.dockPlaybackControl],
            [cw] * 3, Qt.Horizontal,
        )
