# -*- coding: utf-8 -*-

import time
from enum import IntEnum
from typing import Dict, Final, Iterable, List, Literal, Union

from spidev import SpiDev
# noinspection PyUnresolvedReferences
from RPi import GPIO

from adc import ADC

__all__ = ['ADS1256']

# Pin definition. Hardware defined. Do not change.
RST_PIN: Final[int] = 18
CS_PIN: Final[int] = 22
CS_DAC_PIN: Final[int] = 23
DATA_READY_PIN: Final[int] = 17

# SPI device, bus = 0, device = 0. Hardware defined. Do not change.
SPI: SpiDev = SpiDev(0, 0)


class ADS1256(ADC):
    # gain channel
    GAIN: Dict[int, int] = {
        1: 0,  # GAIN   1
        2: 1,  # GAIN   2
        4: 2,  # GAIN   4
        8: 3,  # GAIN   8
        16: 4,  # GAIN  16
        32: 5,  # GAIN  32
        64: 6,  # GAIN  64
    }

    # data rate
    DATA_RATE: Dict[Union[int, float], int] = {
        30000: 0xF0,  # reset the default values
        15000: 0xE0,
        7500: 0xD0,
        3750: 0xC0,
        2000: 0xB0,
        1000: 0xA1,
        500: 0x92,
        100: 0x82,
        60: 0x72,
        50: 0x63,
        30: 0x53,
        25: 0x43,
        15: 0x33,
        10: 0x20,
        5: 0x13,
        2.5: 0x03
    }

    # registration definition
    class REG(IntEnum):
        STATUS = 0  # x1H
        MUX = 1  # 01H
        AD_CON = 2  # 20H
        DATA_RATE = 3  # F0H
        IO = 4  # E0H
        OFC0 = 5  # xxH
        OFC1 = 6  # xxH
        OFC2 = 7  # xxH
        FSC0 = 8  # xxH
        FSC1 = 9  # xxH
        FSC2 = 10  # xxH

    # command definition
    class CMD(IntEnum):
        WAKEUP = 0x00  # Completes SYNC and Exits Standby mode 0000  0000 (00h)
        READ_DATA = 0x01  # Read Data 0000  0001 (01h)
        READ_DATA_CONTINUOUSLY = 0x03  # Read Data Continuously 0000   0011 (03h)
        STOP_READING_DATA_CONTINUOUSLY = 0x0F  # Stop Read Data Continuously 0000   1111 (0Fh)
        READ_REG = 0x10  # Read from REG rrr 0001 rrrr (1xh)
        WRITE_REG = 0x50  # Write to REG rrr 0101 rrrr (5xh)
        SELF_CALIBRATION = 0xF0  # Offset and Gain Self-Calibration 1111    0000 (F0h)
        SELF_OFFSET_CALIBRATION = 0xF1  # Offset Self-Calibration 1111    0001 (F1h)
        SELF_GAIN_CALIBRATION = 0xF2  # Gain Self-Calibration 1111    0010 (F2h)
        SYSTEM_OFFSET_CALIBRATION = 0xF3  # System Offset Calibration 1111   0011 (F3h)
        SYSTEM_GAIN_CALIBRATION = 0xF4  # System Gain Calibration 1111    0100 (F4h)
        SYNC = 0xFC  # Synchronize the A/D Conversion 1111   1100 (FCh)
        STANDBY = 0xFD  # Begin Standby mode 1111   1101 (FDh)
        RESET = 0xFE  # Reset to Power-Up Values 1111   1110 (FEh)

    class Mode(IntEnum):
        SINGLE = 0
        DIFFERENTIAL = 1

    def __init__(self, channels: Iterable[int], *, timeout: float = 0.1) -> None:
        super().__init__(channels)
        self.timeout: float = timeout

        self.rst_pin: Final[int] = RST_PIN
        self.cs_pin: Final[int] = CS_PIN
        self.cs_dac_pin: Final[int] = CS_DAC_PIN
        self.data_ready_pin: Final[int] = DATA_READY_PIN
        self.scan_mode: ADS1256.Mode = self.Mode.DIFFERENTIAL

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.rst_pin, GPIO.OUT)
        GPIO.setup(self.cs_dac_pin, GPIO.OUT)
        GPIO.setup(self.cs_pin, GPIO.OUT)
        # GPIO.setup(self.data_ready_pin, GPIO.IN)
        GPIO.setup(self.data_ready_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        SPI.max_speed_hz = 20000
        SPI.mode = 0b01

        self.reset()
        chip_id = self.read_chip_id()
        if chip_id == 3:
            print("ID Read succeeded")
        else:
            raise RuntimeError("ID Read failed")
        self.config_adc(self.GAIN[1], self.DATA_RATE[30000])

    def __del__(self) -> None:
        GPIO.cleanup()

    # Hardware reset
    def reset(self) -> None:
        GPIO.output(self.rst_pin, GPIO.HIGH)
        time.sleep(0.2)
        GPIO.output(self.rst_pin, GPIO.LOW)
        time.sleep(0.2)
        GPIO.output(self.rst_pin, GPIO.HIGH)

    def _write_cmd(self, cmd: CMD) -> None:
        GPIO.output(self.cs_pin, GPIO.LOW)  # cs  0
        SPI.writebytes([cmd])
        GPIO.output(self.cs_pin, GPIO.HIGH)  # cs 1

    def write_reg(self, reg: REG, data) -> None:
        GPIO.output(self.cs_pin, GPIO.LOW)  # cs  0
        SPI.writebytes([self.CMD.WRITE_REG | reg, 0x00, data])
        GPIO.output(self.cs_pin, GPIO.HIGH)  # cs 1

    def read_data(self, reg: REG) -> bytes:
        GPIO.output(self.cs_pin, GPIO.LOW)  # cs  0
        SPI.writebytes([self.CMD.READ_REG | reg, 0x00])
        data = SPI.readbytes(1)
        GPIO.output(self.cs_pin, GPIO.HIGH)  # cs 1
        return data

    def _wait_for_data(self) -> None:
        for i in range(0, 400):
            if GPIO.input(self.data_ready_pin) == 0:
                break
            else:
                time.sleep(0.01)
        else:
            raise TimeoutError

    def read_chip_id(self) -> int:
        self._wait_for_data()
        chip_id = self.read_data(self.REG.STATUS)
        chip_id = chip_id[0] >> 4
        # print('ID:', chip_id)
        return chip_id

    # The configuration parameters of adc, gain and data rate
    def config_adc(self, gain: int, data_rate: int):
        self._wait_for_data()
        buf: List[int] = [0, 0, 0, 0, 0, 0, 0, 0]
        buf[0] = (0 << 3) | (1 << 2) | (0 << 1)
        buf[1] = 0x08
        buf[2] = (0 << 5) | (0 << 3) | (gain << 0)
        buf[3] = data_rate

        GPIO.output(self.cs_pin, GPIO.LOW)  # cs  0
        SPI.writebytes([self.CMD.WRITE_REG, 0x03])
        SPI.writebytes(buf)

        GPIO.output(self.cs_pin, GPIO.HIGH)  # cs 1
        time.sleep(0.001)

    def _set_channel(self, channel: Literal[0, 1, 2, 3, 4, 5, 6, 7]) -> None:
        if channel not in [0, 1, 2, 3, 4, 5, 6, 7]:
            raise ValueError(f'Invalid channel: {channel}')
        self.write_reg(self.REG.MUX, (channel << 4) | (1 << 3))

    def _set_diff_channel(self, channel: Literal[0, 1, 2, 3]) -> None:
        if channel not in [0, 1, 2, 3]:
            raise ValueError(f'Invalid channel: {channel}')
        self.write_reg(self.REG.MUX, ((channel * 2) << 4) | (channel * 2 + 1))
        # print(f'DiffChannel   AIN{channel * 2}-AIN{channel * 2 + 1}')

    def set_mode(self, mode: Mode) -> None:
        self.scan_mode = mode

    def read_adc_data(self) -> float:
        self._wait_for_data()
        GPIO.output(self.cs_pin, GPIO.LOW)  # cs  0
        SPI.writebytes([self.CMD.READ_DATA])
        # time.sleep(0.01)

        buf: bytes = SPI.readbytes(3)
        GPIO.output(self.cs_pin, GPIO.HIGH)  # cs 1
        read: int = (buf[0] << 16) & 0xff0000
        read |= (buf[1] << 8) & 0xff00
        read |= (buf[2]) & 0xff
        if read & 0x800000:
            read &= 0xf000000
        return read * 5.0 / 0x7fffff

    def get_channel_value(self, channel: Literal[0, 1, 2, 3, 4, 5, 6, 7]) -> float:
        value: float
        if self.scan_mode == ADS1256.Mode.SINGLE:  # Single-ended input with 8 channels
            if channel >= 8:
                raise ValueError(f'Invalid channel: {channel}')
            self._set_channel(channel)
            self._write_cmd(self.CMD.SYNC)
            # time.sleep(0.01)
            self._write_cmd(self.CMD.WAKEUP)
            # time.sleep(0.2)
            value = self.read_adc_data()
        elif self.scan_mode == ADS1256.Mode.DIFFERENTIAL:  # Differential input with 4 channels
            if channel >= 4:
                raise ValueError(f'Invalid channel: {channel}')
            self._set_diff_channel(channel)
            self._write_cmd(self.CMD.SYNC)
            # time.sleep(0.01)
            self._write_cmd(self.CMD.WAKEUP)
            # time.sleep(0.01)
            value = self.read_adc_data()
        else:
            raise ValueError(f'Invalid mode: {self.scan_mode}')
        return value

    def run(self):
        self._is_running = True
        try:
            while self._is_running:
                index: int
                channel: Literal[0, 1, 2, 3, 4, 5, 6, 7]
                for index, channel in enumerate(self.channels):
                    self.voltages[index] = self.get_channel_value(channel)
                time.sleep(self.timeout)
        except (KeyboardInterrupt, SystemExit):
            return
