import socket, sys, json, threading, queue
from time import sleep


class Pump:

    def __init__(self, host: str, port: int):
        self._host = host
        self._port = port

        self._percent = 0.0

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.settimeout(10.0)
        try:
            self._socket.connect((self._host, self._port))
            print(f'Connected')
        except socket.timeout:
            print(f'Could not connect to the Raspberry Pi')
            raise BrokenPipeError(f'No Raspberry Pi found')

    @property
    def speed_percent(self) -> float:
        return self._percent

    @speed_percent.setter
    def speed_percent(self, value: float):
        try:
            if not isinstance(value, float):
                raise TypeError
            if value < 0:
                value = 0
            elif value > 100:
                value = 100
            self._set_speed_in_percent(value)
        except Exception as ex:
            print(ex)

    def _set_speed_in_percent(self, value):
        self._socket.send(str(value).encode('utf-8'))

    def __del__(self):
        self._socket.close()
