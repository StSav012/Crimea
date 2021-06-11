# -*- coding: utf-8 -*-

import time
from math import nan
from threading import Thread
from typing import Iterable, List


class ADC(Thread):
    def __init__(self, channels: Iterable[int]):
        super().__init__()
        self.daemon: bool = True
        self.channels: List[int] = list(channels)
        self.voltages: List[float] = [nan] * len(self.channels)
        self._is_running: bool = False

    def stop(self):
        self._is_running = False

    def run(self):
        self._is_running = True


class LCardADC(ADC):
    def __init__(self, channels: Iterable[int], *, timeout: float = 0.1, app: str = './ldevio'):
        super().__init__(channels)
        self.timeout: float = timeout
        self._channels_str: List[str] = [str(channel) for channel in self.channels]
        self._app: str = app
        if max(self.channels) > 7:
            raise ValueError(f'There is no channel {max(self.channels)}')
        self._is_running: bool = False

    def stop(self):
        self._is_running = False

    def run(self):
        self._is_running = True
        try:
            while self._is_running:
                self.voltages = [(0 if (time.perf_counter() % 10 < 3) else
                                  ((time.perf_counter() % 10 - 3) if (time.perf_counter() % 10 < 7) else 4))
                                 for _ in self.channels]
                # self.voltages = [random.gauss(0.15, 0.4) for _ in self.channels]
                time.sleep(self.timeout)
        except (KeyboardInterrupt, SystemExit):
            return
