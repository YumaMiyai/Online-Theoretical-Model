import socket, sys, json, threading, queue
from time import sleep


class PressureTransmitter:

    def __init__(self, host: str, port: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._host = host
        self._port = port

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.settimeout(10.0)
        try:
            self._socket.connect((self._host, self._port))
            print(f'Connected')
        except socket.timeout:
            print(f'Could not connect to the Raspberry Pi')
            raise BrokenPipeError(f'No Raspberry Pi found')

    def __del__(self):
        self._socket.close()

    @property
    def value(self):
        try:
            self._socket.send('GetValue'.encode('utf-8'))
            data = self._socket.recv(1024).decode('utf-8')
            data = json.loads(data)
            return data
        except Exception as ex:
            print(f'{type(ex)} exception occurred while getting pressure data from Node-RED: {ex}')
            return None


if __name__ == '__main__':
    nodered_ip = '10.1.10.104'

    pressure_data = PressureTransmitter(nodered_ip, 56005)

    try:
        while True:
            print(f'Pressure: {pressure_data.value}')
            sleep(1.0)
    except KeyboardInterrupt:
        pass
