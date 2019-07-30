import time
from threading import Thread

import serial
import serial.tools.list_ports


class MicrosteppingMode:
    SINGLE = 1
    HALF = 2
    QUARTER = 4
    TINY = 16

    def __iter__(self):
        for key, value in self.__dict__.items():
            if not key.startswith('__') and not key.endswith('__'):
                yield value

    def __new__(cls, *, mode=0, index=None):
        if not isinstance(mode, int):
            raise TypeError(f'Invalid value: {mode}')
        found = False
        _i = 0
        for key, value in cls.__dict__.items():
            if not key.startswith('__') and not key.endswith('__'):
                if index is not None and index == _i:
                    return value
                if index is None and value == mode:
                    found = True
                    break
                _i += 1
        if not found:
            raise ValueError(f'Mode {mode} not found')
        return mode


class Motor(Thread):
    def __init__(self, device, microstepping_mode=MicrosteppingMode.SINGLE, speed=90, ratio=1.):
        Thread.__init__(self)
        self.daemon = True
        self._ser = serial.Serial()
        self._ser_device = device
        self._ser_banned = ()
        self._communicating = False
        self.MICROSTEPPING_MODE = MicrosteppingMode.SINGLE
        self.set_microstepping_mode(microstepping_mode)
        self.abort = False
        self._gear_ratio = ratio
        self._speed = self.degrees_to_steps(speed)

    def steps_to_degrees(self, steps):
        return float(steps) / 100. * 180. / self.MICROSTEPPING_MODE / self._gear_ratio

    def degrees_to_steps(self, degrees):
        v = float(degrees) * self.MICROSTEPPING_MODE * self._gear_ratio / 180. * 100.
        if v != 0. and int(v) == 0:
            print('Warning: To little angle to move: {angle}'.format(angle=degrees))
        return int(v)

    def set_microstepping_mode(self, new_mode):
        self.MICROSTEPPING_MODE = MicrosteppingMode(mode=new_mode)

    def time_to_turn(self, angle):
        if self._speed:
            return abs(self.degrees_to_steps(angle) / self._speed)
        else:
            return None

    def _open_serial(self):
        self._communicating = False
        ports = serial.tools.list_ports.comports()
        if set(port.device for port in ports) <= set(self._ser_banned):
            self._ser_banned = ()
        for port in ports:
            if (port.device == self._ser_device and (self._ser_device not in self._ser_banned)) or \
                    ((self._ser_device in self._ser_banned) and (port.device not in self._ser_banned)):
                self._ser.port = port.device
                self._ser.baudrate = 9600
                self._ser.parity = serial.PARITY_EVEN
                self._ser.bytesize = serial.EIGHTBITS
                self._ser.timeout = 1
                self._ser.write_timeout = 1
                try:
                    self._ser.open()
                except PermissionError:
                    print('Permission to open {} denied'.format(self._ser.port))
                    if self._ser.port not in self._ser_banned:
                        self._ser_banned += (self._ser.port,)
                    time.sleep(1)           # to be changed
                    pass
                else:
                    print(self._ser.port, "opened for the SMSD4.2RS-232")
                    self.disable()
                    self.speed(self.steps_to_degrees(self._speed))
                    self._communicating = False
                    break
        if not self._ser.is_open:
            time.sleep(1)

    def _block(self, timeout=3.):
        i = 0
        dt = 0.1
        while self._communicating:
            time.sleep(dt)
            i += 1
            if i > dt * timeout:
                return False
        return True

    @staticmethod
    def decode_response(resp):
        replies = {'E10': 'The command successfully accepted',
                   'E13': 'There is the error in the executing program',
                   'E14': 'Program executing completed',
                   'E15': 'Communication Error (check port parameters)',
                   'E16': 'Command error (check controller mode or ASCII code of the command)',
                   'E19': 'Command data error (check command data – integer, in allowed range)',
                   }
        if resp in replies:
            return replies[resp]
        else:
            return 'Unknown reply: {reply}'.format(reply=resp)

    def _do(self, cmd):
        if not self._block():
            print("driver is very busy to respond to", cmd)
            return False
        # print('command:', cmd)
        while self._ser.is_open:
            msg = cmd + '*'
            try:
                self._communicating = True
                self._ser.write(msg.encode('ascii'))
                self._ser.flush()
                c = self._ser.read(len(msg) + 4)
                while len(c) > 0 and c[0] == 0:
                    c = c[1:] + self._ser.read(1)
                self._ser.flush()
                self._communicating = False
            except (IOError, serial.SerialException, serial.SerialTimeoutException, UnicodeEncodeError):
                self._communicating = False
                continue
            if len(c) == 0:
                self._ser.close()
                print('restarting ' + self._ser.port)
                if self._ser.port not in self._ser_banned:
                    self._ser_banned += (self._ser.port,)
                self._open_serial()
                continue
            resp = c.decode("ascii").split('*')
            if resp[0] != cmd:
                print('wrong response:', msg, resp)
                continue
            # print(msg, self.decode_response(resp[1]))
            return resp[1]
        else:
            if self._ser.port not in self._ser_banned:
                self._ser_banned += (self._ser.port,)
            self._open_serial()
        return False

    def forward(self):
        return self._do('DL')

    def backward(self):
        return self._do('DR')

    def reverse(self):
        return self._do('RS')

    def move(self, angle=None):
        if angle is None:
            return self._do('MV')
        steps = self.degrees_to_steps(angle)
        if abs(steps) <= 10000000:
            if steps > 0:
                return self.forward() and self._do('MV{steps}'.format(steps=steps))
            elif steps < 0:
                return self.backward() and self._do('MV{steps}'.format(steps=-steps))
            else:
                return True
        else:
            raise ValueError('Too many steps: {steps}'.format(steps=steps))

    def stop(self):
        return self._do('ST1')
    
    def speed(self, speed=None):     # steps/sec
        if speed is None:
            return self.steps_to_degrees(self._speed)
        speed = self.degrees_to_steps(speed)
        if 0 < abs(speed) <= 10000:
            if speed > 0:
                if self.forward() and self._do('SD{speed}'.format(speed=speed)):
                    self._speed = speed
                    return True
            elif speed < 0:
                if self.backward() and self._do('SD{speed}'.format(speed=-speed)):
                    self._speed = -speed
                    return True
        elif speed == 0:
            raise ValueError('Too low speed: {speed}'.format(speed=speed))
        else:
            raise ValueError('Too much speed: {speed}'.format(speed=speed))
        return False

    def gear_ratio(self, ratio=None):
        if ratio is not None and ratio != 0:
            self._gear_ratio = ratio
        return self._gear_ratio

    def move_high(self):
        """ Indefinite movement, till signal to input IN2 """
        return self._do('MH')

    def move_low(self):
        """ Indefinite movement, till signal to input IN1 """
        return self._do('ML')

    def move_home(self):
        """ Indefinite movement, till signal to input “0” (zero limit switch) """
        return self._do('HM')

    def enable(self):
        return self._do('EN') or self._do('EN')

    def disable(self):
        r = self._do('DS')
        if r == 'E16':
            self.stop()
            r = False
        return r or self._do('DS')

    def wait_high(self):
        """ Indefinite pause, wait for a signal to input IN2 """
        return self._do('WH')
    
    def wait_low(self):
        """ Indefinite pause, wait for a signal to input IN1 """
        return self._do('WL')

    def follow_route_in_background(self, route, speed, delay):
        if not route:
            return False
        if len(route) == 1:
            self.move(route[0])
            return True
        for prev_angle, angle in zip(route[:-1], route[1:]):
            step = angle - prev_angle
            if step:
                self.move(self.degrees_to_steps(step))
                time.sleep(abs(step) / speed)
            if self.abort:
                self.abort = False
                break
            time.sleep(delay)
        return True

    def follow_route(self, route, speed, delay):
        Thread(target=lambda: self.follow_route_in_background(route, speed, delay)).start()

    def open(self, device=None):
        if isinstance(device, str):
            self._ser_device = device
        self._open_serial()
