from datetime import timedelta, datetime
from typing import Union
from threading import Thread
from time import sleep, perf_counter


class PIDController:

    def __init__(self, cv_setter: callable,
                 kp: float = 1.0, ki: float = 0.0, kd: float = 0.0, initial_setpoint: float = 0.0,
                 cumulative_error_limit: float = None):
        # self._period = update_rate
        self._setpoint = initial_setpoint
        self._output_setter = cv_setter
        self._kp = kp
        self._ki = ki
        self._kd = kd
        self._error = 0.0
        self._cumulative_error = 0.0
        self._de_dt = 0.0
        self._last_value_time = None
        self._ie_limit = cumulative_error_limit
        self._cv_override = None
        self._cv = 0.0

    @property
    def error(self):
        return self._error

    @property
    def P(self):
        return self._kp*self._error

    @property
    def I(self):
        return self._ki*self._cumulative_error

    @property
    def D(self):
        return self._kd*self._de_dt

    @property
    def CV(self):
        if self._cv_override is None:
            # return self.P + self.I + self.D
            return self._cv
        else:
            return self._cv_override

    @property
    def setpoint(self):
        return self._setpoint

    @setpoint.setter
    def setpoint(self, value):
        assert isinstance(value, (int, float))
        self._setpoint = value
        self._cv_override = None
        self.reset()

    def reset(self):
        self._cv = 0.0
        self._error = 0.0
        self._cumulative_error = 0.0
        self._last_value_time = None

    @property
    def override_control_value(self):
        return self._cv_override

    @override_control_value.setter
    def override_control_value(self, value):
        self._cv_override = value

    def __call__(self, *args, **kwargs):
        call_time = perf_counter()
        next_error = self._setpoint - float(args[0])
        if self._last_value_time is not None:
            dt = call_time - self._last_value_time
            delta_error = next_error - self._error
            self._de_dt = delta_error/dt
            ie = dt*(self._error + (0.5*delta_error))
            ie += self._cumulative_error
            if self._ie_limit is not None:
                self._cumulative_error = max(min(ie, self._ie_limit), -self._ie_limit)
            else:
                self._cumulative_error = ie
        self._error = next_error
        self._last_value_time = call_time
        self._cv += self.P + self.I + self.D
        self._output_setter(self.CV)

