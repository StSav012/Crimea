import time
from threading import Thread
from typing import List, Union, Dict

import serial
import serial.tools.list_ports


class Dallas18B20(Thread):
    D_MIN: int = 22
    D_MAX: int = 51

    def __init__(self):
        super().__init__()
        self.daemon = True
        self._ser = serial.Serial()
        # noinspection PyTypeChecker
        self._communicating = False
        self._temperatures: List[float] = []
        self._setpoints: List[float] = []
        self._states: List[bool] = []
        self._enabled: Union[None, bool] = None
        self._new_setpoints: Dict[int, int] = dict()
        self._new_digitals: Dict[int, bool] = dict()
        self._new_enabled: Union[None, bool] = None

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
                except serial.serialutil.SerialException as ex:
                    print(ex.strerror)
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
            if i * dt > timeout:
                return False
        return True

    def read_text(self, cmd: str, terminator: bytes = serial.serialutil.LF) -> Union[None, str]:
        if not self._block():
            print("Arduino is very busy to respond to", cmd)
            return None
        # print('command:', cmd)
        if not self._ser.is_open:
            self._open_serial()
        while self._ser.is_open:
            msg = cmd + '\n'
            try:
                self._communicating = True
                self._ser.write(msg.encode())
                # print('written', msg.encode('ascii'))
                self._ser.flush()
                # print('reading...')
                try:
                    resp = self._ser.read_until(terminator=terminator).decode().rstrip()
                except UnicodeDecodeError:
                    print('UnicodeDecodeError')
                    resp = ''
                self._ser.flush()
                self._communicating = False
            except (serial.SerialException, TypeError):
                self._communicating = False
                continue
            if not resp:
                self._close_serial()
                print('restarting', self._ser.port)
                self._open_serial()
                continue
            print(cmd, resp.split(','))
            return resp
        return None

    def send(self, cmd: str) -> bool:
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
                self._ser.write(msg.encode())
                # print('written', msg.encode('ascii'))
                self._ser.flush()
                self._communicating = False
            except serial.SerialException:
                self._communicating = False
                continue
            return True
        return False

    def voltage(self, pin: Union[int, str]) -> Union[None, int]:
        mega_pins: Dict[str, int] = {
            'A0': 54,
            'A1': 55,
            'A2': 56,
            'A3': 57,
            'A4': 58,
            'A5': 59,
            'A6': 60,
            'A7': 61,
            'A8': 62,
            'A9': 63,
            'A10': 64,
            'A11': 65,
            'A12': 66,
            'A13': 67,
            'A14': 68,
            'A15': 69,
        }
        if isinstance(pin, str):
            pin = mega_pins[pin]
        try:
            return int(self.read_text(f'V{pin}', terminator=b'\n\r'))  # arduino firmware bug
        except ValueError:
            return None

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

    def _get_enabled(self) -> Union[None, bool]:
        resp = self.read_text('Q')
        if resp is not None:
            try:
                return bool(int(resp))
            except ValueError:
                return None
        return None

    def set_setpoint(self, index: int, value: int):
        self._new_setpoints[index] = value

    def set_digital(self, index: int, value: bool):
        self._new_digitals[index] = value

    def enable(self):
        self._new_enabled = True

    def disable(self):
        self._new_enabled = False

    @property
    def temperatures(self) -> List[float]:
        return self._temperatures

    @property
    def states(self) -> List[bool]:
        return self._states

    @property
    def setpoints(self) -> List[float]:
        return self._setpoints

    @property
    def enabled(self) -> Union[None, bool]:
        return self._enabled

    def run(self):
        try:
            while True:
                init_time: float = time.perf_counter()
                self._temperatures = self._get_temperatures()
                self._setpoints = self._get_setpoints()
                self._states = self._get_states()
                self._enabled = self._get_enabled()
                while self._new_setpoints:
                    for key, value in self._new_setpoints.copy().items():
                        if self._setpoints[key] != value:
                            if self.send(f'I{key}'):
                                # time.sleep(1)
                                self.send(f'T{value}')
                                # time.sleep(1)
                                self._setpoints = self._get_setpoints()
                        else:
                            del self._new_setpoints[key]
                while self._new_digitals:
                    for key, value in self._new_digitals.copy().items():
                        if self.send(f'H{key}' if value else f'L{key}'):
                            del self._new_digitals[key]
                while self._new_enabled is not None and self._enabled is not self._new_enabled:
                    if self._new_enabled is True:
                        self.send('E')
                    elif self._new_enabled is False:
                        self.send('D')
                    self._enabled = self._get_enabled()
                spent_time: float = time.perf_counter() - init_time
                # print(spent_time)
                if spent_time < 10.:
                    time.sleep(10. - spent_time)
        except (SystemExit, KeyboardInterrupt):
            return
