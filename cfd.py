import time
import numpy as np
from numpy import genfromtxt, ndarray
import math
import random

"""
Constants
"""
const_R = 8.314  # gas constant (J/mol/K)


class CFDModel:
    _species_A_flowrate: float
    _species_B_flowrate: float
    _species_A_stock_concentration: float
    _species_B_stock_concentration: float
    _temperature: float
    _A: ndarray
    _An: ndarray
    _B: ndarray
    _Bn: ndarray
    _C: ndarray
    _Cn: ndarray
    _T: ndarray
    _Tn: ndarray
    _k1: ndarray
    _tolcheck: ndarray

    def __init__(self, species_A_concentration: float, species_B_concentration: float, **kwargs):
        """
        PFR CFD reactor_1
        :param species_A_concentration: Stock concentration of species A (acrylate) (mol/m3)
        :param species_B_concentration: Stock concentration of species B (fluoro) (mol/m3)
        """

        self.D = kwargs['Diameter'] if 'Diameter' in kwargs else 0.0015875 # tubing diameter in m
        self.Ac1 = math.pi * (self.D / 2) ** 2  # cross-sectional area (m2)
        self.V1 = kwargs['Volume'] if 'Volume' in kwargs else 2.0 * 10 ** -5  # reactor volume (m^3)
        self.xl1 = self.V1 / self.Ac1  # reactor tubing length (m)
        self.nx1 = kwargs['nx'] if 'nx' in kwargs else 50  # spatial solution size for x
        self.dx1 = self.xl1 / (self.nx1 - 1)  # x step
        self.dt1 = kwargs['dt'] if 'dt' in kwargs else .0075  # time step
        self.D1 = kwargs['AxialDispersion'] if 'AxialDispersion' in kwargs else .0005  # axial dispersion coefficient (m^2/s)
        self.x1 = np.linspace(0, self.xl1, self.nx1)  # spatial array

        self.k = kwargs['ThermalConductivity'] if 'ThermalConductivity' in kwargs else .12  # thermal conductivity W/(m*K)
        self.p = kwargs['Density'] if 'Density' in kwargs else 1750  # density (kg/m3)
        self.Cp = kwargs['SpecificHeat'] if 'SpecificHeat' in kwargs else 1172  # specific heat (J/kg/K)
        self.a = self.k / (self.p * self.Cp)  # thermal diffusivity (m2/s)
        self.Nu = kwargs['NusseltLaminarFlow'] if 'NusseltLaminarFlow' in kwargs else 3.66  # nusselt laminar flow in tube
        self.h = self.Nu * self.k / self.D  # convective heat transfer coefficient (W/m2/K)
        self.T0 = kwargs['InletTemperature'] if 'InletTemperature' in kwargs else 25 + 273.15  # stream inlet temperature (degK)
        self.reltol = kwargs['ConvergenceTolerance'] if 'ConvergenceTolerance' in kwargs else 1e-8  # tolerance for convergence
        self.lam = self.a * self.dt1 / self.dx1 ** 2  # heat transfer coefficient
        self.dHr = kwargs['HeatOfReaction'] if 'HeatOfReaction' in kwargs else 0
        self.molecular_weight = kwargs['MolecularWeight'] if 'MolecularWeight' in kwargs else 334.17

        self.sample_steps = kwargs['SampleSteps'] if 'SampleSteps' in kwargs else 1000

        self.Ea1 = kwargs['ActivationEnergy'] if 'ActivationEnergy' in kwargs else 51080  # activation energy (J/mol)
        self.k01 = kwargs['ArrheniusFactor'] if 'ArrheniusFactor' in kwargs else 923.8  # arrhenius factor (m3/mol/s)

        self._species_A_flowrate = 0.0
        self._species_B_flowrate = 0.0
        self._species_A_stock_concentration = species_A_concentration
        self._species_B_stock_concentration = species_B_concentration
        self._temperature = 25 + 273.15

        self._A = np.ones(self.nx1)  # species A solution array
        self._An = np.ones(self.nx1)  # species A temporary solution array
        self._B = np.ones(self.nx1)  # species B solution array
        self._Bn = np.ones(self.nx1)  # species B temporary solution array
        self._C = np.zeros(self.nx1)  # species C solution array
        self._Cn = np.zeros(self.nx1)  # species C temporary solution array
        self._T = np.ones(self.nx1)*self.T0
        self._Tn = np.ones(self.nx1)*self.T0
        self._k1 = self.k01 * np.exp(-self.Ea1 / const_R / self._T[1:-1])
        self._tolcheck = np.ones(self.nx1)

        self._last_sample_time = None

    def reset_arrays(self):
        self._tolcheck = np.ones(self.nx1)
        self._A = np.ones(self.nx1)  # species A solution array
        self._An = np.ones(self.nx1)  # species A temporary solution array
        self._B = np.ones(self.nx1)  # species B solution array
        self._Bn = np.ones(self.nx1)  # species B temporary solution array
        self._C = np.zeros(self.nx1)  # species C solution array
        self._Cn = np.zeros(self.nx1)  # species C temporary solution array
        self._T = np.ones(self.nx1)
        self._Tn = np.ones(self.nx1)
        self._k1 = self.k01 * np.exp(-self.Ea1 / const_R / self._T[1:-1])

    # region Temperature
    @property
    def temperature(self) -> float:
        """
        Temperature measured by the temperature probe
        :return: Temperature (degrees K)
        """
        return self._temperature

    @temperature.setter
    def temperature(self, value: float):
        self._temperature = value

    def set_temperature_in_degrees_celsius(self, value: float) -> None:
        """
        Set the temperature value (stored as degrees K) using a value in degrees Celsius
        :param value: Temperature in degrees Celsius
        :return: None
        """
        self._temperature = value + 273.15

    # endregion

    # region Concentration
    @property
    def species_A_stock_concentration(self) -> float:
        return self._species_A_stock_concentration

    @species_A_stock_concentration.setter
    def species_A_stock_concentration(self, value):
        self._species_A_stock_concentration = value

    @property
    def species_B_stock_concentration(self):
        return self._species_B_stock_concentration

    @species_B_stock_concentration.setter
    def species_B_stock_concentration(self, value):
        self._species_B_stock_concentration = value

    @property
    def species_B_stream_concentration(self):
        """
        :return: Fluoro (species B) molar stream concentration (mol/m3)
        """
        try:
            return self.species_B_stock_concentration * self.species_B_flowrate / self.combined_flowrate
        except:
            return 0

    @property
    def species_A_stream_concentration(self):
        """
        :return: Acrylate (species A) molar stream concentration (mol/m3)
        """
        try:
            return self.species_A_stock_concentration * self.species_A_flowrate / self.combined_flowrate
        except:
            return 0.0

    @property
    def product_concentration(self) -> float:
        """
        Product concentration (mg/mL)
        :return:
        """
        return (self._C[self.nx1 - 1] / 1000) * 334.17

    @property
    def default_product_concentration(self):
        """
        Product concentration (mol/m^3)
        :return:
        """
        return self._C[self.nx1 - 1]

    # endregion

    # region Flowrate
    @property
    def species_A_flowrate(self) -> float:
        """
        :return: Acrylate flowrate in mL/min
        """
        return self._species_A_flowrate

    @species_A_flowrate.setter
    def species_A_flowrate(self, value):
        self._species_A_flowrate = value

    def set_acrylate_flowrate_in_microliters_per_second(self, value: float):
        self.species_A_flowrate = ((value * 0.00582) - 1.55) * 1.66667 * 10 ** -8

    @property
    def species_B_flowrate(self) -> float:
        """
        :return: Fluoro flowrate in mL/min
        """
        return self._species_B_flowrate

    @species_B_flowrate.setter
    def species_B_flowrate(self, value):
        self._species_B_flowrate = value

    def set_fluoro_flowrate_in_microliters_per_second(self, value: float):
        self.species_B_flowrate = ((value * 0.00582) - 1.55) * 1.66667 * 10 ** -8

    @property
    def combined_flowrate(self) -> float:
        """
        Function that uses flowrate readings to calculate combined flowrates and velocity
        Flowrates from sensirion are uL/s, converted to mL/min with calibration, then unit conversion to m3/s
        :return: Combined flowrate
        """
        return self.species_A_flowrate + self.species_B_flowrate

    @property
    def stream_velocity(self) -> float:
        """
        :return: Average velocity (m/s)
        """
        return self.combined_flowrate / self.Ac1

    # endregion

    def _tolerance_check(self) -> ndarray:
        """
        Compares norms of current and previous solution arrays
        :return:
        """
        return np.abs((np.linalg.norm(self._tolcheck) - np.linalg.norm(self._Cn)) / np.linalg.norm(self._Cn))

    def _uds(self, species: ndarray, stoichiometry: float):
        return species[1:-1] - self.stream_velocity * (self.dt1 / self.dx1) * (species[1:-1] - species[:-2]) \
               + self.D1 * self.dt1 / self.dx1 ** 2 * (species[2:] - 2 * species[1:-1] + species[:-2]) \
               + stoichiometry * self._k1 * self._An[1:-1] * self._Bn[1:-1] * self.dt1

    def update(self, dt = None) -> None:
        """
        Function that uses all defined and calculated values to solve for the reaction progression in the tubular reactor
        :return: None
        """
        now = time.time()
        num_steps = 1000
        if dt is None:
            if not self._last_sample_time:
                self._last_sample_time = now
            else:
                time_difference = now - self._last_sample_time
                num_steps = time_difference / self.dt1
                self._last_sample_time = now
        else:
            num_steps = dt / self.dt1

        stepcount = 0

        while stepcount < num_steps:

            self._T[0] = self.T0  # impose dirichlet BC
            self._T[self.nx1 - 1] = self._T[self.nx1 - 2]  # impose neumann BC
            self._Tn = self._T.copy()  # update temporary array

            self._T[1:-1] = self._Tn[1:-1] - (
                        self.stream_velocity * (self.dt1 / self.dx1) * (self._Tn[1:-1] - self._Tn[:-2])) \
                            + self.lam * (self._Tn[2:] - 2 * self._Tn[1:-1] + self._Tn[:-2]) \
                            - self.h * self.D * math.pi * (self._Tn[
                                                           1:-1] - self.temperature) * self.dt1 / self.p / self.Cp * self.xl1 / self.V1 \
                            - self.dHr * self._k1 * self._A[1:-1] * self._B[1:-1] / self.p / self.Cp * self.dt1
            self._k1 = self.k01 * np.exp(-self.Ea1 / const_R / self._T[1:-1])

            self._A[0] = self.species_A_stream_concentration
            self._B[0] = self.species_B_stream_concentration
            self._A[self.nx1 - 1] = self._A[self.nx1 - 2]
            self._B[self.nx1 - 1] = self._B[self.nx1 - 2]
            self._C[self.nx1 - 1] = self._C[self.nx1 - 2]

            self._An = self._A.copy()
            self._Bn = self._B.copy()
            self._Cn = self._C.copy()

            self._A[1:-1] = self._uds(self._An, -1.0)  # UDS(u1, dt1, dx1, D1, k1, An, An, Bn, -1.0)
            self._B[1:-1] = self._uds(self._Bn, -1.0)  # UDS(u1, dt1, dx1, D1, k1, Bn, An, Bn, -1.0)
            self._C[1:-1] = self._uds(self._Cn, 1.0)  # UDS(u1, dt1, dx1, D1, k1, Cn, An, Bn, 1.0)

            self._tolcheck = self._C.copy()
            stepcount += 1  # update counter


if __name__ == '__main__':
    reactor_1 = CFDModel(1200, 1000, nx=1500, Volume=10e-6)
    reactor_2 = CFDModel(0, 1250, Volume=5e-6, ActivationEnergy=23681, ArrheniusFactor=11.3, nx=750)

    start_time = time.time()

    with open('two_reactor_sim.csv','a') as output_file:
        output_file.write(f'Time,Reactor 1 Output Concentration,Reactor 2 Output Concentration\n')

        try:
            t = 0
            while True:
                reactor_1.set_temperature_in_degrees_celsius(150.0)
                reactor_2.set_temperature_in_degrees_celsius(150.0)

                if t > 200000:
                    reactor_1.species_A_flowrate = 1.7 * 1.66667e-8
                else:
                    reactor_1.species_A_flowrate = 2.5 * 1.66667e-8
                if t > 200000:
                    reactor_1.species_B_flowrate = 1.7 * 1.66667e-8
                else:
                    reactor_1.species_B_flowrate = 2.5 * 1.66667e-8
    
                reactor_1.update()

                reactor_2.species_A_flowrate = reactor_1.species_A_flowrate + reactor_1.species_B_flowrate
                reactor_2.species_B_flowrate = 2.5 * 1.66667e-8
                reactor_2.species_A_stock_concentration = reactor_1.default_product_concentration
                reactor_2.update()

                t = time.time() - start_time
                print(f'The predicted product output concentration at {t} seconds is:\n'
                      f'\tReactor 1: {reactor_1.product_concentration:0.4}\tReactor 2: {reactor_2.product_concentration:0.4}')
                output_file.write(f'{t},{reactor_1.product_concentration},{reactor_2.product_concentration}\n')
                output_file.flush()

                time.sleep(2 + random.random())  # pauses reactor_1 loop before refreshing and updating next solution
        except KeyboardInterrupt:
            output_file.flush()

