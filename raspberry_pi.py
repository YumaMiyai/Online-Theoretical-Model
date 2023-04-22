# -*- coding: utf-8 -*-
"""
Created on Fri Oct 29 15:41:17 2021

@author: Mettler
"""

import socket, sys, json, threading, queue
from time import sleep


class Server:
    _host: str
    _port: int
    _socket: socket.socket

    def __init__(self, host: str, port: int):
        self._host = host
        self._port = port
        ## UDP
        # self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        ## TCP
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.settimeout(10.0)
        try:
            self._socket.connect((self._host, self._port))
            print(f'Connected')
        except socket.timeout:
            print(f'Could not connect to the Raspberry Pi')
            raise BrokenPipeError(f'No Raspberry Pi found')
            
        self._disconnect = False
        self._data = {}
        self._queue = queue.Queue(10)
        self._thread = threading.Thread(target=self._send_data)
        self._thread.daemon = True
        self._thread.start()

    def _send_data(self):
        print(f'Thread starting')
        while not self._disconnect:
            try:
                #key, value = self._queue.get(timeout=1.0)
                #self._data[key] = value
                #data = json.dumps({'pump1': 10.0, 'pump2': 7.0}).encode('utf-8')
                data = json.dumps(self._data).encode('utf-8')
                print(f'Sending data: {data}')
                self._socket.send(data)
                sleep(1.0)
            except queue.Empty:
                print(f'Queue empty')
                sleep(5.0)
            except socket.timeout:
                print(f'Socket timed out. Closing socket')
                self._disconnect = True
            except Exception as ex:
                print(f'{type(ex)} exception occurred: {ex}')
        print(f'Thread stopping')
            
    def set_value(self, item: str, value):
        #self._queue.put((item, value), block=False, timeout=5.0)
        self._data[item] = value

    def __del__(self):
        self._disconnect = True
        self._thread.join(10.0)
        self._socket.close()
