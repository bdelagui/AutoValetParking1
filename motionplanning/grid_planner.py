# Grid planner module, image processing, and A-star path finding
# Tung M. Phan
# California Institute of Technology
# February 10th, 2020

# Resolve cv2 conflict with ROS
import sys
ros_path = '/opt/ros/kinetic/lib/python2.7/dist-packages'
if ros_path in sys.path:
    sys.path.remove('/opt/ros/kinetic/lib/python2.7/dist-packages')
import cv2
import networkx as nx
from typing import List, Any, Tuple
import itertools
from collections import namedtuple
from planning_graph import WeightedDirectedGraph
import csv
import numpy as np
import matplotlib.pyplot as plt
import _pickle as pickle
import json
from collections import OrderedDict as od
from ipdb import set_trace as st
from prim_json_maker import import_json
from tools import get_rotation_matrix, reflect_over_x_axis, constrain_heading_to_pm_180, manhattan_distance

def img_to_csv_bitmap(img_path, save_name=None, verbose=False):
    # usage: img_to_bitmap(img) where img is a numpy array of RGB values with
    # drivable area masked as white
    # saves as 'save_name'.csv and then returns a bitmap of drivable area (1) for drivable, (0) otherwise
    img = cv2.imread('imglib/{}.png'.format(img_path))
    m = img.shape[0]
    n = img.shape[1]
    np_bitmap = np.zeros((m,n), dtype=bool)
    for i in range(m):
        for j in range(n):
            np_bitmap[i][j] = all(img[i][j] == [255, 255, 255]) # if white
        if verbose:
            print('bitmap progress: {0:.1f}%'.format((i*n+j)/(m*n)*100))
    if save_name:
        np.savetxt('{}.csv'.format(save_name), np_bitmap, fmt='%i', delimiter=",")
    return np_bitmap

def csv_bitmap_to_numpy_bitmap(file_name):
    with open('{}.csv'.format(file_name), 'rt') as f:
        np_bitmap = np.array(list(csv.reader(f, delimiter=','))).astype('bool')
    return np_bitmap

def get_ball_neighbors(center, r):
    r = int(np.ceil(r)) # robustify r
    neighbors = []
    dy_max = r
    for dy in range(-dy_max, dy_max+1):
        dx_max = int(np.floor(np.sqrt(r**2-dy**2)))
        for dx in range(-dx_max, dx_max+1):
            neighbors.append([center[0]+dx, center[1]+dy])
    return np.unique(np.array(neighbors), axis=0)

def in_range(x, x_min, x_max):
    return x >= x_min and x <= x_max

def point_set_is_safe(point_set, bitmap):
    i_max = bitmap.shape[0]
    j_max = bitmap.shape[1]
    for point in point_set:
        if in_range(point[0], 0, i_max-1) and in_range(point[1], 0, j_max-1):
            if not bitmap[point[0]][point[1]]:
                return False
    return True


def rotate_vector(vec, theta, deg=False):
    rot_mat = get_rotation_matrix(theta, deg=deg)
    outvec =  np.array([int(round(x)) for x in np.matmul(rot_mat, vec)])
    return outvec

class Node:
    def __init__(self, x, y, heading, v):
        self.x = x
        self.y = y
        self.heading = heading
        self.v = v

class GridPrimitiveSet:
    def __init__(self, json_dict, symmetrize=True):
        if symmetrize:
            all_sets = [self.symmetrize_entry(json_dict[key]) for key in json_dict]
            self.grid_trajectory_set = list(itertools.chain(*all_sets))
        else:
            self.grid_trajectory_set = [self.add_heading_and_rescale_node_sequence(json_dict[key]) for key in json_dict]

    def rotate_trajectory(self, traj, angle, deg):
        rotated_entry = od()
        path = []
        for point in traj:
            new_vec = reflect_over_x_axis(rotate_vector(point, angle, deg=deg))
            path.append(new_vec.tolist())
        return path

    def get_headings_from_path(self, path, travel_direction):
        if travel_direction == 'forward':
            p1s, p2s = path[:2]
            dys = p2s[1]-p1s[1]
            dxs = p2s[0]-p1s[0]
            p1e, p2e = path[-2:]
            dye = p2e[1]-p1e[1]
            dxe = p2e[0]-p1e[0]
            start_heading = int(np.arctan2(-dys, dxs) / np.pi * 180)
            end_heading = int(np.arctan2(-dye, dxe) / np.pi * 180)
        else:
            start_heading, end_heading = self.get_headings_from_path(path, 'forward')
            start_heading = constrain_heading_to_pm_180(start_heading + 180)
            end_heading = constrain_heading_to_pm_180(end_heading + 180)
        return start_heading, end_heading

    def get_edges_for_xy(self, xy):
        edges = []
        for prim in self.grid_trajectory_set:
            edge = dict()
            node_sequence = [[point[0]+xy[0], point[1]+xy[1]] for point in prim['node_sequence']]
            start_node = (node_sequence[0][0], node_sequence[0][1], prim['start_heading'], prim['start_v'])
            end_node = (node_sequence[-1][0], node_sequence[-1][1], prim['end_heading'], prim['end_v'])
            edge['node_sequence'] = node_sequence
            edge['start_node'] = start_node
            edge['end_node'] = end_node
            edges.append(edge)
        return edges

    def add_heading_and_rescale_node_sequence(self, entry):
        traj = entry['node_sequence']
        start_heading, end_heading = self.get_headings_from_path(path=entry['node_sequence'],
                                                         travel_direction=entry['prim_type'])
        new_traj = [[point[0] * entry['grid_size'], point[1] * entry['grid_size']] for point in traj]
        entry['start_heading'] = start_heading
        entry['end_heading'] = end_heading
        entry['node_sequence'] = new_traj
        return entry

    def symmetrize_entry(self, entry):
        traj = entry['node_sequence']
        new_entries = [self.add_heading_and_rescale_node_sequence(entry)]
        angles = [-90, 90, 180] # assuming square grid
        for angle in angles:
            new_traj = self.rotate_trajectory(traj, angle, deg=True)
            new_entry = dict(entry) # make copy of original entry
            new_entry['node_sequence'] = new_traj
            new_entries.append(self.add_heading_and_rescale_node_sequence(new_entry))
        return new_entries

def get_rect_for_line(point1, point2, r):
    angle = np.arctan2(point2[1] - point1[1], point2[0] - point1[0])
    r = int(np.ceil(r)) # robustify r
    d = int(np.ceil(np.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2)))
    pre_displacements = []
    for dy in range(-r, r+1):
        for dx in range(0, d+1):
            pre_displacements.append([dx, dy])
    pre_displacements = np.matmul(np.array(pre_displacements), get_rotation_matrix(angle, deg=False).transpose()).astype(int)
    offset = np.tile(np.array(point1), (pre_displacements.shape[0], 1))
    displacements = pre_displacements + offset
    return np.unique(displacements, axis=0)

def get_tube_for_line(point1, point2, r):
    ball1 = get_ball_neighbors(point1, r)
    ball2 = get_ball_neighbors(point2, r)
    rect = get_rect_for_line(point1, point2, r)
    tube = np.vstack((ball1, ball2, rect))
    return np.unique(tube, axis=0)

def get_tube_for_lines(points, r):
    assert len(points) > 1
    tubes = []
    for point1, point2 in zip(points, points[1:]):
        tube = get_tube_for_line(point1, point2, r)
        tubes.append(tube)
    return np.unique(np.vstack(tubes), axis=0)

def json_to_grid_primitive_set(infile):
    json_dict = import_json(infile)
    prim_set = GridPrimitiveSet(json_dict)
    return prim_set

class GridParams:
    def __init__(self, grid_size, grid_anchor):
        self.grid_size = grid_size
        self.grid_anchor = grid_anchor

class GridPlanner:
    def __init__(self, bitmap, prim_set, grid_params, uncertainty):
        self.bitmap = bitmap
        self.grid_size = grid_params.grid_size
        self.grid_anchor = grid_params.grid_anchor
        self.grid = self.create_uniform_grid()
        self.prim_set = prim_set
        self.uncertainty = uncertainty
        self.planning_graph = None

    def create_uniform_grid(self):
        bitmap = self.bitmap
        grid_size = self.grid_size
        grid_anchor = self.grid_anchor
        Grid = namedtuple('Grid', ['sampled_points', 'grid_size'])
        h = bitmap.shape[0]
        w = bitmap.shape[1]
        assert grid_anchor[0] >= 0 and grid_anchor[0] <= w # check range x
        assert grid_anchor[1] >= 0 and grid_anchor[1] <= h # check range y
        x_start = grid_anchor[0] % grid_size
        y_start = grid_anchor[1] % grid_size
        sampled_points = []
        x_curr = x_start
        y_curr = y_start
        while x_curr < w:
            y_curr = y_start
            while y_curr < h:
                sampled_points.append([x_curr, y_curr])
                y_curr += grid_size
            x_curr += grid_size
        grid = Grid(sampled_points=np.array(sampled_points), grid_size = grid_size)
        return grid

    def compute_sequence_weight(self, sequence):
        weight = 0
        for n1, n2 in zip(sequence, sequence[1:]):
            weight += manhattan_distance(n1, n2)
        return weight

    def get_planning_graph(self, verbose=True):
        bitmap = self.bitmap.transpose()
        if not self.planning_graph:
            planning_graph = dict()
            planning_graph['graph'] = None
            planning_graph['edge_info'] = None
            graph = WeightedDirectedGraph()
            edge_info = dict()
            sampled_points = self.grid.sampled_points
            all_xy_nodes = []
            for xy in sampled_points:
                neighbors = get_ball_neighbors(xy, self.uncertainty)
                if point_set_is_safe(neighbors, bitmap):
                    all_xy_nodes.append(xy)

            for idx, xy in enumerate(all_xy_nodes):
                if verbose:
                    print('planning graph progress: {0:.1f}%'.format(idx/len(all_xy_nodes)*100))
                for edge in self.prim_set.get_edges_for_xy(xy):
                    tube = get_tube_for_lines(edge['node_sequence'], r=self.uncertainty)
                    if point_set_is_safe(tube, bitmap):
                        graph.add_edges([[edge['start_node'], edge['end_node'], self.compute_sequence_weight(edge['node_sequence'])]])
                        edge_info[edge['start_node'], edge['end_node']] = edge['node_sequence']

            planning_graph['graph'] = graph
            planning_graph['edge_info'] = edge_info
            self.planning_graph = planning_graph
            return planning_graph
        else:
            return self.planning_graph

def plot_planning_graph(planning_graph, plt, verbose=True):
    # very inefficient plotting
    edges = [] # type: List[Any]
    for idx, edge in enumerate(planning_graph._edges):
        print('collecting graph edges progress: {0:.1f}%'.format(idx/len(planning_graph._edges)*100))
        for to_edge in planning_graph._edges[edge]:
            if [edge, to_edge] not in edges and [edge, to_edge] not in edges:
                edges.append([edge, to_edge])
    for idx, edge in enumerate(edges):
        print('plotting graph edges progress: {0:.1f}%'.format(idx/len(edges)*100))
        plt.plot([edge[0][0], edge[1][0]], [edge[0][1], edge[1][1]])

def convert_to_nx_graph(digraph):
    G = nx.DiGraph()
    for start in digraph._edges:
        for end in digraph._edges[start]:
            edge = (start, end)
            weight = digraph._weights[edge]
            G.add_weighted_edges_from([(edge[0], edge[1], weight)])
    return G

def find_closest_point(p1, graph):
    def angle_similarity_scores(a_diff):
        c_diff = []
        for diff in a_diff:
            diff = constrain_heading_to_pm_180(diff)
            c_diff.append(diff)
        return np.array(c_diff)
    diff = np.array(graph._nodes)-p1
    if (diff.shape[1] == 4):
        return graph._nodes[np.argmin(np.sqrt(diff[:,0]**2 +
            diff[:,1]**2) + 0.001 * angle_similarity_scores(diff[:,2])**2 + 0.001 * diff[:,3]**2)]
    if (diff.shape[1] == 3):
        return graph._nodes[np.argmin(np.sqrt(diff[:,0]**2 +
            diff[:,1]**2 + 0.1 * diff[0:,2]**2))]
    if (diff.shape[1] == 2):
        return graph._nodes[np.argmin(np.sqrt(diff[:,0]**2 +
            diff[:,1]**2))]

def astar_trajectory(planning_graph,start,end,heuristic=None):
    closest_start = find_closest_point(start, planning_graph)
    closest_end = find_closest_point(end, planning_graph)
    nx_graph = convert_to_nx_graph(planning_graph)
    if heuristic:
        path = np.array(nx.astar_path(nx_graph, closest_start, closest_end, heuristic))
    else:
        path = np.array(nx.astar_path(nx_graph, closest_start, closest_end))
    return path

if __name__ == '__main__':
    remap = False
    if remap:
        # create bitmap from parking lot image
        bitmap = img_to_csv_bitmap('AVP_planning_300p') # compute bitmap
        # define grid parameters
        grid_params = GridParams(grid_size = 10, grid_anchor = [0, 0])
        # load primitive set
        prim_set = json_to_grid_primitive_set('10px_prims_hacked.json')
        grid_planner = GridPlanner(bitmap, prim_set, grid_params, uncertainty = 7)
        planning_graph = grid_planner.get_planning_graph()
        with open('planning_graph.pkl', 'wb') as f:
            pickle.dump(planning_graph, f)
    else:
        with open('planning_graph.pkl', 'rb') as f:
            planning_graph = pickle.load(f)
        edge_info = planning_graph['edge_info']
        planning_graph = planning_graph['graph']
        ps = []
        ps.append((120, 60, 0, 0))
        plt.plot(ps[0][0], ps[0][1], 'c.')
        img = plt.imread('imglib/AVP_planning_300p.png')
        fig = plt.figure(1)
        plt.imshow(img)
        plt.axis('equal')

        coords = []
        clicks = 0
        print('click on parking lot to set next desired xy')
        clickok = True
        def onclick(event):
            global ix, iy, clicks, coords, ps, clickok
            if clickok:
                clickok = False
                ix, iy = event.xdata, event.ydata
                clicks += 1
                coords.append((ix, iy))
                if clicks % 2: # if odd
                    print('x = %d, y = %d'%( ix, iy))
                    print('click on another point to set desired heading')
                    clickok = True
                else:
                    try:
                        dys = coords[1][1] - coords[0][1]
                        dxs = coords[1][0] - coords[0][0]
                        theta = np.arctan2(-dys, dxs) / np.pi * 180
                        print('theta = %d'%(theta))
                        ps.append((coords[0][0], coords[0][1], theta, 0))
                        coords = []
                        start = ps[-2]
                        end = ps[-1]
                        traj = astar_trajectory(planning_graph, start, end)
                        for start, end in zip(traj, traj[1:]):
                            segment = np.array(edge_info[(tuple(start), tuple(end))])
                            plt.plot(segment[0,0], segment[0,1], 'b.')
                            plt.plot(segment[-1,0], segment[-1,1], 'rx')
                            plt.plot(segment[:,0], segment[:,1], 'k--')
                            plt.pause(0.3)
                        print('trajectory plotted!')
                        print('click to set desired xy')
                        clickok = True
                        plt.show()
                    except:
                        clickok = True
                        print('CANNOT FIND TRAJECTORY: click again to set xy!')
                        if len(ps) > 1:
                            ps = ps[:-1]
        cid = fig.canvas.mpl_connect('button_press_event', onclick)
        plt.show()
