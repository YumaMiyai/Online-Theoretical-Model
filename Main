from instruments import FlowMeter, JKemTemperature, Pump, Valve, SynTQ, MovingAverage, Balance, PressureTransmitter
from time import sleep
from datetime import datetime, timedelta
from threading import Thread
from pid_control import PIDController
from sched import scheduler
from cfd import CFDModel
import sched, time


PUMP_OFF = 0.0
PUMP_TWO_AND_A_HALF_ML_MIN = 50.0

DIVERT_TO_WASTE = False
DIVERT_TO_COLLECTION = True

fluoro_flow = FlowMeter("\\\\PC-C6N8JC2\\Users\\Mettler\\Documents\\ContinuousFlowControl\\Fluoro.csv", 0.0038,
                        -0.7274)
cyclo_flow = FlowMeter("\\\\PC-C6N8JC2\\Users\\Mettler\\Documents\\ContinuousFlowControl\\Cyclo.csv", 0.0041,
                       -1.0507)
acrylate_flow = FlowMeter("\\\\PC-C6N8JC2\\Users\\Mettler\\Documents\\ContinuousFlowControl\\Acrylate.csv", 0.0048,
                          -0.9793)

acrylate_ma = MovingAverage(10)
fluoro_ma = MovingAverage(10)
cyclo_ma = MovingAverage(10)

ACRYLATE_DENSITY = 0.817
FLUORO_DENSITY = 0.901
CYCLO_DENSITY = 0.788

temperature_probe = JKemTemperature(
    "\\\\PC-C6N8JC2\\Users\\Mettler\\Documents\\ContinuousFlowControl\\Temperature.csv")

nodered_ip = '10.1.10.104'
valve = Valve(nodered_ip, 56000)

cyclo_pump = Pump(nodered_ip, 56001)
fluoro_pump = Pump(nodered_ip, 56002)
acrylate_pump = Pump(nodered_ip, 56003)
balance_data = Balance(nodered_ip, 56004)

reactor1 = CFDModel(1200, 1000, nx= 500, Volume=10e-6, dt=0.005)
#reactor2 = CFDModel(1, 1250, nx=500, Volume=5e-6 + 4.7e-6, dt=0.005, ArrheniusFactor=11.3, ActivationEnergy=23681, MolecularWeight=346.0)
reactor2 = CFDModel(1, 1250, nx=400, Volume=5e-6 + 3.36e-6, dt=0.005, ArrheniusFactor=11.3, ActivationEnergy=23681, MolecularWeight=346.0)

start_time = None

log_file = None


def set_pump(pump, cv):
    pump.speed_percent = max(min(cv, 75.0), 0.0)


def _log_data():
    global log_file
    human_time = datetime.now()
    log_time = human_time.timestamp()
    print(f'{human_time}')
    balance_values = balance_data.value
    waste_mass = balance_values['Waste Mass']
    collection_mass = balance_values['Collection Mass']
    log_file.write(','.join(
        [str(value) for value in
         [log_time, human_time, acrylate_pump.speed_percent, fluoro_pump.speed_percent, cyclo_pump.speed_percent,
          acrylate_flow.value, fluoro_flow.value, cyclo_flow.value, temperature_probe.value, valve.open, waste_mass, collection_mass,
          None, None, None]]))
          # None, None, pressure.value]]))
    log_file.write('\n')
    log_file.flush()


def log_data(acrylate_flowrate, fluoro_flowrate, cyclo_flowrate, reactor_1_temperature, valve_state, pressure,
             concentrations):
    global log_file
    human_time = datetime.now()
    log_time = human_time.timestamp()
    print(f'{human_time}')
    print(f'Pressure: {pressure}')
    print(
        f'\tReactor 1 Output Concentration: {concentrations[0]:6.4} mg/mL\tReactor 2 Output Concentration: {concentrations[1]:6.4} mg/mL')

    balance_values = balance_data.value
    waste_mass = balance_values['Waste Mass']
    collection_mass = balance_values['Collection Mass']

    log_file.write(','.join(
        [str(value) for value in
         [log_time, human_time, acrylate_pump.speed_percent, fluoro_pump.speed_percent, cyclo_pump.speed_percent,
          acrylate_flowrate, fluoro_flowrate, cyclo_flowrate, reactor_1_temperature, valve_state, waste_mass, collection_mass,
          concentrations[0], concentrations[1], pressure]]))
    log_file.write('\n')
    log_file.flush()


def step_1():

    valve.open = DIVERT_TO_WASTE


def step_2():
    temperature_probe.normal_operating_range = (20, 153)
    while not temperature_probe.within_range:
        print(
            f'Step 2: Waiting for temperature to reach {temperature_probe.normal_operating_range[0]} degrees.  Current value: {temperature_probe.value}')
        _log_data()
        sleep(2.0)

    fluoro_pump.speed_percent = PUMP_TWO_AND_A_HALF_ML_MIN
    acrylate_pump.speed_percent = PUMP_TWO_AND_A_HALF_ML_MIN
    cyclo_pump.speed_percent = PUMP_TWO_AND_A_HALF_ML_MIN


def step_3_and_4():
    start_time = datetime.now()
    duration = timedelta(days=1, minutes=25.0)

    continue_current_step = True

    acrylate_flow.normal_operating_range = (1.8, 3.2)
    fluoro_flow.normal_operating_range = (1.8, 3.2)

    temperature_probe.normal_operating_range = (145, 155)

    checked_instruments = [temperature_probe]

    def process_inputs():
        while continue_current_step:
            try:
               
                temperature = temperature_probe.value

                acrylate_flowrate = acrylate_ma(acrylate_flow.value)
                fluoro_flowrate = fluoro_ma(fluoro_flow.value)
                cyclo_flowrate = cyclo_ma(cyclo_flow.value)

                acrylate_flowrate = acrylate_flowrate if acrylate_flowrate > 0 else 0.0
                fluoro_flowrate = fluoro_flowrate if fluoro_flowrate > 0 else 0.0
                cyclo_flowrate = cyclo_flowrate if cyclo_flowrate > 0 else 0.0

                print(f'Acrylate flowrate: {acrylate_flowrate:6.4}\tFluoro flowrate: {fluoro_flowrate:6.4}\tCyclo flowrate: {cyclo_flowrate:6.4}')

                acrylate_flowrate = acrylate_flowrate*1.667e-8
                fluoro_flowrate = fluoro_flowrate*1.667e-8
                cyclo_flowrate = cyclo_flowrate*1.667e-8

                reactor1.set_temperature_in_degrees_celsius(temperature)
                reactor1.species_A_flowrate = acrylate_flowrate
                reactor1.species_B_flowrate = fluoro_flowrate

                reactor1.update()

                reactor2.set_temperature_in_degrees_celsius(25.0)
                reactor2.species_A_flowrate = reactor1.combined_flowrate
                reactor2.species_B_flowrate = cyclo_flowrate
                reactor2.species_A_stock_concentration = reactor1.default_product_concentration

                reactor2.update()

                predicted_concentration = (reactor1.product_concentration*0.96*0.98, reactor2.product_concentration*0.96*0.98)

             
                if predicted_concentration[1] < 100:
                    valve.open = DIVERT_TO_WASTE
                else:
                    valve.open = DIVERT_TO_COLLECTION
               
                log_data(acrylate_flowrate, fluoro_flowrate, cyclo_flowrate, temperature, valve.open, None,
                         predicted_concentration)
            except Exception as ex:
                print(ex)

                sleep(0.1)

    try:
        process_thread = Thread(target=process_inputs)
        process_thread.start()

        print(f'Waiting for a duration of {duration}')
        while (datetime.now() - start_time) < duration:
            sleep(1.0)
    except KeyboardInterrupt:
        pass

    continue_current_step = False
    process_thread.join(10.0)


def step_5():

    fluoro_pump.speed_percent = PUMP_OFF
    acrylate_pump.speed_percent = PUMP_OFF
    cyclo_pump.speed_percent = PUMP_OFF
    valve.open = DIVERT_TO_WASTE


def step_6():
    pass
   

def main(filename: str):
    global log_file
   
    log_file = open(filename, 'a+')
    log_file.write(
        'Timestamp,'
        'Human Timestamp,'
        'Acrylate Pump,'
        'Fluoro Pump,'
        'Cyclo Pump,'
        'Acrylate Flowrate,'
        'Fluoro Flowrate,'
        'Cyclo Flowrate,'
        'Temperature,'
        'Valve Set to Collection,'
        'Waste Mass,'
        'Collection Mass,'
        'Reactor 1 Product Concentration,'
        'Reactor 2 Product Concentration,'
        'Pressure\n')
    try:
        print('Starting step 1')
        step_1()
        print('Starting step 2')
        step_2()
        print('Starting step 3 and 4')
        step_3_and_4()
        print('Starting step 5')
        step_5()
        print('Starting step 6')
        step_6()
        print('Done')
    finally:
        log_file.close()


if __name__ == '__main__':

    filename = input('Enter the name for the CSV file (minus the .csv): ') + '.csv'

    try:
        print('Waiting for data from instruments')
        for instrument in [temperature_probe, fluoro_flow, acrylate_flow, cyclo_flow]:
           
            while instrument.value is None:
                print(f'Waiting for data from {instrument}...')
                sleep(1.0)
      
        main(filename)
       
    except KeyboardInterrupt:
        pass
    except Exception as ex:
        print(f'{type(ex)} exception occurred in main function: {ex}')
    finally:
        valve.open = DIVERT_TO_WASTE
        print('Closing files')
        fluoro_flow.close()
        cyclo_flow.close()
        acrylate_flow.close()
        temperature_probe.close()
      
        print('Files closed')

    print('Exiting')
    exit(0)
