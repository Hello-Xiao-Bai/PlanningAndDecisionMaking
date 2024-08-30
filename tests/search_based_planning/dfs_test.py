import math

import matplotlib.pyplot as plt
import sys
import pathlib

file_path = pathlib.Path(__file__)
root_dir = file_path.parent.parent.parent
sys.path.append(str(root_dir))

import copy
from common.geometry import *
from common.plot_util import *
from common.gif_creator import *
from common.common_util import *

show_animation = True


class DepthFirstSearchPlanner:

    def __init__(self, ox, oy, reso, rr):
        """
        Initialize grid map for Depth-First planning

        ox: x position list of Obstacles [m]
        oy: y position list of Obstacles [m]
        resolution: grid resolution [m]
        rr: robot radius[m]
        """

        self.reso = reso
        self.rr = rr
        self.calc_obstacle_map(ox, oy)
        self.motion = self.get_motion_model()

    class Node:
        def __init__(self, x, y, cost, parent_index, parent):
            self.x = x  # index of grid
            self.y = y  # index of grid
            self.cost = cost
            self.parent_index = parent_index
            self.parent = parent

        def __str__(self):
            return (
                str(self.x)
                + ","
                + str(self.y)
                + ","
                + str(self.cost)
                + ","
                + str(self.parent_index)
            )

    def planning(self, sx, sy, gx, gy):
        """
        Depth First search

        input:
            s_x: start x position [m]
            s_y: start y position [m]
            gx: goal x position [m]
            gy: goal y position [m]

        output:
            rx: x position list of the final path
            ry: y position list of the final path
        """

        nstart = self.Node(
            self.calc_xyindex(sx, self.minx),
            self.calc_xyindex(sy, self.miny),
            0.0,
            -1,
            None,
        )
        ngoal = self.Node(
            self.calc_xyindex(gx, self.minx),
            self.calc_xyindex(gy, self.miny),
            0.0,
            -1,
            None,
        )

        open_set, closed_set = dict(), dict()
        open_set[self.calc_grid_index(nstart)] = nstart
        while True:
            if len(open_set) == 0:
                print("Open set is empty..")
                break

            current = open_set.pop(list(open_set.keys())[-1])
            c_id = self.calc_grid_index(current)

            # show graph
            if show_animation:  # pragma: no cover
                plt.plot(
                    self.calc_grid_position(current.x, self.minx),
                    self.calc_grid_position(current.y, self.miny),
                    "xc",
                )
                # for stopping simulation with the esc key.
                plt.gcf().canvas.mpl_connect(
                    "key_release_event",
                    lambda event: [exit(0) if event.key == "escape" else None],
                )
                plt.savefig(gif_creator.get_image_path())
                plt.pause(0.01)

            if current.x == ngoal.x and current.y == ngoal.y:
                print("Find goal")
                ngoal.parent_index = current.parent_index
                ngoal.cost = current.cost
                break

            # expand_grid search grid based on motion model
            for i, _ in enumerate(self.motion):
                node = self.Node(
                    current.x + self.motion[i][0],
                    current.y + self.motion[i][1],
                    current.cost + self.motion[i][2],
                    c_id,
                    None,
                )
                n_id = self.calc_grid_index(node)

                # If the node is not safe, do nothing
                if not self.verify_node(node):
                    continue

                if n_id not in closed_set:
                    open_set[n_id] = node
                    closed_set[n_id] = node
                    node.parent = current

        rx, ry = self.calc_final_path(ngoal, closed_set)
        return rx, ry

    def calc_final_path(self, ngoal, closedset):
        # generate final course
        rx, ry = [self.calc_grid_position(ngoal.x, self.minx)], [
            self.calc_grid_position(ngoal.y, self.miny)
        ]
        n = closedset[ngoal.parent_index]
        while n is not None:
            rx.append(self.calc_grid_position(n.x, self.minx))
            ry.append(self.calc_grid_position(n.y, self.miny))
            n = n.parent

        return rx, ry

    def calc_grid_position(self, index, minp):
        """
        calc grid position

        :param index:
        :param minp:
        :return:
        """
        pos = index * self.reso + minp
        return pos

    def calc_xyindex(self, position, min_pos):
        return round((position - min_pos) / self.reso)

    def calc_grid_index(self, node):
        return (node.y - self.miny) * self.xwidth + (node.x - self.minx)

    def verify_node(self, node):
        px = self.calc_grid_position(node.x, self.minx)
        py = self.calc_grid_position(node.y, self.miny)

        if px < self.minx:
            return False
        elif py < self.miny:
            return False
        elif px >= self.maxx:
            return False
        elif py >= self.maxy:
            return False

        # collision check
        if self.obmap[node.x][node.y]:
            return False

        return True

    def calc_obstacle_map(self, ox, oy):
        self.minx = round(min(ox))
        self.miny = round(min(oy))
        self.maxx = round(max(ox))
        self.maxy = round(max(oy))
        self.xwidth = round((self.maxx - self.minx) / self.reso)
        self.ywidth = round((self.maxy - self.miny) / self.reso)

        # obstacle map generation
        self.obmap = [[False for _ in range(self.ywidth)] for _ in range(self.xwidth)]
        for ix in range(self.xwidth):
            x = self.calc_grid_position(ix, self.minx)
            for iy in range(self.ywidth):
                y = self.calc_grid_position(iy, self.miny)
                for iox, ioy in zip(ox, oy):
                    d = math.hypot(iox - x, ioy - y)
                    if d <= self.rr:
                        self.obmap[ix][iy] = True
                        continue

    @staticmethod
    def get_motion_model():
        # dx, dy, cost
        motion = [
            [1, 0, 1],
            [0, 1, 1],
            [-1, 0, 1],
            [0, -1, 1],
            [-1, -1, math.sqrt(2)],
            [-1, 1, math.sqrt(2)],
            [1, -1, math.sqrt(2)],
            [1, 1, math.sqrt(2)],
        ]

        return motion


def construct_env_info():
    border_x = []
    border_y = []
    ox = []
    oy = []

    # map border.
    for i in range(-10, 60):
        border_x.append(i)
        border_y.append(-10.0)
    for i in range(-10, 60):
        border_x.append(60.0)
        border_y.append(i)
    for i in range(-10, 61):
        border_x.append(i)
        border_y.append(60.0)
    for i in range(-10, 61):
        border_x.append(-10.0)
        border_y.append(i)

    # Obstacle 1.
    for i in range(40, 55, 1):
        for j in range(5, 15, 1):
            ox.append(i)
            oy.append(j)

    # Obstacle 2.
    for i in range(40):
        for j in range(20, 25, 1):
            ox.append(j)
            oy.append(i)

    # Obstacle 3.
    for i in range(30):
        for j in range(40, 45, 1):
            ox.append(j)
            oy.append(58.0 - i)

    # Obstacle 4.
    for i in range(0, 20, 1):
        for j in range(35, 40, 1):
            ox.append(i)
            oy.append(j)

    return border_x, border_y, ox, oy


def main():
    print(__file__ + " start!!")

    # start and goal position
    start_x = 10.0  # [m]
    start_y = 10.0  # [m]
    goal_x = 50.0  # [m]
    goal_y = 0.0  # [m]
    grid_size = 2.0  # [m]
    robot_radius = 1.0  # [m]

    # construct environment info.
    border_x, border_y, ox, oy = construct_env_info()

    if show_animation:  # pragma: no cover
        plt.plot(border_x, border_y, "s", color=(0.5, 0.5, 0.5), markersize=10)
        plt.plot(ox, oy, "s", color="k")
        plt.plot(start_x, start_y, "og", markersize=10)
        plt.plot(goal_x, goal_y, "ob", markersize=10)
        plt.grid(True)
        plt.axis("equal")

    ox.extend(border_x)
    oy.extend(border_y)
    dfs = DepthFirstSearchPlanner(ox, oy, grid_size, robot_radius)
    rx, ry = dfs.planning(start_x, start_y, goal_x, goal_y)

    if show_animation:  # pragma: no cover
        plt.plot(rx, ry, "-r")
        plt.savefig(gif_creator.get_image_path())
        plt.pause(0.01)
        gif_creator.create_gif()
        plt.show()


if __name__ == "__main__":
    fig, ax = plt.subplots()
    gif_creator = GifCreator(file_path, fig, ax)
    main()