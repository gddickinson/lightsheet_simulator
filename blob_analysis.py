"""
Blob analysis and visualization dialogs for the lightsheet simulator.

Contains BlobAnalyzer (statistics, colocalization), BlobAnalysisDialog,
BlobResultsDialog, and TimeSeriesDialog.
"""

import numpy as np
from scipy.spatial import cKDTree

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QWidget, QPushButton, QComboBox,
    QTabWidget, QTextEdit, QTableWidget, QTableWidgetItem,
)
from matplotlib import pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import pyqtgraph as pg


class BlobAnalyzer:
    """Statistical analysis of detected blobs across channels and time."""

    def __init__(self, blobs):
        self.blobs = blobs
        self.channels = np.unique(blobs[:, 4]).astype(int)
        self.time_points = np.unique(blobs[:, 5]).astype(int)

    def calculate_nearest_neighbor_distances(self, time_point):
        """Calculate nearest-neighbor distances for all, within-, and between-channel blobs."""
        time_blobs = self.blobs[self.blobs[:, 5] == time_point]
        all_distances = self._calculate_nn_distances(time_blobs[:, :3])
        within = {
            ch: self._calculate_nn_distances(time_blobs[time_blobs[:, 4] == ch][:, :3])
            for ch in self.channels
        }
        between = {}
        for ch1 in self.channels:
            for ch2 in self.channels:
                if ch1 < ch2:
                    b1 = time_blobs[time_blobs[:, 4] == ch1][:, :3]
                    b2 = time_blobs[time_blobs[:, 4] == ch2][:, :3]
                    between[(ch1, ch2)] = self._calculate_cross_distances(b1, b2)
        return all_distances, within, between

    def _calculate_nn_distances(self, points):
        if len(points) < 2:
            return np.array([])
        tree = cKDTree(points)
        distances, _ = tree.query(points, k=2)
        return distances[:, 1]

    def _calculate_cross_distances(self, points1, points2):
        if len(points1) == 0 or len(points2) == 0:
            return np.array([])
        tree = cKDTree(points2)
        distances, _ = tree.query(points1)
        return distances

    def calculate_blob_density(self, volume_size, time_point):
        """Return (overall_density, {channel: density})."""
        time_blobs = self.blobs[self.blobs[:, 5] == time_point]
        total_volume = np.prod(volume_size)
        channel_densities = {
            ch: np.sum(time_blobs[:, 4] == ch) / total_volume for ch in self.channels
        }
        return len(time_blobs) / total_volume, channel_densities

    def calculate_colocalization(self, distance_threshold, time_point):
        """Basic distance-based colocalization between channel pairs."""
        time_blobs = self.blobs[self.blobs[:, 5] == time_point]
        coloc = {}
        for ch1 in self.channels:
            for ch2 in self.channels:
                if ch1 < ch2:
                    b1 = time_blobs[time_blobs[:, 4] == ch1][:, :3]
                    b2 = time_blobs[time_blobs[:, 4] == ch2][:, :3]
                    if len(b1) > 0 and len(b2) > 0:
                        tree = cKDTree(b2)
                        distances, _ = tree.query(b1)
                        coloc[(ch1, ch2)] = np.mean(distances < distance_threshold)
                    else:
                        coloc[(ch1, ch2)] = 0
        return coloc

    def calculate_blob_sizes(self, time_point):
        time_blobs = self.blobs[self.blobs[:, 5] == time_point]
        return {ch: time_blobs[time_blobs[:, 4] == ch][:, 3] for ch in self.channels}

    def calculate_blob_intensities(self, time_point):
        time_blobs = self.blobs[self.blobs[:, 5] == time_point]
        return {ch: time_blobs[time_blobs[:, 4] == ch][:, 6] for ch in self.channels}

    def calculate_advanced_colocalization(self, time_point):
        """Pearson + Manders colocalization for channel pairs."""
        time_blobs = self.blobs[self.blobs[:, 5] == time_point]
        results = {}
        for ch1 in self.channels:
            for ch2 in self.channels:
                if ch1 < ch2:
                    b1 = time_blobs[time_blobs[:, 4] == ch1]
                    b2 = time_blobs[time_blobs[:, 4] == ch2]
                    if len(b1) > 0 and len(b2) > 0:
                        tree1 = cKDTree(b1[:, :3])
                        dist_thresh = np.mean(np.concatenate([b1[:, 3], b2[:, 3]]))
                        distances, indices = tree1.query(b2[:, :3])
                        nearby = distances < dist_thresh
                        i1 = b1[indices[nearby], 6]
                        i2 = b2[nearby, 6]
                        if len(i1) > 1 and len(i2) > 1:
                            pearson = np.corrcoef(i1, i2)[0, 1]
                        else:
                            pearson = np.nan
                        m1 = np.sum(i1) / np.sum(b1[:, 6])
                        m2 = np.sum(i2) / np.sum(b2[:, 6])
                        results[(ch1, ch2)] = {"pearson": pearson, "manders_m1": m1, "manders_m2": m2}
                    else:
                        results[(ch1, ch2)] = {"pearson": np.nan, "manders_m1": np.nan, "manders_m2": np.nan}
        return results


# ---------------------------------------------------------------------------
# Qt Dialogs
# ---------------------------------------------------------------------------

class BlobAnalysisDialog(QDialog):
    """Multi-tab dialog showing blob analysis results."""

    def __init__(self, blob_analyzer, parent=None):
        super().__init__(parent)
        self.blob_analyzer = blob_analyzer
        self.setWindowTitle("Blob Analysis Results")
        self.setGeometry(100, 100, 800, 600)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()
        self.timeComboBox = QComboBox()
        self.timeComboBox.addItems([str(t) for t in self.blob_analyzer.time_points])
        self.timeComboBox.currentIndexChanged.connect(self._update)
        layout.addWidget(self.timeComboBox)
        self.tabWidget = QTabWidget()
        layout.addWidget(self.tabWidget)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)
        self.setLayout(layout)
        self._update()

    def _update(self):
        self.tabWidget.clear()
        tp = int(self.timeComboBox.currentText())
        self._add_distance_tab(tp)
        self._add_density_tab(tp)
        self._add_colocalization_tab(tp)
        self._add_size_tab(tp)
        self._add_intensity_tab(tp)
        self._add_3d_tab(tp)
        self._add_stats_tab(tp)

    def _add_distance_tab(self, tp):
        tab = QWidget()
        layout = QVBoxLayout()
        all_d, within_d, _ = self.blob_analyzer.calculate_nearest_neighbor_distances(tp)
        plt.figure(figsize=(10, 6))
        plt.hist(all_d, bins=50, alpha=0.5, label="All Blobs")
        for ch, d in within_d.items():
            plt.hist(d, bins=50, alpha=0.5, label=f"Channel {ch}")
        plt.xlabel("Nearest Neighbor Distance")
        plt.ylabel("Frequency")
        plt.legend()
        plt.title(f"Nearest Neighbor Distance Distribution (Time: {tp})")
        layout.addWidget(FigureCanvas(plt.gcf()))
        tab.setLayout(layout)
        self.tabWidget.addTab(tab, "Distance Analysis")
        plt.close()

    def _add_density_tab(self, tp):
        tab = QWidget()
        layout = QVBoxLayout()
        overall, by_ch = self.blob_analyzer.calculate_blob_density((30, 100, 100), tp)
        te = QTextEdit()
        te.setReadOnly(True)
        te.append(f"Time Point: {tp}")
        te.append(f"Overall Blob Density: {overall:.6f} blobs/unit^3")
        for ch, d in by_ch.items():
            te.append(f"Channel {ch} Density: {d:.6f} blobs/unit^3")
        layout.addWidget(te)
        tab.setLayout(layout)
        self.tabWidget.addTab(tab, "Density Analysis")

    def _add_colocalization_tab(self, tp):
        tab = QWidget()
        layout = QVBoxLayout()
        basic = self.blob_analyzer.calculate_colocalization(5, tp)
        advanced = self.blob_analyzer.calculate_advanced_colocalization(tp)
        te = QTextEdit()
        te.setReadOnly(True)
        te.append(f"Time Point: {tp}")
        te.append("\nBasic Colocalization:")
        for (c1, c2), val in basic.items():
            te.append(f"Channels {c1} and {c2}: {val:.2%}")
        te.append("\nAdvanced Colocalization:")
        for (c1, c2), r in advanced.items():
            te.append(f"Channels {c1} and {c2}:")
            p = r["pearson"]
            te.append(f"  Pearson's coefficient: {p:.4f}" if not np.isnan(p) else "  Pearson's coefficient: N/A")
            te.append(f"  Manders' M1: {r['manders_m1']:.4f}")
            te.append(f"  Manders' M2: {r['manders_m2']:.4f}")
        layout.addWidget(te)
        tab.setLayout(layout)
        self.tabWidget.addTab(tab, "Colocalization")

    def _add_size_tab(self, tp):
        tab = QWidget()
        layout = QVBoxLayout()
        sizes = self.blob_analyzer.calculate_blob_sizes(tp)
        plt.figure(figsize=(10, 6))
        for ch, s in sizes.items():
            plt.hist(s, bins=50, alpha=0.5, label=f"Channel {ch}")
        plt.xlabel("Blob Size")
        plt.ylabel("Frequency")
        plt.legend()
        plt.title(f"Blob Size Distribution (Time: {tp})")
        layout.addWidget(FigureCanvas(plt.gcf()))
        tab.setLayout(layout)
        self.tabWidget.addTab(tab, "Blob Size Analysis")
        plt.close()

    def _add_intensity_tab(self, tp):
        tab = QWidget()
        layout = QVBoxLayout()
        intensities = self.blob_analyzer.calculate_blob_intensities(tp)
        sizes = self.blob_analyzer.calculate_blob_sizes(tp)
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        for ch in self.blob_analyzer.channels:
            ax1.hist(intensities[ch], bins=50, alpha=0.5, label=f"Channel {ch}")
        ax1.set_xlabel("Intensity")
        ax1.set_ylabel("Frequency")
        ax1.set_title("Blob Intensity Distribution")
        ax1.legend()
        for ch in self.blob_analyzer.channels:
            ax2.scatter(sizes[ch], intensities[ch], alpha=0.5, label=f"Channel {ch}")
        ax2.set_xlabel("Blob Size")
        ax2.set_ylabel("Intensity")
        ax2.set_title("Blob Size vs Intensity")
        ax2.legend()
        layout.addWidget(FigureCanvas(fig))
        tab.setLayout(layout)
        self.tabWidget.addTab(tab, "Intensity Analysis")
        plt.close()

    def _add_3d_tab(self, tp):
        tab = QWidget()
        layout = QVBoxLayout()
        time_blobs = self.blob_analyzer.blobs[self.blob_analyzer.blobs[:, 5] == tp]
        fig = plt.figure(figsize=(8, 8))
        ax = fig.add_subplot(111, projection="3d")
        for ch in self.blob_analyzer.channels:
            cb = time_blobs[time_blobs[:, 4] == ch]
            ax.scatter(cb[:, 0], cb[:, 1], cb[:, 2], s=cb[:, 3] * 10, alpha=0.5, label=f"Channel {ch}")
        ax.set_xlabel("X")
        ax.set_ylabel("Y")
        ax.set_zlabel("Z")
        ax.set_title(f"3D Blob Positions (Time: {tp})")
        ax.legend()
        layout.addWidget(FigureCanvas(fig))
        tab.setLayout(layout)
        self.tabWidget.addTab(tab, "3D Visualization")
        plt.close()

    def _add_stats_tab(self, tp):
        tab = QWidget()
        layout = QVBoxLayout()
        te = QTextEdit()
        te.setReadOnly(True)
        all_d, within_d, _ = self.blob_analyzer.calculate_nearest_neighbor_distances(tp)
        overall_density, ch_densities = self.blob_analyzer.calculate_blob_density((30, 100, 100), tp)
        sizes = self.blob_analyzer.calculate_blob_sizes(tp)
        time_blobs = self.blob_analyzer.blobs[self.blob_analyzer.blobs[:, 5] == tp]

        te.append(f"Statistics for Time Point: {tp}")
        te.append("\nOverall Statistics:")
        te.append(f"Total number of blobs: {len(time_blobs)}")
        te.append(f"Overall blob density: {overall_density:.6f} blobs/unit^3")
        if len(all_d) > 0:
            te.append(f"Mean nearest neighbor distance: {np.mean(all_d):.2f}")
            te.append(f"Median nearest neighbor distance: {np.median(all_d):.2f}")
        else:
            te.append("Not enough blobs to calculate nearest neighbor distances.")

        for ch in self.blob_analyzer.channels:
            te.append(f"\nChannel {ch} Statistics:")
            cb = time_blobs[time_blobs[:, 4] == ch]
            te.append(f"Number of blobs: {len(cb)}")
            te.append(f"Blob density: {ch_densities[ch]:.6f} blobs/unit^3")
            if len(sizes[ch]) > 0:
                te.append(f"Mean blob size: {np.mean(sizes[ch]):.2f}")
                te.append(f"Median blob size: {np.median(sizes[ch]):.2f}")
            else:
                te.append("No blobs detected in this channel.")
            if ch in within_d and len(within_d[ch]) > 0:
                te.append(f"Mean nearest neighbor distance: {np.mean(within_d[ch]):.2f}")
                te.append(f"Median nearest neighbor distance: {np.median(within_d[ch]):.2f}")
            else:
                te.append("Not enough blobs to calculate nearest neighbor distances.")

        layout.addWidget(te)
        tab.setLayout(layout)
        self.tabWidget.addTab(tab, "Statistics")


class BlobResultsDialog(QDialog):
    """Simple table dialog showing blob detection results."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Blob Detection Results")
        self.layout = QVBoxLayout(self)
        self.table = QTableWidget()
        self.layout.addWidget(self.table)

    def update_results(self, blobs):
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["X", "Y", "Z", "Size", "Channel", "Time"])
        self.table.setRowCount(len(blobs))
        for i, blob in enumerate(blobs):
            y, x, z, r, channel, t = blob[:6]
            self.table.setItem(i, 0, QTableWidgetItem(f"{x:.2f}"))
            self.table.setItem(i, 1, QTableWidgetItem(f"{y:.2f}"))
            self.table.setItem(i, 2, QTableWidgetItem(f"{z:.2f}"))
            self.table.setItem(i, 3, QTableWidgetItem(f"{r:.2f}"))
            self.table.setItem(i, 4, QTableWidgetItem(f"{int(channel)}"))
            self.table.setItem(i, 5, QTableWidgetItem(f"{int(t)}"))


class TimeSeriesDialog(QDialog):
    """Dialog plotting blob counts over time per channel."""

    def __init__(self, blob_analyzer, parent=None):
        super().__init__(parent)
        self.blob_analyzer = blob_analyzer
        self.setWindowTitle("Time Series Analysis")
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()
        plot_widget = pg.PlotWidget()
        layout.addWidget(plot_widget)
        tps = np.unique(self.blob_analyzer.blobs[:, 5])
        channels = np.unique(self.blob_analyzer.blobs[:, 4])
        for channel in channels:
            counts = [
                np.sum((self.blob_analyzer.blobs[:, 5] == t) & (self.blob_analyzer.blobs[:, 4] == channel))
                for t in tps
            ]
            plot_widget.plot(tps, counts, pen=(int(channel), len(channels)), name=f"Channel {int(channel)}")
        plot_widget.setLabel("left", "Number of Blobs")
        plot_widget.setLabel("bottom", "Time Point")
        plot_widget.addLegend()
        self.setLayout(layout)
