import socket, sys, json, threading, queue
from time import sleep


class Valve:

    def __init__(self, host: str, port: int):
        self._host = host
        self._port = port

        self._open = False

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.settimeout(10.0)
        try:
            self._socket.connect((self._host, self._port))
            print(f'Connected')
        except socket.timeout:
            print(f'Could not connect to the Raspberry Pi')
            raise BrokenPipeError(f'No Raspberry Pi found')

    @property
    def open(self) -> bool:
        return self._open

    @open.setter
    def open(self, value: bool):
        try:
            if not isinstance(value, bool):
                raise TypeError
            self._socket.send(str(value).encode('utf-8'))
            self._open = value
        except Exception as ex:
            print(ex)

    def __del__(self):
        self._socket.close()
