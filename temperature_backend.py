import io
import time
from threading import Thread
from typing import List, Union, Dict

import serial
import serial.tools.list_ports


class Dallas18B20(Thread):
    def __init__(self):
        super().__init__()
        self.daemon = True
        self._ser = serial.Serial()
        # noinspection PyTypeChecker
        self._sio = io.TextIOWrapper(io.BufferedRWPair(self._ser, self._ser, 1), newline='\n', write_through=True)
        self._communicating = False
        self._temperatures: List[float] = []
        self._setpoints: List[float] = []
        self._states: List[bool] = []
        self._new_setpoints: Dict[int, int] = dict()

    def _open_serial(self):
        self._communicating = False
        ports = serial.tools.list_ports.comports()
        for port in ports:
            if (port.pid == 0x7523 and port.vid == 0x1a86) \
                    or (port.pid == 0x0042 and port.vid == 0x2341):
                self._ser.port = port.device
                self._ser.baudrate = 9600
                self._ser.parity = serial.PARITY_NONE
                self._ser.bytesize = serial.EIGHTBITS
                self._ser.timeout = 3
                self._ser.write_timeout = 3
                try:
                    self._ser.open()
                except PermissionError:
                    print(f'Permission to open {self._ser.port} denied')
                else:
                    print(f'{self._ser.port} opened for the Arduino Mega 2560 R3 (CDC ACM)')
                    self._communicating = False
                    break
                finally:
                    time.sleep(1)  # to be changed
        if not self._ser.is_open:
            time.sleep(1)

    def _close_serial(self):
        self._ser.close()

    def _block(self, timeout: float = 10.) -> bool:
        i = 0
        dt = 0.1
        while self._communicating:
            time.sleep(dt)
            i += 1
            if i > timeout / dt:
                return False
        return True

    def read_text(self, cmd) -> Union[None, str]:
        if not self._block():
            print("Arduino is very busy to respond to", cmd)
            return None
#        print('command:', cmd)
        if not self._ser.is_open:
            self._open_serial()
        while self._ser.is_open:
            msg = cmd + '\n'
            try:
                self._communicating = True
                self._sio.write(msg)
#                print('written', msg.encode('ascii'))
                self._sio.flush()
#                print('reading...')
                try:
                    resp = self._sio.readline().strip()
                except UnicodeDecodeError:
                    resp = ''
                self._sio.flush()
                self._communicating = False
            except (serial.SerialException, TypeError):
                self._communicating = False
                continue
            if not resp:
                self._close_serial()
                print('restarting ' + self._ser.port)
                self._open_serial()
                continue
            print(cmd, resp.split(','))
            return resp
        return None

    def send(self, cmd) -> bool:
        if not self._block():
            print("Arduino is very busy to respond to", cmd)
            return False
        print('sending', cmd)
        if not self._ser.is_open:
            self._open_serial()
        while self._ser.is_open:
            msg = cmd + '\n'
            try:
                self._communicating = True
                self._sio.write(msg)
#                print('written', msg.encode('ascii'))
                self._sio.flush()
                self._communicating = False
            except serial.SerialException:
                self._communicating = False
                continue
            return True
        return False

    def _get_temperatures(self) -> List[float]:
        resp = self.read_text('R')
        if resp is not None:
            try:
                return list(map(float, resp.split(',')))
            except ValueError:
                return []
        return []

    def _get_states(self) -> List[bool]:
        resp = self.read_text('S')
        if resp is not None:
            try:
                return list(map(bool, map(int, resp.split(','))))
            except ValueError:
                return []
        return []

    def _get_setpoints(self) -> List[float]:
        resp = self.read_text('P')
        if resp is not None:
            try:
                return list(map(float, resp.split(',')))
            except ValueError:
                return []
        return []

    def set_setpoint(self, index: int, value: int):
        self._new_setpoints[index] = value

    @property
    def temperatures(self) -> List[float]:
        return self._temperatures

    @property
    def states(self) -> List[bool]:
        return self._states

    @property
    def setpoints(self) -> List[float]:
        return self._setpoints

    def run(self):
        try:
            while True:
                self._temperatures = self._get_temperatures()
                self._setpoints = self._get_setpoints()
                self._states = self._get_states()
                init_time: float = time.perf_counter()
                while self._new_setpoints:
                    for key, value in self._new_setpoints.copy().items():
                        if self._setpoints[key] != value:
                            if self.send(f'I{key}'):
                                time.sleep(1)
                                self.send(f'T{value}')
                                time.sleep(1)
                                self._setpoints = self._get_setpoints()
                        else:
                            del self._new_setpoints[key]
                spent_time: float = time.perf_counter() - init_time
                if spent_time < 10.:
                    time.sleep(10. - spent_time)
        except (SystemExit, KeyboardInterrupt):
            return
