# -*- coding: utf-8 -*-

import time
from datetime import datetime
from threading import Thread
from typing import Any, Callable, Iterable, List, Optional, Tuple

import numpy as np

import adc


class ADCAcquisition(Thread):
    def __init__(self, adc_channels: Iterable[int], measurement_completed_callback: Callable[[], None]) -> None:
        super().__init__()
        self.daemon = True

        self._is_running: bool = False
        self._closing: bool = False
        self.targets: List[Tuple[Callable, Tuple[Any, ...]]] = []

        self._adc: adc.ADC = adc.ADCDevice(channels=adc_channels, timeout=0.1)
        self._adc.start()

        self._start_time: Optional[float] = None
        self._stop_time: Optional[float] = None

        self.current_x: datetime = datetime.now()
        self.current_y: List[np.ndarray] = [np.empty(0)] * len(self._adc.channels)

        self.measurement_completed_callback: Callable[[], None] = measurement_completed_callback

    def close(self) -> None:
        self._adc.stop()
        self._adc.join()
        self._is_running = False
        self._closing = True

    def set_running(self, is_running: bool) -> None:
        self._is_running = bool(is_running)

    def set_channels(self, new_channels: Iterable[int]) -> None:
        self._is_running = False
        self._adc.stop()
        self._adc.join()
        self._adc = adc.ADCDevice(channels=new_channels, timeout=0.1)
        self.current_y = [np.empty(0)] * len(self._adc.channels)
        self._adc.start()

    def done(self) -> bool:
        return not self.targets

    def measure(self, delay, duration) -> None:
        self._start_time = time.perf_counter() + delay
        self._stop_time = self._start_time + duration
        self.current_x = datetime.now()
        self.set_running(True)

    def run(self) -> None:
        try:
            while not self._closing:
                if self._is_running and self._stop_time is not None:
                    while self._is_running and time.perf_counter() <= self._stop_time and not self._closing:
                        if time.perf_counter() >= self._start_time:
                            for ch in self._adc.channels:
                                v = self._adc.voltages[ch]
                                if v is not None:
                                    self.current_y[ch] = np.concatenate((self.current_y[ch], np.array([v])))
                        if self._is_running and time.perf_counter() <= self._stop_time and not self._closing:
                            time.sleep(0.1)
                        elif self._is_running and time.perf_counter() <= self._start_time and not self._closing:
                            time.sleep(0.01)
                    else:
                        self.measurement_completed_callback()
                elif not self._closing:
                    if self.targets:
                        _target, _args = self.targets[0]
                        _target(*_args)
                        self.targets.pop(0)
                    else:
                        time.sleep(0.1)
        except (KeyboardInterrupt, SystemExit):
            return
