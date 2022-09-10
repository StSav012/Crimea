import time
from threading import Thread
from typing import Dict, List, Optional, Union

import serial
import serial.tools.list_ports


class Dallas18B20(Thread):
    D_MIN: int = 22
    D_MAX: int = 51

    def __init__(self) -> None:
        super().__init__()
        self.daemon = True
        self._ser = serial.Serial()
        self._communicating: bool = False
        self._temperatures: List[float] = []
        self._setpoints: List[int] = []
        self._states: List[bool] = []
        self._enabled: Optional[bool] = None
        self._new_setpoints: Dict[int, int] = dict()
        self._new_digitals: Dict[int, bool] = dict()
        self._new_enabled: Optional[bool] = None
        self._running: bool = False

    def _open_serial(self) -> None:
        self._communicating = False
        ports = serial.tools.list_ports.comports()
        for port in ports:
            if (port.pid == 0x7523 and port.vid == 0x1a86) \
                    or (port.pid == 0x0042 and port.vid == 0x2341):
                try:
                    self._ser.port = port.device
                except TypeError:
                    print(f'Incorrect device: {port}')
                    time.sleep(1)
                    continue
                self._ser.baudrate = 9600
                self._ser.parity = serial.PARITY_NONE
                self._ser.bytesize = serial.EIGHTBITS
                self._ser.timeout = 3
                self._ser.write_timeout = 3
                try:
                    self._ser.open()
                except PermissionError:
                    print(f'Permission to open {self._ser.port} denied')
                except TypeError:
                    print(f'Incorrect device: {port}')
                except serial.serialutil.SerialException as ex:
                    print('SerialException:', ex.strerror)
                else:
                    print(f'{self._ser.port} opened for the Arduino Mega 2560 R3 (CDC ACM)')
                    self._communicating = False
                    break
                finally:
                    time.sleep(1)  # to be changed

    def _close_serial(self) -> None:
        self._ser.cancel_read()
        self._ser.cancel_write()
        self._ser.close()

    def _block(self, timeout: float = 12.) -> bool:
        i: int = 0
        dt: float = 0.1
        while self._communicating:
            time.sleep(dt)
            i += 1
            if i * dt > timeout:
                return False
        return True

    def read_text(self, cmd: str, terminator: bytes = serial.serialutil.LF) -> str:
        if not self._block():
            print("Arduino is very busy to respond to", cmd)
            return ''
        # print('command:', cmd)
        if not self._ser.is_open:
            self._open_serial()
        resp: str = ''
        try:
            if self._ser.is_open:
                msg: str = cmd + '\n'
                self._communicating = True
                self._ser.write(msg.encode())
                # print('written', msg.encode('ascii'))
                self._ser.flush()
                # print('reading...')
                resp_bytes: bytes = self._ser.read_until(terminator)
                try:
                    resp = resp_bytes.decode().rstrip()
                except UnicodeDecodeError:
                    print(f'UnicodeDecodeError while reading response {resp_bytes} to {cmd}')
                    resp = ''
                self._ser.flush()
                self._communicating = False
                if not resp:
                    self._close_serial()
                    print('restarting', self._ser.port)
                # print(cmd, resp.split(','))
                return resp
        finally:
            self._communicating = False
            return resp

    def send(self, cmd: str) -> bool:
        if not self._block():
            print("Arduino is very busy to respond to", cmd)
            return False
        # print('sending', cmd)
        if not self._ser.is_open:
            self._open_serial()
        while self._ser.is_open:
            msg: str = cmd + '\n'
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

    def voltage(self, pin: Union[int, str]) -> Optional[int]:
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
        v: Optional[int] = None
        try:
            if isinstance(pin, str):
                pin = mega_pins[pin]
            v = int(self.read_text(f'V{pin}', terminator=b'\n\r'))  # arduino firmware bug
        finally:
            return v

    def _get_temperatures(self) -> List[float]:
        resp: str = self.read_text('R')
        if resp:
            try:
                return list(map(float, resp.split(',')))
            except ValueError:
                return []
        return []

    def _get_states(self) -> List[bool]:
        resp: str = self.read_text('S')
        if resp:
            try:
                return list(map(bool, map(int, resp.split(','))))
            except ValueError:
                return []
        return []

    def _get_setpoints(self) -> List[int]:
        resp: str = self.read_text('P')
        if resp:
            try:
                return list(map(int, resp.split(',')))
            except ValueError:
                return []
        return []

    def _get_enabled(self) -> Optional[bool]:
        resp: str = self.read_text('Q')
        if resp:
            try:
                return bool(int(resp))
            except ValueError:
                return None
        return None

    def set_setpoint(self, index: int, value: int) -> None:
        self._new_setpoints[index] = value

    def set_digital(self, index: int, value: bool) -> None:
        self._new_digitals[index] = value

    def enable(self) -> None:
        self._new_enabled = True

    def disable(self) -> None:
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
    def enabled(self) -> Optional[bool]:
        return self._enabled

    def stop(self) -> None:
        self._running = False

    def run(self) -> None:
        try:
            self._running = True
            while self._running:
                try:
                    self._temperatures = self._get_temperatures()
                    time.sleep(1.0)
                    self._setpoints = self._get_setpoints()
                    time.sleep(1.0)
                    self._states = self._get_states()
                    time.sleep(1.0)
                    self._enabled = self._get_enabled()
                    time.sleep(1.0)
                    while self._running and self._new_setpoints:
                        for key, value in self._new_setpoints.copy().items():
                            if key not in self._setpoints or self._setpoints[key] != value:
                                if self.send(f'I{key}'):
                                    # time.sleep(1)
                                    self.send(f'T{value}')
                                    # time.sleep(1)
                                    self._setpoints = self._get_setpoints()
                                    time.sleep(1.0)
                            else:
                                del self._new_setpoints[key]
                    while self._running and self._new_digitals:
                        for key, value in self._new_digitals.copy().items():
                            if self.send(f'H{key}' if value else f'L{key}'):
                                del self._new_digitals[key]
                        time.sleep(1.0)
                    while self._running and self._new_enabled is not None and self._enabled is not self._new_enabled:
                        if self._new_enabled is True:
                            self.send('E')
                        elif self._new_enabled is False:
                            self.send('D')
                        self._enabled = self._get_enabled()
                        time.sleep(1.0)
                except (SystemExit, KeyboardInterrupt):
                    return
        except (SystemExit, KeyboardInterrupt):
            return
