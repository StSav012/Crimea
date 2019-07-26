import time
from threading import Thread


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
            raise TypeError('Invalid value: {}'.format(mode))
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
            raise ValueError('Mode {} not found'.format(mode))
        return mode


class Motor(Thread):
    def __init__(self, device, microstepping_mode=MicrosteppingMode.SINGLE, speed=90, ratio=1.):
        Thread.__init__(self)
        self.daemon = True
        self.MICROSTEPPING_MODE = MicrosteppingMode.SINGLE
        self.set_microstepping_mode(microstepping_mode)
        self.abort = False
        self._gear_ratio = ratio
        self._speed = self.degrees_to_steps(speed)
        del device

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

    @staticmethod
    def _do(cmd):
        # print('command:', cmd)
        del cmd
        return True

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

    def open(self):
        return
