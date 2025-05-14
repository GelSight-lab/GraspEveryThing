import open3d
from open3d import *
import numpy as np

class ClassVis3D:
    def __init__(self, n=100, m=200):
        self.n, self.m = n, m

        self.init_open3D()
        pass

    def init_open3D(self):
        x = np.arange(self.n)
        y = np.arange(self.m)
        self.X, self.Y = np.meshgrid(x, y)
        Z = np.sin(self.X)

        self.points = np.zeros([self.n * self.m, 3])
        self.points[:, 0] = np.ndarray.flatten(self.X) / self.m
        self.points[:, 1] = np.ndarray.flatten(self.Y) / self.m
        print(self.m, np.max(self.points[:, 0]), np.max(self.points[:, 1]))

        self.depth2points(Z)

        self.pcd = open3d.geometry.PointCloud()

        self.pcd.points = open3d.utility.Vector3dVector(self.points)

        self.vis = open3d.visualization.Visualizer()
        self.vis.create_window()
        self.vis.add_geometry(self.pcd)

        self.ctr = self.vis.get_view_control()
        self.ctr.change_field_of_view(-10)
        print("fov", self.ctr.get_field_of_view())
        self.ctr.convert_to_pinhole_camera_parameters()
        self.ctr.set_zoom(0.35)
        self.ctr.rotate(0, -200)  # mouse drag in x-axis, y-axis
        self.vis.update_renderer()

    def depth2points(self, Z):
        self.points[:, 2] = np.ndarray.flatten(Z)

    def update(self, Z):
        # points = np.random.rand(60000,3)
        self.depth2points(3 * Z)

        dx, dy = np.gradient(Z)
        dx, dy = dx * 100, dy * 100

        np_colors = dx + 0.5
        np_colors[np_colors < 0] = 0
        np_colors[np_colors > 1] = 1
        np_colors = np.ndarray.flatten(np_colors)
        colors = np.zeros([self.points.shape[0], 3])

        colors = np.zeros([self.points.shape[0], 3])

        for _ in range(3):
            colors[:, _] = np_colors

        self.pcd.points = open3d.utility.Vector3dVector(self.points)
        self.pcd.colors = open3d.utility.Vector3dVector(colors)

        try:
            self.vis.update_geometry()
        except:
            self.vis.update_geometry(self.pcd)
        self.vis.poll_events()
        self.vis.update_renderer()
