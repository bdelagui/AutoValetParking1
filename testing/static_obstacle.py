# Automated Valet Parking - Static obstacles for testing
# Josefine Graebener
# California Institute of Technology
# July, 2020
import sys
sys.path.append('..') # enable importing modules from an upper directory:
from prepare.boxcomponent import BoxComponent
import trio
from variables.geometries import FAILURE_ACCEPT_BOX_1
from variables.global_vars import SCALE_FACTOR_PLAN as SFP
import numpy as np
from ipdb import set_trace as st
import pickle

from shapely.geometry import Polygon, Point, LineString
import pdb


class Obstacles(BoxComponent):
    def __init__(self,
                 loc = [110,80,10], # (x, y, radius) in gridpoints
                 ):
        super().__init__()
        # init_state: initial state by default
        self.name = self.__class__.__name__
        self.obs = dict()
        self.num_obs = len(self.obs) # number of obstacles currently in the lot
        self.max_serial_number = 0
        self.only_accept_obs = False

    def create_obstacle_map(self): # static obstacles initialized at the beginning of the simulation
        self.obs = {1: (200, 100, 0, 3),
        2: (210, 100, 0, 3),
        3: (220, 100, 0, 3),
        4: (175, 180, 0, 3),
        #4:(200, 212.5, 0, 3)} # state 64
        5: (182.5, 180, 0 ,3),
        6: (210, 120, 0, 3),
        7: (210, 130, 0, 3),
        8: (170, 100, 0, 3),
        9: (192, 180, 0, 3)} # state 62
        #   self.obs = {1: (170, 100, 0, 3), # example test data
        # 2: (180, 100, 0, 3),
        # 3: (190, 100, 0, 3)}
        # read static obstacle map from test data file
#        with open('/Users/berlindelaguila/AutoValetParking/testing/testing/static_obstacle_test_data/static_obstacle.dat', 'rb') as f:
#           obs_map = pickle.load(f)
#        obs = [(item[0][0], item[0][1], 0, item[1]) for item in obs_map]
#        self.obs = dict(enumerate(obs))
#        #self.obs.pop(0) # delete big obstacle for test
#        #self.obs.pop(1) #  delete obstacle in red area
#        # delete all obstacles in unacceptable area
#        if self.only_accept_obs:
#           delkeys = []
#           for key,val in self.obs.items():
#               loc = Point([(val[0]*SFP,val[1]*SFP)]).buffer(val[3]*SFP)
#               if not loc.intersects(FAILURE_ACCEPT_BOX_1):
#                   delkeys.append(key)
#           for key in delkeys:
#               self.obs.pop(key)
                
        self.num_obs = len(self.obs)
        self.max_serial_number = self.max_serial_number + self.num_obs
        print('Obstacle Map created')
        return self.obs

    def add_obstacle(self,obs): # add new obstacle
        num = self.max_serial_number+1
        self.obs.update({num : obs})
        self.max_serial_number = self.max_serial_number+1
        print('Obstacle added')

    def rmv_obstacle(self,obsnum): # remove an obstacle
        self.obs.pop(obsnum)
        print('Obstacle removed')

    def get_updated_obstacles(self): # return current obstacle list
        return self.obs

    async def listen_for_commands(self,Game,Simulation,Planner):
        async with self.in_channels['TestSuite']:
            async for response in self.in_channels['TestSuite']:
                if response[0]=='Add':
                    obs = response[1]
                    self.add_obstacle(obs)
                elif response[0]=='Remove':
                    obsnum = response[1]
                    self.rmv_obstacle(obsnum)
                await Planner.update_obstacle_map(Game,self,Simulation)


    async def run(self,Game,Simulation,Planner):
        async with trio.open_nursery() as nursery:
            nursery.start_soon(self.listen_for_commands,Game,Simulation,Planner)
            await trio.sleep(0)
