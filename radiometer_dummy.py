# import random
import time
from math import nan
from threading import Thread
from typing import List


class ADC(Thread):
    def __init__(self, channels: List[int], *, timeout: float = 0.1, app: str = './ldevio'):
        Thread.__init__(self)
        self.daemon: bool = True
        self.timeout: float = timeout
        self._channels: List[int] = channels[:]
        self._channels_str: List[str] = [str(channel) for channel in self._channels]
        self.voltages: List[float] = [nan] * len(self._channels)
        if max(self._channels) > 7:
            raise ValueError(f'There is no channel {max(self._channels)}')
        self._is_running: bool = False
        # print('adc is running in', os.path.abspath(os.path.curdir))
        del app

    def stop(self):
        self._is_running = False

    def run(self):
        self._is_running = True
        try:
            while self._is_running:
                self.voltages = [(0 if (time.perf_counter() % 10 < 3) else
                                  ((time.perf_counter() % 10 - 3) if (time.perf_counter() % 10 < 7) else 4))
                                 for _ in self._channels]
                # self.voltages = [random.gauss(0.15, 0.4) for _ in self._channels]
                time.sleep(self.timeout)
        except (KeyboardInterrupt, SystemExit):
            return
