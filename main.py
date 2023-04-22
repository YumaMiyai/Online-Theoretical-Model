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

# acrylate_raman = SynTQ("\\\\DESKTOP-PG7HAVP\\synTQ_Shared_Data\\AcrylateRamanFileWriter.csv")
# product_ir = SynTQ("\\\\DESKTOP-PG7HAVP\\SynTQRoot\\synTQ_Shared_Data\\ProductIR.csv")
# fluoro_raman = SynTQ("\\\\DESKTOP-PG7HAVP\\SynTQRoot\\synTQ_Shared_Data\\FluoroRaman.csv")

temperature_probe = JKemTemperature(
    "\\\\PC-C6N8JC2\\Users\\Mettler\\Documents\\ContinuousFlowControl\\Temperature.csv")

nodered_ip = '10.1.10.104'
valve = Valve(nodered_ip, 56000)

cyclo_pump = Pump(nodered_ip, 56001)
fluoro_pump = Pump(nodered_ip, 56002)
acrylate_pump = Pump(nodered_ip, 56003)
balance_data = Balance(nodered_ip, 56004)
# pressure = PressureTransmitter(nodered_ip, 56005)

reactor1 = CFDModel(1200, 1000, nx= 500, Volume=10e-6, dt=0.005)
#reactor2 = CFDModel(1, 1250, nx=500, Volume=5e-6 + 4.7e-6, dt=0.005, ArrheniusFactor=11.3, ActivationEnergy=23681, MolecularWeight=346.0)
reactor2 = CFDModel(1, 1250, nx=400, Volume=5e-6 + 3.36e-6, dt=0.005, ArrheniusFactor=11.3, ActivationEnergy=23681, MolecularWeight=346.0)

start_time = None

log_file = None


def set_pump(pump, cv):
    # pump.speed_percent = max(min(cv, 100.0), 0.0)
    pump.speed_percent = max(min(cv, 75.0), 0.0)


# fluoro_controller = PIDController(lambda cv: set_pump(fluoro_pump, cv), kp=0.4, ki=0.025, kd=0.25,
#                                   cumulative_error_limit=10.0)
# acrylate_controller = PIDController(lambda cv: set_pump(acrylate_pump, cv), kp=0.4, ki=0.025, kd=0.25,
#                                     cumulative_error_limit=10.0)
# solvent_controller = PIDController(lambda cv: set_pump(cyclo_pump, cv), kp=0.4, ki=0.025, kd=0.25,
#                                    cumulative_error_limit=10.0)
#
# fluoro_controller.override_control_value = 0.0
# acrylate_controller.override_control_value = 0.0
# solvent_controller.override_control_value = 0.0
#
# fluoro_flow.on_message(fluoro_controller)
# acrylate_flow.on_message(acrylate_controller)
# cyclo_flow.on_message(solvent_controller)


# def log_data():
#     global log_file
#     human_time = datetime.now()
#     log_time = human_time.timestamp()
#     print(f'{human_time}')
#     print(f'Pressure: {pressure.value}')
#     log_file.write(','.join(
#         [str(value) for value in [log_time, human_time, acrylate_pump.speed_percent, fluoro_pump.speed_percent, cyclo_pump.speed_percent,
#          acrylate_flow.value, fluoro_flow.value, cyclo_flow.value, acrylate_raman.value, fluoro_raman.value,
#          product_ir.value, temperature_probe.value, valve.open, None, None, pressure.value]]))
#          # product_ir.value, temperature_probe.value, valve.open, balance_data.value['Waste Mass'], balance_data.value['Collection Mass'], pressure.value]]))
#     log_file.write('\n')
#     log_file.flush()

def _log_data():
    global log_file
    human_time = datetime.now()
    log_time = human_time.timestamp()
    print(f'{human_time}')
    # print(f'Pressure: {pressure.value}')
    balance_values = balance_data.value
    waste_mass = balance_values['Waste Mass']
    collection_mass = balance_values['Collection Mass']
    log_file.write(','.join(
        [str(value) for value in
         [log_time, human_time, acrylate_pump.speed_percent, fluoro_pump.speed_percent, cyclo_pump.speed_percent,
          acrylate_flow.value, fluoro_flow.value, cyclo_flow.value, temperature_probe.value, valve.open, waste_mass, collection_mass,
          None, None, None]]))
          # None, None, pressure.value]]))
    # product_ir.value, temperature_probe.value, valve.open, balance_data.value['Waste Mass'], balance_data.value['Collection Mass'], pressure.value]]))
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

    # print(f'\tCalculated flow rates from balance data:\n\t\tFluoro: {balance_values["Fluoro Mass Flowrate"]/FLUORO_DENSITY:6.4}\tAcrylate: {balance_values["Acrylate Mass Flowrate"]/ACRYLATE_DENSITY:6.4}\tCyclo: {balance_values["Cyclo Mass Flowrate"]/CYCLO_DENSITY:6.4}')
    # print(f'\tFluoro: {fluoro_flowrate:6.4}\tAcrylate: {acrylate_flowrate:6.4}\tCyclo: {cyclo_flowrate:6.4}')

    log_file.write(','.join(
        [str(value) for value in
         [log_time, human_time, acrylate_pump.speed_percent, fluoro_pump.speed_percent, cyclo_pump.speed_percent,
          acrylate_flowrate, fluoro_flowrate, cyclo_flowrate, reactor_1_temperature, valve_state, waste_mass, collection_mass,
          concentrations[0], concentrations[1], pressure]]))
    log_file.write('\n')
    log_file.flush()


# def pid_tune_function():
#     # ma = MovingAverage(4)
#     setpoint = 3.5
#     i = 0
#     while True:
#         if setpoint < 0:
#             break
#         try:
#             solvent_controller.setpoint = setpoint
#             while True:
#                 print(
#                     f'Setpoint: {solvent_controller.setpoint:0.2}\tSolvent: {cyclo_flow.value:0.2}\tFluoro: {fluoro_flow.value:0.2}\tAcrylate: {acrylate_flow.value:0.2}')
#                     # f'Solvent (MovingAverage): {ma(cyclo_flow.value):0.2}\tFluoro: {fluoro_flow.value:0.2}\tAcrylate: {acrylate_flow.value:0.2}')
#                 sleep(0.25)
#                 i += 1
#                 if i == 100:
#                     solvent_controller.setpoint = 2.5
#         except KeyboardInterrupt:
#             setpoint = float(input('Enter desired flow rate for solvent: '))


def step_1():
    """
    Manually turn on hot plate to 150 degrees Celsius
    :return: None
    """
    valve.open = DIVERT_TO_WASTE


def step_2():
    # temperature_probe.normal_operating_range = (147, 153)
    temperature_probe.normal_operating_range = (20, 153)
    while not temperature_probe.within_range:
        print(
            f'Step 2: Waiting for temperature to reach {temperature_probe.normal_operating_range[0]} degrees.  Current value: {temperature_probe.value}')
        _log_data()
        sleep(2.0)

    # Set fluoro and acrylate pumps to 2.5 ml/min
    # fluoro_controller.setpoint = 2.4
    # acrylate_controller.setpoint = 2.5
    fluoro_pump.speed_percent = PUMP_TWO_AND_A_HALF_ML_MIN
    acrylate_pump.speed_percent = PUMP_TWO_AND_A_HALF_ML_MIN
    cyclo_pump.speed_percent = PUMP_TWO_AND_A_HALF_ML_MIN


def step_3_and_4():
    start_time = datetime.now()
    duration = timedelta(days=1, minutes=25.0)

    continue_current_step = True

    # acrylate_raman.normal_operating_range = (1.05, 1.35)
    # fluoro_raman.normal_operating_range = (0.85, 1.15)
    # product_ir.normal_operating_range = (150, 190)

    acrylate_flow.normal_operating_range = (1.8, 3.2)
    fluoro_flow.normal_operating_range = (1.8, 3.2)

    temperature_probe.normal_operating_range = (145, 155)

    # checked_instruments = [acrylate_raman, fluoro_raman, product_ir, acrylate_flow, fluoro_flow, temperature_probe]
    # checked_instruments = [acrylate_raman, fluoro_raman, product_ir, temperature_probe]
    checked_instruments = [temperature_probe]

    # s = sched.scheduler(time.time, time.sleep)

    def process_inputs():
        while continue_current_step:
            try:
                # print(
                #     f'Solvent: {cyclo_flow.value:0.2}\tFluoro: {fluoro_flow.value:0.2}\tAcrylate: {acrylate_flow.value:0.2}')
                # if all([ins.within_range for ins in checked_instruments]):
                #     print('Inside normal operating conditions.  Diverting to collection.')
                #     valve.open = DIVERT_TO_COLLECTION
                # else:
                #     print('Outside normal operating conditions. Diverting to waste. ')
                #     for ins in checked_instruments:
                #         if not ins.within_range:
                #             print(f'{ins} outside of normal operating range {ins.normal_operating_range}: {ins.value:0.2}')
                #     valve.open = DIVERT_TO_WASTE
                # log_data()
                # sleep(1.0)
                temperature = temperature_probe.value
                # balance_values = balance_data.value

                # acrylate_flowrate = acrylate_ma(acrylate_flow.value*1.667e-8)
                # fluoro_flowrate = fluoro_ma(fluoro_flow.value*1.667e-8)
                # cyclo_flowrate = cyclo_ma(cyclo_flow.value*1.667e-8)

                acrylate_flowrate = acrylate_ma(acrylate_flow.value)
                fluoro_flowrate = fluoro_ma(fluoro_flow.value)
                cyclo_flowrate = cyclo_ma(cyclo_flow.value)

                # calculated_acrylate_flowrate = balance_values['Acrylate Mass Flowrate']/ACRYLATE_DENSITY
                # calculated_fluoro_flowrate = balance_values['Fluoro Mass Flowrate'] / FLUORO_DENSITY
                # calculated_cyclo_flowrate = balance_values['Cyclo Mass Flowrate'] / FLUORO_DENSITY
                #
                # calculated_acrylate_flowrate = calculated_acrylate_flowrate if calculated_acrylate_flowrate < 5 else acrylate_flowrate
                # calculated_fluoro_flowrate = calculated_fluoro_flowrate if calculated_fluoro_flowrate < 5 else fluoro_flowrate
                # calculated_cyclo_flowrate = calculated_cyclo_flowrate if calculated_cyclo_flowrate < 5 else cyclo_flowrate
                #
                # acrylate_flowrate = acrylate_flowrate if acrylate_flowrate < 1 else calculated_acrylate_flowrate
                # fluoro_flowrate = fluoro_flowrate if fluoro_flowrate < 1 else calculated_fluoro_flowrate
                # cyclo_flowrate = cyclo_flowrate if cyclo_flowrate < 1 else calculated_cyclo_flowrate

                # print(f'Acrylate flowrate: {acrylate_ma.value:5.2}\tFluoro flowrate: {fluoro_ma.value:5.2}')

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

                # def print_time(a='default'):
                #     print("From print_time", time.time(), a)
                #
                # def print_some_times():
                #     print(time.time())
                #
                # s.enter(10, 1, print_time)
                # s.enter(5, 2, print_time, argument=('positional',))
                # s.enter(5, 1, print_time, kwargs={'a': 'keyword'})
                # s.run()
                # print(time.time())

                if predicted_concentration[1] < 100:
                    valve.open = DIVERT_TO_WASTE
                else:
                    valve.open = DIVERT_TO_COLLECTION
                # log_data(acrylate_flowrate, fluoro_flowrate, cyclo_flowrate, temperature, valve.open, pressure.value,
                #          predicted_concentration)
                log_data(acrylate_flowrate, fluoro_flowrate, cyclo_flowrate, temperature, valve.open, None,
                         predicted_concentration)
            except Exception as ex:
                print(ex)

            # sleep(0.038)
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
    # fluoro_controller.override_control_value = 0.0
    # acrylate_controller.override_control_value = 0.0
    fluoro_pump.speed_percent = PUMP_OFF
    acrylate_pump.speed_percent = PUMP_OFF
    cyclo_pump.speed_percent = PUMP_OFF
    valve.open = DIVERT_TO_WASTE


def step_6():
    pass
    # cyclo_pump.speed_percent = PUMP_TWO_AND_A_HALF_ML_MIN
    # # solvent_controller.setpoint = 3.0
    # start_time = datetime.now()
    # duration = timedelta(minutes=15.0)
    #
    # print(f'Waiting for a duration of {duration}')
    # while (datetime.now() - start_time) < duration:
    #     log_data()
    #     sleep(1.0)
    #
    # cyclo_pump.speed_percent = PUMP_OFF
    # # solvent_controller.override_control_value = 0.0


def main(filename: str):
    global log_file
    # log_file = open('C:\\Users\\Mettler\\Desktop\\PythonOrchestration\\InstrumentData.csv', 'a+')
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
        # 'Acrylate Concentration,'
        # 'Cyclo Concentration,'
        # 'Product Concentration,'
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
            # for instrument in [temperature_probe, fluoro_flow, acrylate_flow, cyclo_flow, acrylate_raman, fluoro_raman,
            #                    product_ir]:
            # product_ir, balance_data]:
            while instrument.value is None:
                print(f'Waiting for data from {instrument}...')
                sleep(1.0)
        # while temperature_probe.value is None or fluoro_flow.value is None or acrylate_flow.value is None or cyclo_flow.value is None:
        #     sleep(1.0)
        main(filename)
        # pid_tune_function()
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
        # acrylate_raman.close()
        # fluoro_raman.close()
        # product_ir.close()
        print('Files closed')

    print('Exiting')
    exit(0)
