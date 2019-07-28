import time
from threading import Thread
import random


class ADC(Thread):
    def __init__(self, channels, *, timeout=0.1, app='./ldevio'):
        Thread.__init__(self)
        self.daemon = True
        self.timeout = timeout
        self._channels = channels[:]
        self._channels_str = [str(channel) for channel in self._channels]
        self.voltages = [None] * len(self._channels)
        if max(self._channels) > 7:
            raise ValueError('There is no channel {}'.format(max(self._channels)))
        self._is_running = False
        # print('adc is running in', os.path.abspath(os.path.curdir))
        del app

    def stop(self):
        self._is_running = False

    def run(self):
        self._is_running = True
        try:
            while self._is_running:
                self.voltages = [random.gauss(0.15, 0.4) for _ in self._channels]
                time.sleep(self.timeout)
        except (KeyboardInterrupt, SystemExit):
            return
