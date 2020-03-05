import curses
from ipdb import set_trace as st
import numpy as np
import trio
import random

average_arrival_rate = 0.5 # per second
beta = 1/average_arrival_rate
average_park_time = 10 # seconds
MAX_BUFFER_SIZE = np.inf
MAX_NO_PARKING_SPOTS = 3
START_X = 0
START_Y = 0
START_YAW = 0
OPEN_TIME = 500 # not yet working


def get_current_time():
    return trio.current_time() - start_time

def create_unidirectional_channel(sender, receiver, max_buffer_size, name = False):
    out_channel, in_channel = trio.open_memory_channel(max_buffer_size)
    if name:
        sender.out_channels[name] = out_channel
        receiver.in_channels[name] = in_channel
    else:
        sender.out_channels[receiver.name] = out_channel
        receiver.in_channels[sender.name] = in_channel

def create_bidirectional_channel(compA, compB, max_buffer_size):
    create_unidirectional_channel(sender=compA, receiver=compB, max_buffer_size=max_buffer_size)
    create_unidirectional_channel(sender=compB, receiver=compA, max_buffer_size=max_buffer_size)

class CarInfo:
    def __init__(self, arrive_time, depart_time):
        self.arrive_time = arrive_time
        self.depart_time = depart_time

class BoxComponent:
    def __init__(self):
        self.in_channels = dict()
        self.out_channels = dict()

#    def _initialize_channels(self, num_channels):
#        channels = []
#        for _ in range(num_channels):
#            channels.append(None)
#        return channels
#
#    def _find_open_channel(self, channel_list):
#        for idx in range(len(channel_list)):
#            if channel_list[idx] == None:
#                return idx
#        # all channels are closed!
#        return -1

class Map(BoxComponent): 
    def __init__(self):
        super().__init__()
        self.name = self.__class__.__name__
        self.car_positions = dict()

    async def send_position(self,car):
        print('Map System - sending car position to Planner')
        for key, value in self.car_positions.items():
            if (key==car.name):
                pos = value
        await self.out_channels['Planner'].send((car,pos))

    async def add_car_to_map(self):
        async with self.in_channels['Enter']:
            async for car in self.in_channels['Enter']:
                print('Map System - Adding new car to Map')
                self.car_positions.update({car.name: (car.x,car.y,car.yaw)})
                print(self.car_positions)

    async def send_camera_data_to_planner(self):
        async with self.in_channels['Planner']:
            async for car in self.in_channels['Planner']:
                await self.send_position(car)
                print(self.car_positions)
            
    async def get_camera_data(self, receive_update_channel):
        async with receive_update_channel:
            async for car in receive_update_channel:
                self.car_positions.update({car.name: (car.x,car.y,car.yaw)})

    async def rmv_car_from_map(self):
        async with self.in_channels['Exit']:
            async for car in self.in_channels['Exit']:
                print('Map System - Removing {} from Map'.format(car.name))
                self.car_positions.pop(car.name)
                print(self.car_positions)

    async def run(self, receive_update_channel):
        async with trio.open_nursery() as nursery:
            nursery.start_soon(self.add_car_to_map)
            nursery.start_soon(self.rmv_car_from_map)
            nursery.start_soon(self.get_camera_data,receive_update_channel)
            nursery.start_soon(self.send_camera_data_to_planner)

    
class Planner(BoxComponent):
    def __init__(self, nursery):
        super().__init__()
        self.name = self.__class__.__name__
        self.nursery = nursery
        self.cars = []
        self.parking_spots = dict([ (i, (i, i, np.pi)) for i in range(0,MAX_NO_PARKING_SPOTS) ]) # example coordinates for parking spots

    async def get_car_position(self,car):
        print('Planner - Sending position request to Map system')
        await self.out_channels['Map'].send(car)
        pos = await self.in_channels['Map'].receive()
        return pos

    async def find_spot_coordinates(self, spot):
        print(self.parking_spots)
        return self.parking_spots[spot]

    async def send_directive_to_car(self, car, ref):
        await self.get_car_position(car)
        print('Planner - sending Directive to {0}'.format(car.name))
        await self.out_channels[car.name].send(ref)
        await trio.sleep(1)

    async def update_car_response(self, receive_response_channel):
        async with receive_response_channel:
            async for response in receive_response_channel:
                car = response[0]
                resp = response[1]
                print('Planner - receiving "{0}" response from {1}'.format(resp,car.name))
                await trio.sleep(0)
                await self.send_response_to_supervisor(car,resp)

    async def send_response_to_supervisor(self,car,response):
        print('Planner - sending "{0} - {1}" response to Supervisor'.format(response,car.name))
        await self.out_channels['Supervisor'].send((car,response))
        await trio.sleep(0)
    
    async def check_supervisor(self,send_response_channel,send_update_channel):
        async for directive in self.in_channels['Supervisor']:
            car = directive[0]
            todo = directive[1]
            #print(todo)
            if todo[0] == 'Park':
                print('Planner - receiving directive from Supervisor to park {0} in Lot {1}'.format(car.name,todo[1]))
                self.cars.append(car)
                create_unidirectional_channel(self, car, max_buffer_size=np.inf)
                self.nursery.start_soon(car.run,send_response_channel,send_update_channel)
                ref = await self.find_spot_coordinates(todo[1])
                
            elif todo == 'Pickup':
                print('Planner -  receiving directive from Supervisor to retrieve {0}'.format(car.name))
                ref = [0,0,0]
            await self.send_directive_to_car(car, ref)

    async def run(self,send_update_channel):
        send_response_channel, receive_response_channel = trio.open_memory_channel(25)
        async with trio.open_nursery() as nursery:
            nursery.start_soon(self.check_supervisor,send_response_channel,send_update_channel)
            await trio.sleep(1)
            nursery.start_soon(self.update_car_response,receive_response_channel)


class Car(BoxComponent):
    def __init__(self, arrive_time, depart_time):
        super().__init__()
        self.name = 'Car {}'.format(id(self))
        self.arrive_time = arrive_time
        self.depart_time = depart_time
        self.ref = None
        self.x = None
        self.y = None
        self.yaw = None

    async def update_planner_command(self,send_response_channel,send_update_channel):
        async for directive in self.in_channels['Planner']:
            self.ref = directive
            print('{0} - Receiving Directive from Planner'.format(self.name))
            ref=self.ref
            await self.track_reference(ref,send_update_channel)
            await trio.sleep(1)
            await self.send_response(send_response_channel)
 
    async def track_reference(self,ref,send_update_channel):
        #self.ref = await self.in_channels['Planner'].receive()
        print('{0} - Tracking reference... {1}'.format(self.name,ref))
        self.x = ref[0]
        self.y = ref[1]
        self.yaw = ref[2]
        await self.send_update_to_map(send_update_channel)
        await trio.sleep(1)

    async def send_response(self,send_response_channel):
        await trio.sleep(1)
        response = 'Completed'
        print('{0} - sending {1} response to Planner'.format(self.name,response))
        await send_response_channel.send((self,response))
        await trio.sleep(1)

    async def send_update_to_map(self,send_update_channel):
        print('{0} - sending position update to Map'.format(self.name))
        await send_update_channel.send(self)

    async def run(self,send_response_channel,send_update_channel):
        async with trio.open_nursery() as nursery:
            nursery.start_soon(self.update_planner_command,send_response_channel,send_update_channel)
            await trio.sleep(0)
            #nursery.start_soon(self.send_update_to_map,send_update_channel)
            #await trio.sleep(0)
            #nursery.start_soon(self.track_reference)
            #nursery.start_soon(self.send_response,send_response_channel)


class Supervisor(BoxComponent):
    def __init__(self):
        super().__init__()
        self.name = self.__class__.__name__
        self.cars = []
        self.spot_no = MAX_NO_PARKING_SPOTS
        self.parking_spots = dict([ (i, ("Vacant", "None")) for i in range(0,self.spot_no) ])

    async def send_directive_to_planner(self, car,ref):
        directive = [car,ref]
        await self.out_channels['Planner'].send(directive)

    async def update_parking_spots(self,car):
        for spot, status in self.parking_spots.items():
                if (status[1] == car.name):
                    if (status[0] == 'Assigned'):
                        self.parking_spots[spot]=(('Occupied',car.name))
                    elif (status[0] == 'Occupied'):
                        self.parking_spots[spot]=(('Vacant','None'))
                        await self.out_channels['Exit'].send(car)
                        self.spot_no=self.spot_no+1

    async def update_planner_response(self):
        async with self.in_channels['Planner']:
            async for response in self.in_channels['Planner']:
                car = response[0]
                resp = response[1]
                print('Supervisor - receiving "{0} - {1}" Response from Planner'.format(car.name,resp))
                await self.update_parking_spots(car)
                await trio.sleep(0)
        
    def pick_spot(self,car):
        for spot, status in self.parking_spots.items():
            if (status[0]=='Vacant'):
                self.parking_spots[spot]=(('Assigned',car.name))
                return spot

    async def process_queue(self):
        async for car in self.in_channels['Customer']:
            accept_condition = False
            print(str(self.spot_no)+' parking Spots vacant')
            print(self.parking_spots)
            if self.spot_no>0:
                accept_condition = True
            if accept_condition:
                print('{} has been accepted!'.format(car.name))
                await self.out_channels['Customer'].send(True)
                self.spot_no=self.spot_no-1
                await self.out_channels['Enter'].send(car)
                #map_sys.car_positions.update({car.name: (car.x,car.y)})
                #await trio.sleep(0)
                spot = self.pick_spot(car)
                await self.send_directive_to_planner(car,('Park',spot))
            else:
                await self.out_channels['Customer'].send(False)
                print('Garage fully occupied - A car has been rejected!')

    async def request_queue(self):
        async for car in self.in_channels['Request']:
            print('Supervisor - sending Directive to Planner to retrieve {}'.format(car.name))
            await self.send_directive_to_planner(car, 'Pickup')

    async def run(self):
        print(self.parking_spots)
        async with trio.open_nursery() as nursery:
            nursery.start_soon(self.process_queue)
            nursery.start_soon(self.request_queue)
            nursery.start_soon(self.update_planner_response)

class Customer(BoxComponent):
    def __init__(self, average_arrival_rate, average_park_time):
        super().__init__()
        self.name = self.__class__.__name__
        self.average_arrival_rate = average_arrival_rate
        self.average_park_time = average_park_time
        self.cars = []

    def generate_car(self):
        arrive_time = get_current_time()
        depart_time = arrive_time + np.random.exponential(self.average_park_time)
        car = Car(arrive_time=arrive_time, depart_time=depart_time)
        return car
        
    async def run(self,end_time):
        now = trio.current_time()
        #garage_open = True
        while True:
            # spawns cars according to exponential distribution
            await trio.sleep(np.random.exponential(1/self.average_arrival_rate))
            car = self.generate_car()
            self.cars.append(car)
            car.x = START_X
            car.y = START_Y
            car.yaw = START_YAW
            print("Car with ID {0} arrives at {1:.3f}".format(car.name, car.arrive_time))
            await self.out_channels['Supervisor'].send(car)
            accept = await self.in_channels['Supervisor'].receive() # checks if car is accepted by the garage
            if (accept == False):
                self.cars.pop()
            now = get_current_time()
            for i,car in enumerate(self.cars): # checks for requested cars
                if car.depart_time <= now:
                    print('{0} is requested at {1:.3f}'.format(car.name,car.depart_time))
                    await self.out_channels['Request'].send(car)
                    self.cars.pop(i)
            #if (now>=end_time):
            #    garage_open = False
            # Random sleeps help trigger the problem more reliably
            await trio.sleep(random.random())
        print('--------- It is {} time  --------'.format(trio.current_time()))
        print('The garage is closed now!')
            

async def main():
    global start_time
    start_time = trio.current_time()
    end_time = start_time + OPEN_TIME
    all_components = []
    print('--- Starting Parking Garage ---')
    async with trio.open_nursery() as nursery:
        map_sys = Map()
        #all_components.append(map_sys)
        supervisor = Supervisor()
        all_components.append(supervisor)
        planner = Planner(nursery=nursery)
        #all_components.append(planner)
        customer = Customer(average_arrival_rate = average_arrival_rate, average_park_time = average_park_time)
        #all_components.append(customer)
        # create communication channels
        create_bidirectional_channel(supervisor,planner,max_buffer_size=np.inf)
        create_bidirectional_channel(customer, supervisor, max_buffer_size=np.inf)
        create_unidirectional_channel(sender=customer, receiver=supervisor, max_buffer_size=np.inf, name='Request')
        create_unidirectional_channel(sender=supervisor, receiver=map_sys, max_buffer_size=np.inf, name='Enter')
        create_unidirectional_channel(sender=supervisor, receiver=map_sys, max_buffer_size=np.inf, name='Exit')
        create_bidirectional_channel(map_sys, planner, max_buffer_size=np.inf)
        send_update_channel, receive_update_channel = trio.open_memory_channel(25) # to track car positions
        for comp in all_components:
            nursery.start_soon(comp.run)        
        nursery.start_soon(customer.run,end_time)
        nursery.start_soon(map_sys.run,receive_update_channel)
        nursery.start_soon(planner.run,send_update_channel)

trio.run(main)