"""
Utility functions for the lightsheet simulator.

Contains the Bresenham 3D line drawing algorithm and other geometric helpers.
"""

import numpy as np


def line_3d(x0, y0, z0, x1, y1, z1):
    """Generate coordinates of a 3D line using Bresenham's algorithm.

    Args:
        x0, y0, z0: Start point coordinates.
        x1, y1, z1: End point coordinates.

    Returns:
        Tuple of (x_coords, y_coords, z_coords) as numpy arrays.
    """
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    dz = abs(z1 - z0)
    sx = 1 if x1 > x0 else -1
    sy = 1 if y1 > y0 else -1
    sz = 1 if z1 > z0 else -1
    x, y, z = x0, y0, z0
    x_coords, y_coords, z_coords = [x], [y], [z]

    # Step along the driving (longest) axis; the two error terms decide when the other axes step.
    if dx >= dy and dx >= dz:
        e1, e2 = 2 * dy - dx, 2 * dz - dx
        for _ in range(dx):
            x += sx
            if e1 >= 0:
                y += sy
                e1 -= 2 * dx
            if e2 >= 0:
                z += sz
                e2 -= 2 * dx
            e1 += 2 * dy
            e2 += 2 * dz
            x_coords.append(x); y_coords.append(y); z_coords.append(z)
    elif dy >= dx and dy >= dz:
        e1, e2 = 2 * dx - dy, 2 * dz - dy
        for _ in range(dy):
            y += sy
            if e1 >= 0:
                x += sx
                e1 -= 2 * dy
            if e2 >= 0:
                z += sz
                e2 -= 2 * dy
            e1 += 2 * dx
            e2 += 2 * dz
            x_coords.append(x); y_coords.append(y); z_coords.append(z)
    else:
        e1, e2 = 2 * dy - dz, 2 * dx - dz
        for _ in range(dz):
            z += sz
            if e1 >= 0:
                y += sy
                e1 -= 2 * dz
            if e2 >= 0:
                x += sx
                e2 -= 2 * dz
            e1 += 2 * dy
            e2 += 2 * dx
            x_coords.append(x); y_coords.append(y); z_coords.append(z)

    return np.array(x_coords), np.array(y_coords), np.array(z_coords)
