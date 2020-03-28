from components.boxcomponent import BoxComponent
import trio
import _pickle as pickle
import motionplanning.end_planner as path_planner
from prepare.communication import *
from variables.global_vars import *
from variables.parking_data import parking_spots
import math
from ipdb import set_trace as st
#from motionplanning.parking_data import parking_spots

class Planner(BoxComponent):
    def __init__(self, nursery):
        super().__init__()
        self.name = self.__class__.__name__
        self.nursery = nursery
        self.cars = dict()
        self.obstacles = dict()
        self.reachable = np.ones((MAX_NO_PARKING_SPOTS,1)) # if spots can be reached from drop_off, currently all reachable

    async def get_car_position(self,car):
        print('Planner - Sending position request to Map system')
        await self.out_channels['Map'].send(car)
        car, pos = await self.in_channels['Map'].receive()
        return pos

    async def find_spot_coordinates(self, spot):
        return parking_spots[spot]

    async def send_directive_to_car(self, car, end):
        pos = await self.get_car_position(car)
        start = np.zeros(4)
        start[0] = pos[0]/SCALE_FACTOR_PLAN
        start[1] = pos[1]/SCALE_FACTOR_PLAN
        start[2] = -np.rad2deg(pos[2])
        traj = await self.get_path(start,end) 
        if traj:
            print('Planner - sending Directive to {0}'.format(car.name))
            await self.out_channels[car.name].send(traj)
        else:
            print('Planner - No Path found - sending Response to Supervisor')
            resp = ['NoPath', car]
            await self.out_channels['Supervisor'].send(resp)
        await trio.sleep(1)

    async def add_obstacle(self, car):
        self.obstacles.update({car.name: (car.x,car.y,car.yaw)})
        # update reachability matrix here

    def is_in_buffer(self,x,y,center_x,center_y):
        # assume radius of 10 pixels (gridsize) to delete around obstacle center
        if math.sqrt((x-center_x)**2+(y-center_y)**2)<=10:
            return True

    def get_current_planning_graph(self):
        sys.path.append('../motionplanning')
        with open('planning_graph_refined.pkl', 'rb') as f:
            planning_graph = pickle.load(f)
        # loop through obstacles and generate new graph
        if self.obstacles:
            obs = []
            for key,value in self.obstacles.items():
                obs.append(value)
            obs = [(row[0]/SCALE_FACTOR_PLAN,row[1]/SCALE_FACTOR_PLAN) for row in obs]
            # find grid nodes around obstacle
            print(obs)
            nodes = planning_graph['graph']._nodes
            del_nodes = [(node) for node in nodes if self.is_in_buffer(node[0],node[1],obs[0][0],obs[0][1])]
            print(del_nodes)
            # edges = planning_graph['graph']._edges
            # give list of edges
            # set weights to np.inf
            # return new planning_graph
            #planning_graph = path_planner.update_planning_graph(del_nodes)
        return planning_graph

    async def get_path(self, start, end): 
        planning_graph= self.get_current_planning_graph()
        traj = path_planner.get_mpc_path(start,end,planning_graph)
        if traj:# add no traj possible to catch execption
            return traj
        else: 
            return False

    async def update_car_response(self, receive_response_channel):
        async with receive_response_channel:
            async for response in receive_response_channel:
                car = response[0]
                resp = response[1]
                print('Planner - receiving "{0}" response from {1}'.format(resp,car.name))
                if response[1]=='Completed':
                    if self.cars.get(car.name,0)=='Assigned':
                        self.cars.update({car.name: 'Parked'})
                    elif self.cars.get(car.name,0)=='Request':
                        self.cars.pop(car.name)
                if response[1]=='Failure':
                    await self.add_obstacle(car)
                    self.cars.update({car.name: 'Failure'})
                await trio.sleep(0)
                print(self.cars)
                await self.send_response_to_supervisor((resp,car))

    async def send_response_to_supervisor(self,resp):
        response = resp[0]
        car = resp[1]
        print(resp)
        print('Planner - sending "{0} - {1}" response to Supervisor'.format(response,car.name))
        await self.out_channels['Supervisor'].send((car,response))
        await trio.sleep(0)
    
    async def check_supervisor(self,send_response_channel,Game):
        async for directive in self.in_channels['Supervisor']:
            car = directive[0]
            todo = directive[1]
            if todo[0] == 'Park':
                print('Planner - receiving directive from Supervisor to park {0} in Lot {1}'.format(car.name,todo[1]))
                self.cars.update({car.name: 'Assigned'})
                create_unidirectional_channel(self, car, max_buffer_size=np.inf)
                self.nursery.start_soon(car.run,send_response_channel,Game)
                end = await self.find_spot_coordinates(todo[1])
                await self.send_directive_to_car(car, end)
            elif todo == 'Pickup':
                print('Planner -  receiving directive from Supervisor to retrieve {0}'.format(car.name))
                await self.send_directive_to_car(car, PICK_UP)
                self.cars.update({car.name : 'Request'})
            elif todo == 'Towed':
                # remove the car
                print('Planner - {0} is being towed'.format(car.name))
                self.cars.pop(car.name)
                self.obstacles.pop(car.name)

    def check_reachability(self,spot):
        if self.reachable[spot]:
            return True
        else:
            return False

    async def run(self,Game):
        send_response_channel, receive_response_channel = trio.open_memory_channel(25)
        async with trio.open_nursery() as nursery:
            nursery.start_soon(self.check_supervisor,send_response_channel,Game)
            await trio.sleep(1)
            nursery.start_soon(self.update_car_response,receive_response_channel)
