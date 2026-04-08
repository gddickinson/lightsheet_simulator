"""
Data generation and volume processing for the lightsheet simulator.

Contains DataGenerator (synthetic volume/time-series creation, I/O) and
VolumeProcessor (threshold, filter, statistics).
"""

import logging
import numpy as np
import tifffile
from typing import Tuple, Any

from scipy.ndimage import rotate, gaussian_filter


class VolumeProcessor:
    """Basic volume processing operations (threshold, filter, statistics)."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def apply_threshold(self, data, threshold):
        """Zero out voxels below *threshold*."""
        try:
            return np.where(data > threshold, data, 0)
        except Exception as e:
            self.logger.error(f"Error in applying threshold: {str(e)}")
            return data

    def apply_gaussian_filter(self, data, sigma):
        """Apply a Gaussian blur with the given *sigma*."""
        try:
            return gaussian_filter(data, sigma)
        except ImportError:
            self.logger.error("SciPy not installed. Cannot apply Gaussian filter.")
            return data
        except Exception as e:
            self.logger.error(f"Error in applying Gaussian filter: {str(e)}")
            return data

    def calculate_statistics(self, data):
        """Return basic statistics dict for *data*."""
        try:
            stats = {
                "mean": np.mean(data),
                "std": np.std(data),
                "min": np.min(data),
                "max": np.max(data),
            }
            self.logger.info(f"Statistics calculated: {stats}")
            return stats
        except Exception as e:
            self.logger.error(f"Error in calculating statistics: {str(e)}")
            return {}


class DataGenerator:
    """Creates synthetic fluorescence volumes and time-series, with I/O helpers."""

    def __init__(self):
        self.data = None
        self.metadata: dict = {}
        self.logger = logging.getLogger(__name__)

    # ------------------------------------------------------------------
    # Volume generation
    # ------------------------------------------------------------------

    def generate_volume(
        self,
        size: Tuple[int, int, int] = (100, 100, 30),
        num_blobs: int = 30,
        intensity_range: Tuple[float, float] = (0.8, 1.0),
        sigma_range: Tuple[float, float] = (2, 6),
        noise_level: float = 0.02,
    ) -> np.ndarray:
        """Generate a single volume of synthetic blob data."""
        volume = np.zeros(size)
        for _ in range(num_blobs):
            bx, by, bz = [np.random.randint(0, s) for s in size]
            sigma = np.random.uniform(*sigma_range)
            intensity = np.random.uniform(*intensity_range)
            xg, yg, zg = np.ogrid[-bx : size[0] - bx, -by : size[1] - by, -bz : size[2] - bz]
            blob = np.exp(-(xg * xg + yg * yg + zg * zg) / (2 * sigma * sigma))
            volume += intensity * blob
        volume += np.random.normal(0, noise_level, size)
        return np.clip(volume, 0, 1)

    def generate_multi_channel_volume(
        self,
        size=(100, 100, 30),
        num_channels=2,
        num_blobs=30,
        intensity_range=(0.5, 1.0),
        sigma_range=(2, 6),
        noise_level=0.02,
    ):
        """Generate a multi-channel volume."""
        volume = np.zeros((num_channels, *size))
        for c in range(num_channels):
            for _ in range(num_blobs):
                bx, by, bz = [np.random.randint(0, s) for s in size]
                sigma = np.random.uniform(*sigma_range)
                intensity = np.random.uniform(*intensity_range)
                xg, yg, zg = np.ogrid[-bx : size[0] - bx, -by : size[1] - by, -bz : size[2] - bz]
                blob = np.exp(-(xg * xg + yg * yg + zg * zg) / (2 * sigma * sigma))
                volume[c] += intensity * blob
            volume[c] += np.random.normal(0, noise_level, size)
            volume[c] = np.clip(volume[c], 0, 1)
        return volume

    def _generate_single_volume(
        self,
        size: Tuple[int, int, int],
        blob_positions: np.ndarray,
        blob_velocities: np.ndarray,
        intensity_range: Tuple[float, float],
        sigma_range: Tuple[float, float],
        noise_level: float,
    ) -> np.ndarray:
        z, y, x = size
        volume = np.zeros((z, y, x))
        for i, (bz, by, bx) in enumerate(blob_positions):
            sigma = np.random.uniform(*sigma_range)
            intensity = np.random.uniform(*intensity_range)
            zz, yy, xx = np.ogrid[
                max(0, int(bz - 3 * sigma)) : min(z, int(bz + 3 * sigma)),
                max(0, int(by - 3 * sigma)) : min(y, int(by + 3 * sigma)),
                max(0, int(bx - 3 * sigma)) : min(x, int(bx + 3 * sigma)),
            ]
            blob = np.exp(-((zz - bz) ** 2 + (yy - by) ** 2 + (xx - bx) ** 2) / (2 * sigma * sigma))
            volume[zz, yy, xx] += intensity * blob
        volume += np.random.normal(0, noise_level, (z, y, x))
        return np.clip(volume, 0, 1)

    # ------------------------------------------------------------------
    # Time-series generation
    # ------------------------------------------------------------------

    def generate_time_series(
        self,
        num_volumes: int,
        size: Tuple[int, int, int] = (100, 100, 30),
        num_blobs: int = 30,
        intensity_range: Tuple[float, float] = (0.8, 1.0),
        sigma_range: Tuple[float, float] = (2, 6),
        noise_level: float = 0.02,
        movement_speed: float = 1.0,
    ) -> np.ndarray:
        """Generate a time series of volumes with moving blobs."""
        time_series = np.zeros((num_volumes, *size))
        blob_positions = np.random.rand(num_blobs, 3) * np.array(size)
        blob_velocities = np.random.randn(num_blobs, 3) * movement_speed

        for t in range(num_volumes):
            volume = np.zeros(size)
            for i in range(num_blobs):
                bx, by, bz = blob_positions[i]
                sigma = np.random.uniform(*sigma_range)
                intensity = np.random.uniform(*intensity_range)
                xg, yg, zg = np.ogrid[-bx : size[0] - bx, -by : size[1] - by, -bz : size[2] - bz]
                blob = np.exp(-(xg * xg + yg * yg + zg * zg) / (2 * sigma * sigma))
                volume += intensity * blob
                blob_positions[i] += blob_velocities[i]
                blob_positions[i] %= size
            volume += np.random.normal(0, noise_level, size)
            time_series[t] = np.clip(volume, 0, 1)

        self.data = time_series
        return time_series

    def generate_multi_channel_time_series(
        self,
        num_volumes: int,
        num_channels: int = 2,
        size: Tuple[int, int, int] = (30, 100, 100),
        num_blobs: int = 30,
        intensity_range: Tuple[float, float] = (0.5, 1.0),
        sigma_range: Tuple[float, float] = (2, 6),
        noise_level: float = 0.02,
        movement_speed: float = 1.0,
    ) -> np.ndarray:
        """Generate a multi-channel time series with moving blobs."""
        z, y, x = size
        time_series = np.zeros((num_volumes, num_channels, z, y, x))
        blob_positions = np.random.rand(num_channels, num_blobs, 3) * np.array([z, y, x])
        blob_velocities = np.random.randn(num_channels, num_blobs, 3) * movement_speed

        for t in range(num_volumes):
            for c in range(num_channels):
                volume = self._generate_single_volume(
                    size, blob_positions[c], blob_velocities[c],
                    intensity_range, sigma_range, noise_level,
                )
                time_series[t, c] = volume
                blob_positions[c] += blob_velocities[c]
                blob_positions[c] %= [z, y, x]

        self.data = time_series
        self.logger.info(f"Generated time series with shape: {time_series.shape}")
        return time_series

    def generate_structured_multi_channel_time_series(
        self,
        num_volumes,
        num_channels=2,
        size=(30, 100, 100),
        num_blobs=30,
        intensity_range=(0.5, 1.0),
        sigma_range=(2, 6),
        noise_level=0.02,
        movement_speed=1.0,
        channel_ranges=None,
    ):
        """Generate a structured multi-channel time series with per-channel spatial ranges."""
        z, y, x = size
        time_series = np.zeros((num_volumes, num_channels, z, y, x))

        if channel_ranges is None:
            channel_ranges = [((0, x), (0, y), (0, z)) for _ in range(num_channels)]

        blob_positions = []
        blob_velocities = []
        for c in range(num_channels):
            x_range, y_range, z_range = channel_ranges[c]
            cb = np.random.rand(num_blobs, 3)
            cb[:, 0] = cb[:, 0] * (x_range[1] - x_range[0]) + x_range[0]
            cb[:, 1] = cb[:, 1] * (y_range[1] - y_range[0]) + y_range[0]
            cb[:, 2] = cb[:, 2] * (z_range[1] - z_range[0]) + z_range[0]
            blob_positions.append(cb)
            blob_velocities.append(np.random.randn(num_blobs, 3) * movement_speed)

        for t in range(num_volumes):
            for c in range(num_channels):
                volume = np.zeros((z, y, x))
                x_range, y_range, z_range = channel_ranges[c]
                for i in range(num_blobs):
                    bx, by, bz = blob_positions[c][i]
                    sigma = np.random.uniform(*sigma_range)
                    intensity = np.random.uniform(*intensity_range)
                    xx, yy, zz = np.ogrid[
                        max(0, int(bx - 3 * sigma)) : min(x, int(bx + 3 * sigma)),
                        max(0, int(by - 3 * sigma)) : min(y, int(by + 3 * sigma)),
                        max(0, int(bz - 3 * sigma)) : min(z, int(bz + 3 * sigma)),
                    ]
                    blob = np.exp(-((xx - bx) ** 2 + (yy - by) ** 2 + (zz - bz) ** 2) / (2 * sigma * sigma))
                    volume[zz, yy, xx] += intensity * blob
                    blob_positions[c][i] += blob_velocities[c][i]
                    blob_positions[c][i][0] = np.clip(blob_positions[c][i][0], x_range[0], x_range[1])
                    blob_positions[c][i][1] = np.clip(blob_positions[c][i][1], y_range[0], y_range[1])
                    blob_positions[c][i][2] = np.clip(blob_positions[c][i][2], z_range[0], z_range[1])
                volume += np.random.normal(0, noise_level, (z, y, x))
                time_series[t, c] = np.clip(volume, 0, 1)

        self.data = time_series
        return time_series

    # ------------------------------------------------------------------
    # Angular recording
    # ------------------------------------------------------------------

    def simulate_angular_recording(self, angle: float) -> np.ndarray:
        """Simulate an angular recording by rotating the volume."""
        if self.data is None:
            raise ValueError("No data to rotate. Generate data first.")
        return rotate(self.data, angle, axes=(1, 2), reshape=False, mode="constant", cval=0)

    def correct_angular_recording(self, angle: float) -> np.ndarray:
        """Correct an angular recording by rotating the volume back."""
        if self.data is None:
            raise ValueError("No data to correct. Generate data first.")
        return rotate(self.data, -angle, axes=(1, 2), reshape=False, mode="constant", cval=0)

    # ------------------------------------------------------------------
    # I/O
    # ------------------------------------------------------------------

    def save_tiff(self, filename: str):
        """Save the current data as a TIFF stack."""
        if self.data is None:
            raise ValueError("No data to save. Generate data first.")
        try:
            tifffile.imwrite(filename, self.data)
        except OSError as e:
            self.logger.error(f"Failed to write TIFF file '{filename}': {e}")
            raise

    def save_numpy(self, filename: str):
        """Save the current data as a numpy .npy file."""
        if self.data is None:
            raise ValueError("No data to save. Generate data first.")
        try:
            np.save(filename, self.data)
        except OSError as e:
            self.logger.error(f"Failed to write numpy file '{filename}': {e}")
            raise

    def load_tiff(self, filename: str):
        """Load data from a TIFF stack."""
        try:
            self.data = tifffile.imread(filename)
        except OSError as e:
            self.logger.error(f"Failed to read TIFF file '{filename}': {e}")
            raise
        return self.data

    def load_numpy(self, filename: str):
        """Load data from a numpy .npy file."""
        try:
            self.data = np.load(filename)
        except OSError as e:
            self.logger.error(f"Failed to read numpy file '{filename}': {e}")
            raise
        return self.data

    def apply_gaussian_filter(self, sigma: float):
        """Apply a Gaussian filter to the stored data."""
        if self.data is None:
            raise ValueError("No data to filter. Generate or load data first.")
        self.data = gaussian_filter(self.data, sigma)
        return self.data

    def adjust_intensity(self, gamma: float):
        """Apply gamma correction to the stored data."""
        if self.data is None:
            raise ValueError("No data to adjust. Generate or load data first.")
        self.data = np.power(self.data, gamma)
        return self.data

    def get_metadata(self) -> dict:
        """Return metadata about the current dataset."""
        if self.data is None:
            return {}
        self.metadata.update({
            "shape": self.data.shape,
            "dtype": str(self.data.dtype),
            "min": float(np.min(self.data)),
            "max": float(np.max(self.data)),
            "mean": float(np.mean(self.data)),
            "std": float(np.std(self.data)),
        })
        return self.metadata

    def set_metadata(self, key: str, value: Any):
        """Set a metadata value."""
        self.metadata[key] = value
