# -*- coding: utf-8 -*-

import os.path
import time
from math import nan
from subprocess import PIPE, Popen
from typing import Iterable, List

from adc import ADC


__all__ = ['L783']


class L783(ADC):
    def __init__(self, channels: Iterable[int], *, timeout: float = 0.1, app: str = './ldevio'):
        super().__init__(channels)
        self.timeout: float = timeout
        self._channels_str: List[str] = [str(channel) for channel in self.channels]
        self._app: str = app
        if max(self.channels) > 7:
            raise ValueError(f'There is no channel {max(self.channels)}')
        self._p = Popen([app, str(max(self.channels) + 1)], stdin=PIPE, stdout=PIPE,
                        cwd=os.path.dirname(os.path.realpath(__file__)))

    def run(self):
        self._is_running = True
        try:
            while self._is_running:
                while self._is_running and self._p.poll() is None:
                    for index, channel in enumerate(self._channels_str):
                        self._p.stdin.write((channel + '\n').encode('ascii'))
                        self._p.stdin.flush()
                        r = self._p.stdout.readline().strip().decode('ascii').split(maxsplit=1)
                        if r and r[0] == channel:
                            self.voltages[index] = float(r[1])
                        else:
                            self.voltages[index] = nan
                    time.sleep(self.timeout)
                if self._is_running:
                    self._p = Popen([self._app, str(max(self.channels) + 1)], stdin=PIPE, stdout=PIPE)
            else:
                self._p.communicate(input=b'-1', timeout=3)
        except (KeyboardInterrupt, SystemExit):
            self._p.communicate(input=b'-1', timeout=3)
            return
