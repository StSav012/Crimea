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
        self.channels: List[int] = list(sorted(channels))
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
        import ldev_dummy

        ADCDevice = ldev_dummy.LDevDummy
    except ImportError:
        from subprocess import Popen, PIPE

        proc: Popen
        with Popen(('ls''pci', '-n',), shell=True, stdout=PIPE) as proc:
            proc_out: bytes = proc.stdout.read()

        if b'10b5:9050' in proc_out and b'1172:0791' not in proc_out:
            import l780

            ADCDevice = l780.L780
        elif b'10b5:9050' not in proc_out and b'1172:0791' in proc_out:
            import l791

            ADCDevice = l791.L791
        elif b'10b5:9050' in proc_out and b'1172:0791' in proc_out:
            raise SystemError('Can not determine ADC device conclusively')
        else:
            raise SystemError('No ADC device found')
