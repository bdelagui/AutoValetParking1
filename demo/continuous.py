import trio
import sys
sys.path.append('..') # enable importing modules from an upper directory:
# import 
from prepare.communication import *
from variables.global_vars import *
# import components
from components.boxcomponent import Time
from components.game import Game
from components.simulation import Simulation
from components.map  import Map
from components.planner import Planner
from environment.pedestrian import Pedestrian
from components.car import Car
from components.supervisor import Supervisor
from environment.customer import Customer

async def main():
    #global START_TIME
    START_TIME = trio.current_time()
    END_TIME = START_TIME + OPEN_TIME
    time_sys = Time(START_TIME, END_TIME)
    all_components = []
    print('--- Starting Parking Garage ---')
    print('At time: '+str(START_TIME))
    async with trio.open_nursery() as nursery:
        map_sys = Map()
        all_components.append(map_sys)
        simulation = Simulation()
        all_components.append(simulation)
        supervisor = Supervisor(nursery = nursery)
        #all_components.append(supervisor)
        game = Game()
        all_components.append(game)
        planner = Planner(nursery=nursery)
        #all_components.append(planner)
        customer = Customer(average_arrival_rate = average_arrival_rate, average_park_time = average_park_time)
        #create communication channels
        set_up_channels(supervisor,planner, game, map_sys, customer, simulation)
        # start nursery
        for comp in all_components:
            nursery.start_soon(comp.run)
            await trio.sleep(0)
        nursery.start_soon(planner.run, game, time_sys)
        nursery.start_soon(supervisor.run, planner, time_sys)
        nursery.start_soon(customer.run,END_TIME,START_TIME, game)

trio.run(main)