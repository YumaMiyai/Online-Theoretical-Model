import threading
from io import FileIO, TextIOBase, StringIO, SEEK_END
from threading import Thread
from time import sleep
from .instrument import Instrument


class JKemTemperature(Instrument):

    def __init__(self, path: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._path = path
        self._stream = open(self._path)
        self._line = 0
        self._close_requested = False
        self._header = self._stream.readlines()[0:4]
        self._value = None
        self._cb = None
        self._thread = Thread(target=self._process_data)
        self._thread.daemon = True
        self._thread.start()

    def __del__(self):
        if self._stream is not None:
            try:
                self._stream.close()
            except Exception as ex:
                print(f'{type(ex)} occurred while closing file: {ex}')
        try:
            self._thread.join(10.0)
        except:
            pass

    def close(self):
        self._close_requested = True

    def on_message(self, callback: callable):
        assert callable(callback)
        self._cb = callback

    def _process_data(self):
        for value in self._data:
            try:
                if self._close_requested:
                    return
                self._value = value
                if self._cb is not None:
                    self._cb(self._value)
                sleep(1.0)
            except Exception as ex:
                print(f'{type(ex)} occurred while processing flow rate data: {ex}')

    @property
    def value(self):
        return self._value

    @property
    def _data(self):
        self._stream.seek(0, SEEK_END)
        while not self._close_requested:
            try:
                data = self._stream.readline()
                data = data.split(',')
                temperature = float(data[1][:-1])
                yield temperature
            except IndexError:
                pass
            except Exception as ex:
                print(f'{type(ex)} occurred while reading file: {ex}')
