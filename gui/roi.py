"""
3D ROI mesh item for the lightsheet viewer.
"""

import numpy as np
import pyqtgraph.opengl as gl
from PyQt5.QtCore import pyqtSignal


class ROI3D(gl.GLMeshItem):
    """Draggable 3-D cube ROI for the OpenGL view."""

    sigRegionChanged = pyqtSignal(object)

    def __init__(self, size=(10, 10, 10), color=(1, 1, 1, 0.3)):
        verts, faces = self.create_cube(size)
        super().__init__(vertexes=verts, faces=faces, smooth=False, drawEdges=True, edgeColor=color)
        self.size = size
        self.setColor(color)

    @staticmethod
    def create_cube(size):
        x, y, z = size
        verts = np.array([
            [0, 0, 0], [x, 0, 0], [x, y, 0], [0, y, 0],
            [0, 0, z], [x, 0, z], [x, y, z], [0, y, z],
        ])
        faces = np.array([
            [0, 1, 2], [0, 2, 3], [0, 1, 4], [1, 4, 5],
            [1, 2, 5], [2, 5, 6], [2, 3, 6], [3, 6, 7],
            [3, 0, 7], [0, 4, 7], [4, 5, 6], [4, 6, 7],
        ])
        return verts, faces

    def setPosition(self, pos):
        self.resetTransform()
        self.translate(*pos)
        self.sigRegionChanged.emit(self)
