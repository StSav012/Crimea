# -*- coding: utf-8 -*-

import time
from typing import Any, Iterable, List

from adc import ADC


__all__ = ['LDevDummy']


class LDevDummy(ADC):
    def __init__(self, channels: Iterable[int], *, timeout: float = 0.1, **kwargs: Any):
        super().__init__(channels)
        self.timeout: float = timeout
        self._channels_str: List[str] = [str(channel) for channel in self.channels]
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
