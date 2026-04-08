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
    dm = max(dx, dy, dz)
    x, y, z = x0, y0, z0

    x_coords, y_coords, z_coords = [], [], []

    for _ in range(dm + 1):
        x_coords.append(x)
        y_coords.append(y)
        z_coords.append(z)

        if x == x1 and y == y1 and z == z1:
            break

        if dx >= dy and dx >= dz:
            x += sx
            dy += dy
            dz += dz
            if dy >= dx:
                y += sy
                dy -= dx
            if dz >= dx:
                z += sz
                dz -= dx
        elif dy >= dx and dy >= dz:
            y += sy
            dx += dx
            dz += dz
            if dx >= dy:
                x += sx
                dx -= dy
            if dz >= dy:
                z += sz
                dz -= dy
        else:
            z += sz
            dx += dx
            dy += dy
            if dx >= dz:
                x += sx
                dx -= dz
            if dy >= dz:
                y += sy
                dy -= dz

    return np.array(x_coords), np.array(y_coords), np.array(z_coords)
