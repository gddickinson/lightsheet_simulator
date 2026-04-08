"""
Biological simulation engine for the lightsheet simulator.

Contains the BiologicalSimulator class which generates synthetic 3D biological
datasets including cell shapes, organelles, protein diffusion, and calcium signals.
"""

import logging
import numpy as np
from typing import Tuple, Dict

from scipy.ndimage import (
    center_of_mass,
    binary_dilation,
    gaussian_filter,
)

from utils import line_3d


class BiologicalSimulator:
    """Generates synthetic 3D biological volumes for lightsheet microscopy testing.

    Args:
        size: Tuple (z, y, x) specifying volume dimensions.
        num_time_points: Number of time frames to simulate.
    """

    def __init__(self, size, num_time_points):
        self.size = size
        self.num_time_points = num_time_points
        self.logger = logging.getLogger(__name__)
        self.call_count = 0

    # ------------------------------------------------------------------
    # Protein diffusion / transport
    # ------------------------------------------------------------------

    def simulate_protein_diffusion(self, D, initial_concentration):
        """Simulate protein diffusion using iterative Gaussian blurring.

        Args:
            D: Diffusion coefficient.
            initial_concentration: 3-D array matching ``self.size``.

        Returns:
            4-D array (time, z, y, x) of concentrations.
        """
        self.call_count += 1
        try:
            self.logger.info(f"Starting protein diffusion simulation with D={D}")
            self.logger.info(f"Simulator size: {self.size}")
            self.logger.info(f"Initial concentration shape: {initial_concentration.shape}")

            if initial_concentration.shape != self.size:
                raise ValueError(
                    f"Initial concentration shape {initial_concentration.shape} "
                    f"does not match simulator size {self.size}"
                )

            result = np.zeros((self.num_time_points, *self.size))
            result[0] = initial_concentration

            for t in range(1, self.num_time_points):
                result[t] = gaussian_filter(result[t - 1], sigma=np.sqrt(2 * D))

            self.logger.info("Protein diffusion simulation completed successfully")
            self.logger.info(f"Result shape: {result.shape}")
            return result

        except ValueError:
            raise
        except Exception as e:
            self.logger.error(f"Error in protein diffusion simulation: {str(e)}")
            raise

    def simulate_active_transport(
        self,
        velocity: Tuple[float, float, float],
        cargo_concentration: np.ndarray,
    ) -> np.ndarray:
        """Simulate active transport of cargo along cytoskeleton.

        Args:
            velocity: Velocity vector for transport (vz, vy, vx).
            cargo_concentration: Initial cargo concentration array.

        Returns:
            4-D array (time, z, y, x) of cargo concentrations.
        """
        try:
            result = np.zeros((self.num_time_points, *self.size))
            result[0] = cargo_concentration
            for t in range(1, self.num_time_points):
                result[t] = np.roll(
                    result[t - 1],
                    shift=(int(velocity[0]), int(velocity[1]), int(velocity[2])),
                    axis=(0, 1, 2),
                )
            return result
        except Exception as e:
            self.logger.error(f"Error in active transport simulation: {str(e)}")
            raise

    # ------------------------------------------------------------------
    # Cellular structures
    # ------------------------------------------------------------------

    def generate_cellular_structure(self, structure_type: str) -> np.ndarray:
        """Generate a 3D representation of a cellular structure.

        Args:
            structure_type: One of 'nucleus', 'mitochondria', 'actin', 'lysosomes'.

        Returns:
            3-D array representing the cellular structure.
        """
        try:
            if structure_type == "nucleus":
                return self._generate_nucleus()
            elif structure_type == "mitochondria":
                return self._generate_mitochondria()
            elif structure_type == "actin":
                return self._generate_actin()
            elif structure_type == "lysosomes":
                return self._generate_lysosomes()
            else:
                raise ValueError(f"Unknown structure type: {structure_type}")
        except Exception as e:
            self.logger.error(f"Error generating cellular structure: {str(e)}")
            raise

    def generate_cell_membrane(self, center, radius, thickness=1):
        """Generate a cell plasma membrane.

        Args:
            center: (z, y, x) coordinates of the cell center.
            radius: Radius of the cell.
            thickness: Membrane thickness in pixels.

        Returns:
            3-D boolean array of the membrane.
        """
        try:
            self.logger.info(f"Generating cell membrane at {center} with radius {radius}")
            z, y, x = np.ogrid[: self.size[0], : self.size[1], : self.size[2]]
            dist = np.sqrt(
                (z - center[0]) ** 2 + (y - center[1]) ** 2 + (x - center[2]) ** 2
            )
            membrane = (dist >= radius - thickness / 2) & (dist <= radius + thickness / 2)
            self.logger.info("Cell membrane generated successfully")
            return membrane.astype(float)
        except Exception as e:
            self.logger.error(f"Error in cell membrane generation: {str(e)}")
            raise

    def generate_nucleus(self, cell_interior, soma_center, nucleus_radius, pixel_size=(1, 1, 1)):
        """Generate a cell nucleus within the cell interior.

        Args:
            cell_interior: Boolean volume of the cell interior.
            soma_center: (z, y, x) center of the soma.
            nucleus_radius: Desired nucleus radius in pixels.
            pixel_size: Anisotropic pixel sizes (z, y, x).

        Returns:
            Tuple of (nucleus_volume, nucleus_center).
        """
        try:
            self.logger.info(f"Generating cell nucleus at {soma_center} with radius {nucleus_radius}")
            soma_radius = min(self.size) // 4
            nucleus_radius = min(max(1, nucleus_radius), soma_radius // 3)

            new_center = self.find_suitable_center(cell_interior, soma_center, nucleus_radius)
            if new_center is None:
                self.logger.warning("Unable to find suitable location for nucleus.")
                return np.zeros_like(cell_interior), soma_center

            z, y, x = np.ogrid[: self.size[0], : self.size[1], : self.size[2]]
            dist = np.sqrt(
                ((z - new_center[0]) * pixel_size[0]) ** 2
                + ((y - new_center[1]) * pixel_size[1]) ** 2
                + ((x - new_center[2]) * pixel_size[2]) ** 2
            )
            nucleus = (dist <= nucleus_radius) & (cell_interior > 0)
            self.logger.info(f"Cell nucleus generated. Volume: {np.sum(nucleus)}")
            return nucleus.astype(float), new_center
        except Exception as e:
            self.logger.error(f"Error in cell nucleus generation: {str(e)}")
            raise

    def find_suitable_center(self, cell_shape, soma_center, nucleus_radius):
        """Find a center point inside *cell_shape* that can fit a sphere of *nucleus_radius*."""
        z, y, x = np.ogrid[: self.size[0], : self.size[1], : self.size[2]]
        dist_from_center = np.sqrt(
            (z - soma_center[0]) ** 2
            + (y - soma_center[1]) ** 2
            + (x - soma_center[2]) ** 2
        )
        priority_map = np.where(cell_shape, -dist_from_center, -np.inf)

        search_radius = 0
        max_search_radius = max(self.size)
        while search_radius < max_search_radius:
            potential_centers = np.argwhere(
                (dist_from_center <= search_radius) & (cell_shape > 0)
            )
            if len(potential_centers) > 0:
                priorities = priority_map[tuple(potential_centers.T)]
                sorted_centers = potential_centers[np.argsort(priorities)]
                for center in sorted_centers:
                    z2, y2, x2 = np.ogrid[: self.size[0], : self.size[1], : self.size[2]]
                    d = np.sqrt(
                        (z2 - center[0]) ** 2
                        + (y2 - center[1]) ** 2
                        + (x2 - center[2]) ** 2
                    )
                    if np.sum((d <= nucleus_radius) & (cell_shape > 0)) >= 7:
                        return center
            search_radius += 1

        if np.sum(cell_shape) > 0:
            return np.array(center_of_mass(cell_shape)).astype(int)
        return None

    def generate_er(self, cell_shape, soma_center, nucleus_radius, er_density=0.1, pixel_size=(1, 1, 1)):
        """Generate endoplasmic reticulum within the cytoplasm.

        Args:
            cell_shape: Boolean volume of the entire cell.
            soma_center: (z, y, x) center of the soma.
            nucleus_radius: Radius of the nucleus to exclude.
            er_density: Probability of ER voxels in cytoplasm.
            pixel_size: Anisotropic pixel sizes.

        Returns:
            3-D float array of ER signal.
        """
        try:
            self.logger.info(f"Generating ER with density {er_density}")
            z, y, x = np.ogrid[: self.size[0], : self.size[1], : self.size[2]]
            dist = np.sqrt(
                ((z - soma_center[0]) * pixel_size[0]) ** 2
                + ((y - soma_center[1]) * pixel_size[1]) ** 2
                + ((x - soma_center[2]) * pixel_size[2]) ** 2
            )
            cell_mask = cell_shape > 0
            nucleus_mask = dist <= nucleus_radius
            cytoplasm_mask = cell_mask & ~nucleus_mask
            self.logger.info(
                f"Cell volume: {np.sum(cell_mask)}, Nucleus volume: {np.sum(nucleus_mask)}, "
                f"Cytoplasm volume: {np.sum(cytoplasm_mask)}"
            )
            er = cytoplasm_mask & (np.random.rand(*self.size) < er_density)
            near_nucleus = (dist > nucleus_radius) & (dist <= nucleus_radius * 1.5)
            er |= near_nucleus & cytoplasm_mask & (np.random.rand(*self.size) < er_density * 2)
            self.logger.info(f"ER generated successfully. ER volume: {np.sum(er)}")
            return er.astype(float)
        except Exception as e:
            self.logger.error(f"Error in ER generation: {str(e)}")
            raise

    def generate_cell_shape(self, cell_type, size, pixel_size=(1, 1, 1),
                            membrane_thickness=1, soma_center=None, **kwargs):
        """Generate the 3-D shape of a cell.

        Args:
            cell_type: One of 'spherical', 'neuron', 'epithelial', 'muscle'.
            size: Volume dimensions (z, y, x).
            pixel_size: Anisotropic pixel sizes.
            membrane_thickness: Thickness of the membrane in pixels.
            soma_center: Optional center override.
            **kwargs: Cell-type-specific parameters.

        Returns:
            Tuple of (cell_shape, cell_interior, cell_membrane) float arrays.
        """
        try:
            self.logger.info(f"Generating {cell_type} cell shape")
            z, y, x = np.ogrid[: size[0], : size[1], : size[2]]
            if soma_center is None:
                soma_center = np.array(size) // 2

            if cell_type == "spherical":
                radius = kwargs.get("cell_radius", min(size) // 4)
                self.logger.info(f"Generating spherical cell with radius {radius}")
                dist = np.sqrt(
                    ((z - soma_center[0]) * pixel_size[0]) ** 2
                    + ((y - soma_center[1]) * pixel_size[1]) ** 2
                    + ((x - soma_center[2]) * pixel_size[2]) ** 2
                )
                cell_interior = dist <= (radius - membrane_thickness)
                cell_membrane = (dist <= radius) & (dist > (radius - membrane_thickness))
                cell_shape = cell_interior | cell_membrane

            elif cell_type == "neuron":
                soma_radius = kwargs.get("soma_radius", min(size) // 8)
                axon_length = kwargs.get("axon_length", size[2] // 2)
                axon_width = kwargs.get("axon_width", size[1] // 20)
                num_dendrites = kwargs.get("num_dendrites", 5)
                dendrite_length = kwargs.get("dendrite_length", size[1] // 4)
                self.logger.info(f"Generating neuron with soma radius {soma_radius}")

                dist_from_soma = np.sqrt(
                    ((z - soma_center[0]) * pixel_size[0]) ** 2
                    + ((y - soma_center[1]) * pixel_size[1]) ** 2
                    + ((x - soma_center[2]) * pixel_size[2]) ** 2
                )
                soma = dist_from_soma <= soma_radius

                axon_start = soma_center[2] + soma_radius
                axon = (
                    (x >= axon_start)
                    & (x < axon_start + axon_length)
                    & (np.abs(y - soma_center[1]) <= axon_width // 2)
                    & (np.abs(z - soma_center[0]) <= axon_width // 2)
                )

                axon_end = axon_start + axon_length
                terminals = np.zeros_like(soma, dtype=bool)
                for _ in range(3):
                    tc = (
                        soma_center[0] + np.random.randint(-axon_width, axon_width),
                        soma_center[1] + np.random.randint(-axon_width, axon_width),
                        axon_end + np.random.randint(0, size[2] // 10),
                    )
                    tr = axon_width // 2
                    td = np.sqrt(
                        ((z - tc[0]) * pixel_size[0]) ** 2
                        + ((y - tc[1]) * pixel_size[1]) ** 2
                        + ((x - tc[2]) * pixel_size[2]) ** 2
                    )
                    terminals |= td <= tr

                dendrites = np.zeros_like(soma, dtype=bool)
                for _ in range(num_dendrites):
                    angle = np.random.uniform(0, 2 * np.pi)
                    end_pt = (
                        int(soma_center[0] + dendrite_length * np.sin(angle) * np.cos(angle)),
                        int(soma_center[1] + dendrite_length * np.sin(angle)),
                        int(soma_center[2] - dendrite_length * np.cos(angle)),
                    )
                    rr, cc, zz = line_3d(
                        soma_center[0], soma_center[1], soma_center[2],
                        end_pt[0], end_pt[1], end_pt[2],
                    )
                    dendrites[rr, cc, zz] = True
                dendrites = binary_dilation(dendrites, iterations=2)

                cell_interior = soma | axon | terminals | dendrites
                cell_shape = binary_dilation(cell_interior, iterations=membrane_thickness)
                cell_membrane = cell_shape & ~cell_interior

            elif cell_type == "epithelial":
                height = size[0] // 3
                outer_shape = z < height
                inner_shape = z < (height - membrane_thickness)
                cell_shape = outer_shape ^ inner_shape
                cell_interior = inner_shape
                cell_membrane = cell_shape

            elif cell_type == "muscle":
                outer_shape = (
                    ((y - soma_center[1]) * pixel_size[1]) ** 2
                    + ((z - soma_center[0]) * pixel_size[0]) ** 2
                    <= (min(size) // 4) ** 2
                )
                inner_shape = (
                    ((y - soma_center[1]) * pixel_size[1]) ** 2
                    + ((z - soma_center[0]) * pixel_size[0]) ** 2
                    <= (min(size) // 4 - membrane_thickness) ** 2
                )
                cell_shape = outer_shape ^ inner_shape
                cell_interior = inner_shape
                cell_membrane = cell_shape
            else:
                raise ValueError(f"Unknown cell type: {cell_type}")

            non_zero = np.argwhere(cell_shape > 0)
            self.logger.info(
                f"Non-zero cell shape coordinates: min={non_zero.min(axis=0)}, max={non_zero.max(axis=0)}"
            )
            self.logger.info(f"{cell_type} cell shape generated successfully")
            return cell_shape.astype(float), cell_interior.astype(float), cell_membrane.astype(float)

        except Exception as e:
            self.logger.error(f"Error in cell shape generation: {str(e)}")
            raise

    # ------------------------------------------------------------------
    # Calcium signaling (stubs)
    # ------------------------------------------------------------------

    def simulate_calcium_signal(self, signal_type: str, params: Dict) -> np.ndarray:
        """Simulate calcium signaling events.

        Args:
            signal_type: One of 'blip', 'puff', 'wave'.
            params: Signal-type-specific parameters.

        Returns:
            4-D array (time, z, y, x) of calcium concentrations.
        """
        try:
            if signal_type == "blip":
                return self._simulate_calcium_blip(params)
            elif signal_type == "puff":
                return self._simulate_calcium_puff(params)
            elif signal_type == "wave":
                return self._simulate_calcium_wave(params)
            else:
                raise ValueError(f"Unknown calcium signal type: {signal_type}")
        except Exception as e:
            self.logger.error(f"Error in calcium signal simulation: {str(e)}")
            raise

    # Stub implementations
    def _generate_nucleus(self) -> np.ndarray:
        pass

    def _generate_mitochondria(self) -> np.ndarray:
        pass

    def _generate_actin(self) -> np.ndarray:
        pass

    def _generate_lysosomes(self) -> np.ndarray:
        pass

    def _simulate_calcium_blip(self, params: Dict) -> np.ndarray:
        pass

    def _simulate_calcium_puff(self, params: Dict) -> np.ndarray:
        pass

    def _simulate_calcium_wave(self, params: Dict) -> np.ndarray:
        pass
