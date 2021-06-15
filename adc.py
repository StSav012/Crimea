# -*- coding: utf-8 -*-

from math import nan
from threading import Thread
from typing import Iterable, List, TextIO


def _is_raspberrypi() -> bool:
    try:
        f_in: TextIO
        with open('/sys/firmware/devicetree/base/model', 'rt') as f_in:
            if 'raspberry pi' in f_in.read().casefold():
                return True
    finally:
        return False


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


if _is_raspberrypi():
    import ads1256

    ADCDevice = ads1256.ADS1256
else:
    try:
        import l783_dummy as l783
    except ImportError:
        import l783

    ADCDevice = l783.L783
