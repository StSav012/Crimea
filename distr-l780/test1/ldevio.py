# coding: utf-8
from __future__ import annotations

import typing
from ctypes import *
from ctypes.util import find_library
from pathlib import Path

lib_l780: CDLL = CDLL(find_library('l780') or './lib''l780.so')


class CL780(Structure):
    pass


PCL780 = POINTER(CL780)


class L780BoardDescription(Structure):
    _pack_ = 1
    _fields_ = [
        ('SerNum', c_char * 9),
        ('BoardName', c_char * 5),
        ('Rev', c_char),
        ('DspType', c_char * 5),
        ('Quartz', c_uint),
        ('IsDACPresent', c_ushort),
        ('_', c_ushort * 7),  # reserved
        ('ADCFactor', c_float * 8),
        ('DACFactor', c_float * 4),
        ('Custom', c_ushort * 32),
    ]

    def __repr__(self) -> str:
        return '\n'.join((
            'L780 Board Description:',
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
            'L780 DAQ Parameters:',
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
        ('dScale', c_double),
        ('Rate', c_uint),
        ('Frame', c_uint),
        ('Scale', c_uint),
        ('FPDelay', c_uint),

        ('SyncType', c_uint),
        ('SyncSensitivity', c_uint),  # advanced synchro mode + chan number
        ('SyncMode', c_uint),  # advanced synchro mode + chan number
        ('SyncChannel', c_uint),
        ('SyncThreshold', c_uint),

        ('NumberOfChannels', c_uint),
        ('Chn', c_uint * 128),
        ('IrqEna', c_uint),
        ('AdcEna', c_uint),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.s_Type = DAQParameters.ADC_PARAM

    def __repr__(self) -> str:
        return '\n'.join((
            'L780 ADC Parameters:',

            f's_Type              = {self.s_Type}',
            f'FIFO                = {self.FIFO}',
            f'IrqStep             = {self.IrqStep}',
            f'Pages               = {self.Pages}',

            f'AutoInit            = {bool(self.AutoInit)}',

            f'dRate               = {self.dRate}',
            f'dFrame              = {self.dFrame}',
            f'dScale              = {self.dScale}',
            f'Rate                = {self.Rate}',
            f'Frame               = {self.Frame}',
            f'Scale               = {self.Scale}',
            f'FPDelay             = {self.FPDelay}',

            f'SyncType            = {self.SyncType}',
            f'SyncSensitivity     = {self.SyncSensitivity}',
            f'SyncMode            = {self.SyncMode}',
            f'SyncChannel         = {self.SyncChannel}',
            f'SyncThreshold       = {self.SyncThreshold}',

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
        ('DacEna', c_uint),
        ('DacNumber', c_uint),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.s_Type = DAQParameters.DAC_PARAM

    def __repr__(self) -> str:
        return '\n'.join((
            'L780 ADC Parameters:',

            f's_Type        = {self.s_Type}',
            f'FIFO          = {self.FIFO}',
            f'IrqStep       = {self.IrqStep}',
            f'Pages         = {self.Pages}',

            f'AutoInit      = {bool(self.AutoInit)}',

            f'dRate         = {self.dRate}',
            f'Rate          = {self.Rate}',

            f'IrqEna        = {self.IrqEna}',
            f'DacEna        = {bool(self.DacEna)}',
            f'DacNumber     = {self.DacNumber}',
        ))


class SlotParameters(Structure):
    _pack_ = 1
    _fields_ = [
        ('Base', c_uint),
        ('BaseL', c_uint),
        ('Base1', c_uint),
        ('BaseL1', c_uint),
        ('Mem', c_uint),
        ('MemL', c_uint),
        ('Mem1', c_uint),
        ('MemL1', c_uint),
        ('Irq', c_uint),
        ('BoardType', c_uint),
        ('DSPType', c_uint),
        ('Dma', c_uint),
        ('DmaDac', c_uint),
        ('DTA_REG', c_uint),
        ('IDMA_REG', c_uint),
        ('CMD_REG', c_uint),
        ('IRQ_RST', c_uint),
        ('DTA_ARRAY', c_uint),
        ('RDY_REG', c_uint),
        ('CFG_REG', c_uint),
    ]


class L780:
    STREAM_ADC: int = 1
    STREAM_DAC: int = 2

    def __init__(self, slot: int = 0) -> None:
        create_instance = lib_l780.createInstance
        create_instance.restype = PCL780
        self._instance: PCL780 = create_instance(c_ulong(slot))
        if not self._instance:
            raise RuntimeError('Failed to connect to an L780 board')

    def open(self) -> int:
        return lib_l780.openBoard(self._instance)

    def close(self) -> int:
        return lib_l780.closeBoard(self._instance)

    def read_description(self):
        pd: L780BoardDescription = L780BoardDescription()
        lib_l780.readBoardDescription(self._instance, byref(pd))
        # print(pd)

    def request_stream_buffer(self, stream_id: int) -> int:
        return lib_l780.requestStreamBuffer(self._instance, stream_id)

    def fill_adc_parameters(self, ap: ADCParameters) -> int:
        return lib_l780.fillADCParameters(self._instance, byref(ap))

    def fill_dac_parameters(self, dp: DACParameters) -> int:
        return lib_l780.fillDACParameters(self._instance, byref(dp))

    def set_stream_parameters(self, sp: DAQParameters, stream_id: int) -> int:
        return lib_l780.setStreamParameters(self._instance, byref(sp), stream_id)

    def get_io_buffer_pointer(self, stream_id: int) -> POINTER(c_uint16):
        get_io_buffer = lib_l780.getIOBuffer
        get_io_buffer.restype = POINTER(c_uint16)
        return get_io_buffer(self._instance, stream_id)

    def get_io_buffer_size(self, stream_id: int) -> int:
        return lib_l780.getIOBufferSize(self._instance, stream_id)

    def get_io_buffer(self, stream_id: int) -> list[int]:
        return typing.cast(list, self.get_io_buffer_pointer(stream_id)[:self.get_io_buffer_size(stream_id)])

    def get_reg_buffer_pointer(self) -> POINTER(c_uint32):
        get_reg_buffer = lib_l780.getRegBuffer
        get_reg_buffer.restype = POINTER(c_uint32)
        return get_reg_buffer(self._instance)

    def get_slot_parameters(self) -> tuple[SlotParameters, int]:
        _slot_parameters: SlotParameters = SlotParameters()
        return (lib_l780.getSlotParameters(self._instance, byref(_slot_parameters)), _slot_parameters)[::-1]

    def load_firmware(self, firmware_file: None | str | Path = None) -> int:
        if not firmware_file:
            from subprocess import Popen, PIPE

            proc: Popen
            with Popen('ls''pci -v', shell=True, stdout=PIPE) as proc:
                proc_out: bytes = proc.stdout.read()
            found_ids: tuple[bool, ...] = (b'3631:4c37' in proc_out, b'3833:4c37' in proc_out, b'3931:4c37' in proc_out)
            if found_ids == (True, False, False):
                firmware_file = 'L761'
            elif found_ids == (False, True, False):
                firmware_file = 'L783'
            elif found_ids == (False, False, True):
                firmware_file = 'L791'  # doesn't need a firmware, but may still be present and mess the loading up
            else:
                raise RuntimeError('Can not determine the firmware to load')
        else:
            firmware_file = str(firmware_file)
            if firmware_file.casefold().endswith('.bio'):
                firmware_file = firmware_file[:-4]
        if not Path(firmware_file + '.bio').exists():
            raise FileNotFoundError(f'No file called "{firmware_file}.bio".found')
        return lib_l780.loadFirmware(self._instance, c_char_p(firmware_file.encode()))

    def test(self) -> int:
        return lib_l780.test(self._instance)

    def init_start(self) -> int:
        return lib_l780.initStart(self._instance)

    def start(self) -> int:
        return lib_l780.start(self._instance)

    def stop(self) -> int:
        return lib_l780.stop(self._instance)


error: int
board: L780 = L780()
board.open()

print('Slot parameters:')
sl: SlotParameters
sl, error = board.get_slot_parameters()
if error:
    raise RuntimeError(f'getSlotParameters failed with code {error}')
print(f'Base    {sl.Base}')
print(f'BaseL   {sl.BaseL}')
print(f'Mem     {sl.Mem}')
print(f'MemL    {sl.MemL}')
print(f'Type    {sl.BoardType}')
print(f'DSPType {sl.DSPType}')
print(f'Irq     {sl.Irq}')
print(f'Load Firmware {board.load_firmware()}')
print(f'Board Test    {board.test()}')

print(board.read_description())
error = board.request_stream_buffer(stream_id=L780.STREAM_ADC)
if error:
    raise RuntimeError(f'requestStreamBuffer failed with code {error}')

adc_par: ADCParameters = ADCParameters()

adc_par.AutoInit = True  # True == in loop
adc_par.dRate = 100.0  # kHz
adc_par.dFrame = 0.0
adc_par.dScale = 0.0

adc_par.SyncType = 3
adc_par.SyncSensitivity = 0
adc_par.SyncMode = 0
adc_par.SyncChannel = 0
adc_par.SyncThreshold = 0

adc_par.NumberOfChannels = 4
adc_par.Chn[0] = 0x0
adc_par.Chn[1] = 0x1
adc_par.Chn[2] = 0x2
adc_par.Chn[3] = 0x3

adc_par.FIFO = 1024
adc_par.IrqStep = 1024
adc_par.Pages = 64
adc_par.IrqEna = 1
adc_par.AdcEna = True

error = board.fill_adc_parameters(adc_par)
if error:
    raise RuntimeError(f'fillADCParameters failed with code {error}')
# print(adc_par)
error = board.set_stream_parameters(adc_par, stream_id=L780.STREAM_ADC)
if error:
    raise RuntimeError(f'setStreamParameters failed with code {error}')
data_p = board.get_io_buffer_pointer(stream_id=L780.STREAM_ADC)
sync_p = board.get_reg_buffer_pointer()
print(f'Current Firmware Version: {hex(typing.cast(int, sync_p[1021]))}')

board.init_start()
print('init device started')
board.start()
print('device started')

buffer_size: int = board.get_io_buffer_size(stream_id=L780.STREAM_ADC)
idx: int = int(input('enter something: ') or '0')
while 0 <= idx < adc_par.NumberOfChannels:
    raw_data: list[int] = typing.cast(list, data_p[idx:buffer_size:adc_par.NumberOfChannels])
    raw_data.sort()
    count: int = len(raw_data)
    if count & 1:
        s = raw_data[count // 2]
    else:
        s = 0.5 * raw_data[count // 2] + 0.5 * raw_data[count // 2 - 1]
    s *= 10. / (1 << 14)
    print(idx, s)
    idx = int(input('enter something: ') or '0')

board.stop()
print('device stoped')

board.close()
print('device closed')
