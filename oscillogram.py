#!/usr/bin/python3
# -*- coding: utf-8 -*-
import time
from typing import List

try:
    import radiometer_dummy as radiometer
except ImportError:
    import radiometer

ADC_CHANNELS: List[int] = [0]
EPS: float = 0.01
N_BEFORE: int = 10000
N_AFTER: int = 10000

adc = radiometer.L791(channels=ADC_CHANNELS, timeout=0.01)
adc.start()

data: List[List[float]] = [[]] * len(ADC_CHANNELS)

signal_registered: bool = False
wait_for_signal: bool = True

while wait_for_signal:
    for channel, voltage in enumerate(adc.voltages):
        if not signal_registered and len(data[channel]) > N_BEFORE:
            data[channel].pop(0)
        if len(data[channel]) < N_BEFORE + N_AFTER:
            data[channel].append(voltage)
        if not signal_registered and abs(data[channel][-1] - data[channel][0]) > EPS:
            signal_registered = True
        elif signal_registered and all(abs(data[ch][-1] - data[ch][-2]) < EPS for ch in range(len(data))):
            wait_for_signal = False

    time.sleep(2. * adc.timeout)

with open('log.csv', 'w') as f_out:
    f_out.write('\n'.join(','.join(repr(data[ch][i]) for ch in range(len(data))) for i in range(len(data[0]))))
