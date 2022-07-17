# -*- coding: utf-8 -*-

from __future__ import annotations

import time
import typing
from ctypes import *
from ctypes.util import find_library
from typing import Iterable

from adc import ADC

__all__ = ['L791']
lib_l791: CDLL = CDLL(find_library('l791') or './lib''l791.so')


class _L791:
    class CL791(Structure):
        pass

    PCL791 = POINTER(CL791)

    class L791BoardDescription(Structure):
        _pack_ = 1
        _fields_ = [
            ('CRC16', c_ushort),
            ('SerNum', c_char * 16),
            ('BoardName', c_char * 16),
            ('Rev', c_char),
            ('DspType', c_char * 5),
            ('Quartz', c_uint),
            ('IsDACPresent', c_ushort),
            ('ADCFactor', c_float * 16),
            ('DACFactor', c_float * 4),
            ('Custom', c_ushort),
        ]

        def __repr__(self) -> str:
            return '\n'.join((
                'L791 Board Description:',
                f'CRC16               = {self.CRC16}',
                f'SerNum              = {self.SerNum}',
                f'BoardName           = {self.BoardName}',
                f'Rev                 = {self.Rev}',
                f'DspType             = {self.DspType}',
                f'Quartz              = {self.Quartz}',
                f'IsDACPresent        = {bool(self.IsDACPresent)}',
                f'ADCFactor           = {self.ADCFactor[:]}',
                f'DACFactor           = {self.DACFactor[:]}',
                f'Custom              = {self.Custom}',
            ))

    class DAQParameters(Structure):
        ADC_PARAM: c_uint = c_uint(1)
        DAC_PARAM: c_uint = c_uint(2)
        _pack_ = 1
        _fields_ = [
            ('s_Type', c_uint),
            ('FIFO', c_uint),
            ('IrqStep', c_uint),
            ('Pages', c_uint),
        ]

        def __repr__(self) -> str:
            return '\n'.join((
                'L791 DAQ Parameters:',
                f's_Type              = {self.s_Type}',
                f'FIFO                = {self.FIFO}',
                f'IrqStep             = {self.IrqStep}',
                f'Pages               = {self.Pages}',
            ))

    class ADCParameters(DAQParameters):
        _pack_ = 1
        _fields_ = [
            ('AutoInit', c_uint),

            ('dRate', c_double),
            ('dFrame', c_double),
            ('_', c_ushort),  # reserved
            ('DigRate', c_ushort),
            ('IsDataMarkerEnabled', c_uint),  # data marker ena/dis

            ('Rate', c_uint),
            ('Frame', c_uint),
            ('StartCnt', c_uint),  # delay data acquisition by this number of frames
            ('StopCnt', c_uint),  # stop data acquisition after this number of frames

            ('SyncType', c_uint),
            ('SyncMode', c_uint),  # advanced synchro mode + chan number
            ('SyncThreshold', c_uint),
            ('SyncSrc', c_uint),
            ('AdcIMask', c_uint),

            ('NumberOfChannels', c_uint),
            ('Chn', c_uint * 128),
            ('IrqEna', c_uint),
            ('AdcEna', c_uint),
        ]

        def __init__(self) -> None:
            super().__init__()
            self.s_Type = _L791.DAQParameters.ADC_PARAM

        def __repr__(self) -> str:
            return '\n'.join((
                'L791 ADC Parameters:',

                f's_Type              = {self.s_Type}',
                f'FIFO                = {self.FIFO}',
                f'IrqStep             = {self.IrqStep}',
                f'Pages               = {self.Pages}',

                f'AutoInit            = {bool(self.AutoInit)}',

                f'dRate               = {self.dRate}',
                f'dFrame              = {self.dFrame}',
                f'DigRate             = {self.DigRate}',
                f'IsDataMarkerEnabled = {bool(self.IsDataMarkerEnabled)}',

                f'Rate                = {self.Rate}',
                f'Frame               = {self.Frame}',
                f'StartCnt            = {self.StartCnt}',
                f'StopCnt             = {self.StopCnt}',

                f'SyncType            = {self.SyncType}',
                f'SyncMode            = {self.SyncMode}',
                f'SyncThreshold       = {self.SyncThreshold}',
                f'SyncSrc             = {self.SyncSrc}',
                f'AdcIMask            = {self.AdcIMask}',

                f'NumberOfChannels    = {self.NumberOfChannels}',
                f'Chn                 = {self.Chn[:self.NCh]}',
                f'IrqEna              = {self.IrqEna}',
                f'AdcEna              = {bool(self.AdcEna)}',
            ))

    class DACParameters(DAQParameters):
        _pack_ = 1
        _fields_ = [
            ('AutoInit', c_uint),

            ('dRate', c_double),
            ('Rate', c_uint),

            ('IrqEna', c_uint),
            ('AdcEna', c_uint),
            ('_', c_ushort),
        ]

        def __init__(self) -> None:
            super().__init__()
            self.s_Type = _L791.DAQParameters.DAC_PARAM

        def __repr__(self) -> str:
            return '\n'.join((
                'L791 ADC Parameters:',

                f's_Type        = {self.s_Type}',
                f'FIFO          = {self.FIFO}',
                f'IrqStep       = {self.IrqStep}',
                f'Pages         = {self.Pages}',

                f'AutoInit      = {bool(self.AutoInit)}',

                f'dRate         = {self.dRate}',
                f'Rate          = {self.Rate}',

                f'IrqEna        = {self.IrqEna}',
                f'AdcEna        = {bool(self.AdcEna)}',
            ))

    STREAM_ADC: int = 1
    STREAM_DAC: int = 2

    def __init__(self, slot: int = 0) -> None:
        create_instance = lib_l791.createInstance
        create_instance.restype = _L791.PCL791
        self._instance: _L791.PCL791 = create_instance(c_ulong(slot))
        if not self._instance:
            raise RuntimeError('Failed to connect to an L791 board')

    def __bool__(self) -> bool:
        return bool(self._instance)

    def open(self) -> int:
        return lib_l791.openBoard(self._instance)

    def close(self) -> int:
        return lib_l791.closeBoard(self._instance)

    def read_description(self) -> _L791.L791BoardDescription:
        pd: _L791.L791BoardDescription = _L791.L791BoardDescription()
        lib_l791.readBoardDescription(self._instance, byref(pd))
        return pd

    def request_stream_buffer(self, stream_id: int) -> int:
        return lib_l791.requestStreamBuffer(self._instance, stream_id)

    def fill_adc_parameters(self, ap: ADCParameters) -> int:
        return lib_l791.fillADCParameters(self._instance, byref(ap))

    def fill_dac_parameters(self, dp: DACParameters) -> int:
        return lib_l791.fillDACParameters(self._instance, byref(dp))

    def set_stream_parameters(self, sp: DAQParameters, stream_id: int) -> int:
        return lib_l791.setStreamParameters(self._instance, byref(sp), stream_id)

    def get_io_buffer_pointer(self, stream_id: int) -> POINTER(c_uint16):
        get_io_buffer = lib_l791.getIOBuffer
        get_io_buffer.restype = POINTER(c_uint16)
        return get_io_buffer(self._instance, stream_id)

    def get_io_buffer_size(self, stream_id: int) -> int:
        return lib_l791.getIOBufferSize(self._instance, stream_id)

    def get_io_buffer(self, stream_id: int) -> list[int]:
        return typing.cast(list, self.get_io_buffer_pointer(stream_id)[:self.get_io_buffer_size(stream_id)])

    def get_reg_buffer_pointer(self) -> POINTER(c_uint32):
        get_reg_buffer = lib_l791.getRegBuffer
        get_reg_buffer.restype = POINTER(c_uint32)
        return get_reg_buffer(self._instance)

    def get_reg_buffer_size(self) -> int:
        return lib_l791.getRegBufferSize(self._instance)

    def get_reg_buffer(self) -> list[int]:
        return typing.cast(list, self.get_reg_buffer_pointer()[:self.get_reg_buffer_size()])

    def init_start(self) -> int:
        return lib_l791.initStart(self._instance)

    def start(self) -> int:
        return lib_l791.start(self._instance)

    def stop(self) -> int:
        return lib_l791.stop(self._instance)


class L791(ADC):
    def __init__(self, channels: Iterable[int], *, timeout: float = 0.1):
        super().__init__(channels)
        self.timeout: float = timeout
        if max(self.channels) > 7:
            raise ValueError(f'There is no channel {max(self.channels)}')

        error: int
        self._board: _L791 = _L791()
        if not self._board:
            raise RuntimeError('Failed to initialize L791')

        self._board.open()
        print(self._board.read_description())
        error = self._board.request_stream_buffer(stream_id=_L791.STREAM_ADC)
        if error:
            raise RuntimeError(f'requestStreamBuffer failed with code {error}')

        self._adc_par: _L791.ADCParameters = _L791.ADCParameters()

        self._adc_par.AutoInit = True  # True == in loop
        self._adc_par.dRate = 200.0  # kHz
        self._adc_par.dFrame = .01

        self._adc_par.SyncType = 0
        self._adc_par.SyncSrc = 0

        self._adc_par.NumberOfChannels = 2 * len(self.channels)
        index: int
        for index in range(self._adc_par.NumberOfChannels):
            self._adc_par.Chn[index] = index

        self._adc_par.FIFO = 1024

        self._adc_par.IrqStep = 1024
        self._adc_par.Pages = 64
        self._adc_par.IrqEna = 3  # no interruptions
        self._adc_par.AdcEna = True

        error = self._board.fill_adc_parameters(self._adc_par)
        if error:
            raise RuntimeError(f'fillADCParameters failed with code {error}')
        # print(self._adc_par)
        error = self._board.set_stream_parameters(self._adc_par, stream_id=_L791.STREAM_ADC)
        if error:
            raise RuntimeError(f'setStreamParameters failed with code {error}')
        self._data_p = self._board.get_io_buffer_pointer(stream_id=_L791.STREAM_ADC)
        sync_p = self._board.get_reg_buffer_pointer()
        print(f'Current Firmware Version: {hex(typing.cast(int, sync_p[1021]))}')

        self._board.init_start()
        print('init device started')
        self._board.start()
        print('device started')

        self._buffer_size: int = self._board.get_io_buffer_size(stream_id=_L791.STREAM_ADC)

    def __del__(self) -> None:
        self._board.stop()
        print('device stopped')
        self._board.close()
        print('device closed')

    def run(self):
        self._is_running = True
        try:
            while self._is_running:
                for index, channel in enumerate(self.channels):
                    raw_data: list[int] \
                        = typing.cast(list, self._data_p[index * 2:self._buffer_size:self._adc_par.NumberOfChannels])
                    raw_data.sort()
                    count: int = len(raw_data)
                    s: float
                    if count & 1:
                        s = float(raw_data[count // 2])
                    else:
                        s = 0.5 * raw_data[count // 2] + 0.5 * raw_data[count // 2 - 1]
                    s *= 10. / (1 << 14)
                    self.voltages[index] = s
                time.sleep(self.timeout)
        except (KeyboardInterrupt, SystemExit):
            return
        finally:
            self._board.stop()
            print('device stopped')
            self._board.close()
            print('device closed')
