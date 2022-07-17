# coding: utf-8
import typing
from ctypes import *
from ctypes.util import find_library

liblcomp: CDLL = CDLL(find_library('lcomp') or './lib''lcomp.so')


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
        self.s_Type = DAQParameters.ADC_PARAM

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
        self.s_Type = DAQParameters.DAC_PARAM

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


class L791:
    STREAM_ADC: int = 1
    STREAM_DAC: int = 2

    def __init__(self, slot: int = 0) -> None:
        create_instance = liblcomp.createInstance
        create_instance.restype = PCL791
        self._instance: PCL791 = create_instance(c_ulong(slot))
        if not self._instance:
            raise RuntimeError('Failed to connect to an L791 board')

    def open(self) -> int:
        return liblcomp.openBoard(self._instance)

    def close(self) -> int:
        return liblcomp.closeBoard(self._instance)

    def read_description(self):
        pd = L791BoardDescription()
        liblcomp.readBoardDescription(self._instance, byref(pd))
        # print(pd)

    def request_stream_buffer(self, stream_id: int) -> int:
        return liblcomp.requestStreamBuffer(self._instance, stream_id)

    def fill_adc_parameters(self, ap: ADCParameters) -> int:
        return liblcomp.fillADCParameters(self._instance, byref(ap))

    def fill_dac_parameters(self, dp: DACParameters) -> int:
        return liblcomp.fillDACParameters(self._instance, byref(dp))

    def set_stream_parameters(self, sp: DAQParameters, stream_id: int) -> int:
        return liblcomp.setStreamParameters(self._instance, byref(sp), stream_id)

    def get_io_buffer_pointer(self, stream_id: int) -> POINTER(c_uint16):
        get_io_buffer = liblcomp.getIOBuffer
        get_io_buffer.restype = POINTER(c_uint16)
        return get_io_buffer(self._instance, stream_id)

    def get_io_buffer_size(self, stream_id: int) -> int:
        return liblcomp.getIOBufferSize(self._instance, stream_id)

    def get_io_buffer(self, stream_id: int) -> list[int]:
        return typing.cast(list, self.get_io_buffer_pointer(stream_id)[:self.get_io_buffer_size(stream_id)])

    def get_reg_buffer_pointer(self) -> POINTER(c_uint32):
        get_reg_buffer = liblcomp.getRegBuffer
        get_reg_buffer.restype = POINTER(c_uint32)
        return get_reg_buffer(self._instance)

    def get_reg_buffer_size(self) -> int:
        return liblcomp.getRegBufferSize(self._instance)

    def get_reg_buffer(self) -> list[int]:
        return typing.cast(list, self.get_reg_buffer_pointer()[:self.get_reg_buffer_size()])

    def init_start(self) -> int:
        return liblcomp.initStart(self._instance)

    def start(self) -> int:
        return liblcomp.start(self._instance)

    def stop(self) -> int:
        return liblcomp.stop(self._instance)


error: int
board: L791 = L791()
board.open()
print(board.read_description())
error = board.request_stream_buffer(stream_id=L791.STREAM_ADC)
if error:
    raise RuntimeError(f'requestStreamBuffer failed with code {error}')

adc_par: ADCParameters = ADCParameters()

adc_par.AutoInit = True  # True == in loop
adc_par.dRate = 200.0  # kHz
adc_par.dFrame = .01

adc_par.SyncType = 0
adc_par.SyncSrc = 0

adc_par.NumberOfChannels = 4
adc_par.Chn[0] = 0x0
adc_par.Chn[1] = 0x1
adc_par.Chn[2] = 0x2
adc_par.Chn[3] = 0x3

adc_par.FIFO = 1024

adc_par.IrqStep = 1024
adc_par.Pages = 64
adc_par.IrqEna = 3  # no interruptions
adc_par.AdcEna = True

error = board.fill_adc_parameters(adc_par)
if error:
    raise RuntimeError(f'fillADCParameters failed with code {error}')
# print(adc_par)
error = board.set_stream_parameters(adc_par, stream_id=L791.STREAM_ADC)
if error:
    raise RuntimeError(f'setStreamParameters failed with code {error}')
data_p = board.get_io_buffer_pointer(stream_id=L791.STREAM_ADC)
sync_p = board.get_reg_buffer_pointer()
print(f'Current Firmware Version: {hex(typing.cast(int, sync_p[1021]))}')

board.init_start()
print('init device started')
board.start()
print('device started')

buffer_size: int = board.get_io_buffer_size(stream_id=L791.STREAM_ADC)
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
