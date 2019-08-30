import io
import re
import struct
import time
from typing import List, Dict, Union

import crcmod.predefined
import serial
import serial.tools.list_ports

EXCLUDED_WEATHER_FIELDS: List[str] = [
    'PacketType',  # 4 Always zero for current firmware release
    'NextRec',  # 5 loc in archive memory for next data packet
]


def expand_keys(l: List[str]) -> List[str]:
    for item in l.copy():
        m = re.search(r'\[\d+\]$', item)
        if m:
            i = item[:m.start()]
            for n in range(int(m.group()[1:-1])):
                l.insert(l.index(item), '{key}[{index}]'.format(key=i, index=n))
            del l[l.index(item)]
    return l


def collect_keys(d: Dict[str, Union[None, int, float, str, List[Union[None, int, float, str]]]]) \
        -> Dict[str, Union[None, int, float, str, List[Union[None, int, float, str]]]]:
    dd = {}
    for key in d.copy():
        m = re.search(r'\[\d+\]$', key)
        if m:
            k = key[:m.start()]
            if k not in dd:
                dd[k] = {}
            dd[k][m.group()[1:-1]] = d.pop(key)
    for key in dd:
        d[key] = [dd[key][i] for i in sorted(dd[key])]
    return d


class Dallas:
    crc = crcmod.predefined.Crc('xmodem')
    models = {
        0x00: 'Wizard III',
        0x01: 'Wizard II',
        0x02: 'Monitor',
        0x03: 'Perception',
        0x04: 'GroWeather',
        0x05: 'Energy Environmonitor',
        0x06: 'Health Environmonitor',
        0x10: 'Vantage Pro'
    }
    realtime_data_names = expand_keys([
        # 'ACK',              # -1 ACK from stream
        # 'L',                # 0  character "L"
        # 'O',                # 1  character "O"
        # 'O',                # 2  character "O"
        'BarometerTrend',  # 3  character "P" (RevA) or the current
        #    3-hour Barometer trend as follows:
        #    196 = Falling Rapidly
        #    236 = Falling Slowly
        #    0   = Steady
        #    20  = Rising Slowly
        #    60  = Rising Rapidly
        # any other value is 3-hour data not available
        'PacketType',  # 4 Always zero for current firmware release
        'NextRec',  # 5 loc in archive memory for next data packet
        'Barometer',  # 7 Current barometer as (inch Hg / 1000)
        'InsideTemp',  # 9 Inside Temperature as (DegF / 10)
        'InsideHum',  # 11 Inside Humidity as percentage
        'OutsideTemp',  # 12 Outside Temperature as (DegF / 10)
        'WindSpeed',  # 14 Wind Speed
        'AvgWindSpeed',  # 15 10-Minute Average Wind Speed
        'WindDir',  # 16 Wind Direction in degress
        'XtraTemps[7]',  # 18 Extra Temperatures
        'SoilTemps[4]',  # 25 Soil Temperatures
        'LeafTemps[4]',  # 29 Leaf Temperatures
        'OutsideHum',  # 33 Outside Humidity
        'XtraHums[7]',  # 34 Extra Humidities
        'RainRate',  # 41 Rain Rate
        'UVLevel',  # 43 UV Level
        'SolarRad',  # 44 Solar Radiation
        'StormRain',  # 46 Total Storm Rain
        'StormStart',  # 48 Start date of current storm
        'RainDay',  # 50 Rain Today
        'RainMonth',  # 52 Rain this Month
        'RainYear',  # 54 Rain this Year
        'ETDay',  # 56 Day ET
        'ETMonth',  # 58 Month ET
        'ETYear',  # 60 Year ET
        'SoilMoist',  # 62 Soil Moistures
        'LeafWet',  # 66 Leaf Wetness
        'AlarmInside',  # 70 Inside Alarm bits
        'AlarmRain',  # 71 Rain Alarm bits
        'AlarmOut',  # 72 Outside Temperature Alarm bits
        'AlarmXtra[8]',  # 74 Extra Temp/Hum Alarms
        'AlarmSL',  # 82 Soil and Leaf Alarms
        'XmitBatt',  # 86 Transmitter battery status
        'BattLevel',  # 87 Console Battery Level:
        #    Voltage = ((wBattLevel * 300)/512)/100.0
        'ForecastIcon',  # 89 Forecast Icon
        'Forecast',  # 90 Forecast rule number
        'Sunrise',  # 91 Sunrise time (BCD encoded, 24hr)
        'Sunset',  # 93 Sunset time  (BCD encoded, 24hr)
        # 'LF',               # 95 Line Feed (\n) 0x0a
        # 'CR',               # 96 Carraige Return (\r) 0x0d
        # 'CRC',              # 97 CRC check bytes (CCITT-16 standard)
    ])
    #                       -          1111111 2222222222 3333333333 444444 55555 666 777777777 888888 9999999
    #                       1 01234579 1245689 0123456789 0123456789 013468 02468 026 012456789 012679 0135678
    realtime_data_types = '=x xxxbBHHh BhBBHbb bbbbbbbbbb bbbBBBBBBB BHBHHH HHHHH HII BBHBBBBBB BBIBHB BHHxxxx'

    highlow_data_names = expand_keys([
        # 'ACK',             # -1  ACK from stream

        # barometer
        'BaroLowDay',  # 0   Low barometer for today
        'BaroHighDay',  # 2   High barometer for today
        'BaroLowMonth',  # 4   Low barometer this month
        'BaroHighMonth',  # 6   High barometer this month
        'BaroLowYear',  # 8   Low barometer this year
        'BaroHighYear',  # 10  High barometer this year
        'BaroLowTime',  # 12  Low barometer time of day
        'BaroHighTime',  # 14  High barometer time of day

        # wind speed
        'WindHighDay',  # 16  Highest wind speed for today
        'WindHighTime',  # 18  Highest wind speed time of day
        'WindHighMonth',  # 18  Highest wind speed for the month
        'WindHighYear',  # 20  Highest wind speed for the year

        # inside temperatures
        'InTempHighDay',  # 21  Inside high temp for today
        'InTempLowDay',  # 23  Inside low temp for today
        'InTempHighTime',  # 25  Time of Inside high temp for today
        'InTempLowTime',  # 27  Time of Inside low temp for today
        'InTempLowMonth',  # 29  Inside low temp for the month
        'InTempHighMonth',  # 31  Inside high temp for the month
        'InTempLowYear',  # 33  Inside low temp for the year
        'InTempHighYear',  # 35  Inside high temp for the year

        # Inside Humidity
        'InHumHighDay',  # 37  Inside high humidity for the day
        'InHumLowDay',  # 38  Inside low humidity for the day
        'InHumHighTime',  # 39  Inside high humidity time for today
        'InHumLowTime',  # 41  Inside low humidity time for today
        'InHumHighMonth',  # 43  Inside high humidity for the month
        'InHumLowMonth',  # 44  Inside low humidity for the month
        'InHumHighYear',  # 45  Inside high humidity for the year
        'InHumLowYear',  # 46  Inside low humidity for the year

        # outside temperatures
        'TempLowDay',  # 49  Outside low temp for today
        'TempHighDay',  # 47  Outside high temp for today
        'TempLowTime',  # 53  Time of Outside low temp for today
        'TempHighTime',  # 51  Time of Outside high temp for today
        'TempHighMonth',  # 57  Outside high temp for the month
        'TempLowMonth',  # 55  Outside low temp for the month
        'TempHighYear',  # 61  Outside high temp for the year
        'TempLowYear',  # 59  Outside low temp for the year

        # dew point
        'DewLowDay',  # 63  dew point low for today
        'DewHighDay',  # 65  dew point high for today
        'DewLowTime',  # 67  Time of dew point low for today
        'DewHighTime',  # 69  Time of dew point high for today
        'DewHighMonth',  # 71  Highest dew point this month
        'DewLowMonth',  # 73  Lowest dew point this month
        'DewHighYear',  # 75  Highest dew point for the year
        'DewLowYear',  # 77  Lowest dew point for the year

        # wind chill
        'ChillLowDay',  # 79  wind chill low for today
        'ChillLowTime',  # 81  Time of wind chill low for today
        'ChillLowMonth',  # 83  Lowest wind chill this month
        'ChillLowYear',  # 85  Lowest wind chill for the year

        # heat indices
        'HeatHighDay',  # 87  Heat index high for today
        'HeatHighTime',  # 89  Time of heat index high for today
        'HeatHighMonth',  # 91  Heat index high for the month
        'HeatHighYear',  # 93  Heat index high for the year

        # THSW indices
        'THSWHighDay',  # 95  THSW index high for today
        'THSWHighTime',  # 97  Time of THSW index high for today
        'THSWHighMonth',  # 99  THSW index high for the month
        'THSWHighYear',  # 101 THSW index high for the year

        # Solar Radiation
        'SolarHighDay',  # 103 Solar rad high for today
        'SolarHighTime',  # 105 Time of Solar rad high for today
        'SolarHighMonth',  # 107 Solar rad high for the month
        'SolarHighYear',  # 109 Solar rad high for the year

        # UV Index
        'UVHighDay',  # 111 UV high for today
        'UVHighTime',  # 112 Time of UV high for today
        'UVHighMonth',  # 114 UV high for the month
        'UVHighYear',  # 115 UV high for the year

        # Rain Rate
        'RainHighDay',  # 116 Rain Rate high for today
        'RainHighTime',  # 118 Time of Rain Rate high for today
        'RainHighHour',  # 120 Highest Rain Rate this hour
        'RainHighMonth',  # 122 Highest Rain Rate this month
        'RainHighYear',  # 124 Highest Rain Rate this year

        'ExtraLeaf[150]',  # 126 Extra/Leaf/Soil Temperatures
        'ExtraTemps[80]',  # 276 Extra outside temp/Humidities
        'SoilMoist[40]',  # 356 Soil Moisture section
        'LeafWet[40]',  # 396 Leaf Wetness section
        # 'CRC',              # 436 CRC check bytes (CCITT-16 standard)
    ])
    highlow_data_types = \
        '=x HHHHHHHH BHBB hhhhhhhh BBHHBBBB hhhhhhhh hhhhhhhh hhhh hhhh HHHH HHHH BHBB HHHHH 150B80B40B40Bxx'
    #                                                                      1 1111 1111 11111 1   2  3  3  44
    #     -      111 1112 22222333 33344444 44555556 66667777 7888 8899 9990 0000 1111 11222 2   7  5  9  33
    #     1 02468024 6790 13579135 78913456 79135791 35791357 9135 7913 5791 3579 1245 68024 6   6  6  6  67

    barometer_trends = {
        -60: 'Falling Rapidly',
        -20: 'Falling Slowly',
        0: 'Steady',
        20: 'Rising Slowly',
        60: 'Rising Rapidly'
    }
    forecast_sentences = (
        'Mostly clear and cooler.',
        'Mostly clear with little temperature change.',
        'Mostly clear for 12 hrs. with little temperature change.',
        'Mostly clear for 12 to 24 hrs. and cooler.',
        'Mostly clear with little temperature change.',
        'Partly cloudy and cooler.',
        'Partly cloudy with little temperature change.',
        'Partly cloudy with little temperature change.',
        'Mostly clear and warmer.',
        'Partly cloudy with little temperature change.',
        'Partly cloudy with little temperature change.',
        'Mostly clear with little temperature change.',
        'Increasing clouds and warmer. Precipitation possible within 24 to 48 hrs.',
        'Partly cloudy with little temperature change.',
        'Mostly clear with little temperature change.',
        'Increasing clouds with little temperature change. Precipitation possible within 24 hrs.',
        'Mostly clear with little temperature change.',
        'Partly cloudy with little temperature change.',
        'Mostly clear with little temperature change.',
        'Increasing clouds with little temperature change. Precipitation possible within 12 hrs.',
        'Mostly clear with little temperature change.',
        'Partly cloudy with little temperature change.',
        'Mostly clear with little temperature change.',
        'Increasing clouds and warmer. Precipitation possible within 24 hrs.',
        'Mostly clear and warmer. Increasing winds.',
        'Partly cloudy with little temperature change.',
        'Mostly clear with little temperature change.',
        'Increasing clouds and warmer. Precipitation possible within 12 hrs. Increasing winds.',
        'Mostly clear and warmer. Increasing winds.',
        'Increasing clouds and warmer.',
        'Partly cloudy with little temperature change.',
        'Mostly clear with little temperature change.',
        'Increasing clouds and warmer. Precipitation possible within 12 hrs. Increasing winds.',
        'Mostly clear and warmer. Increasing winds.',
        'Increasing clouds and warmer.',
        'Partly cloudy with little temperature change.',
        'Mostly clear with little temperature change.',
        'Increasing clouds and warmer. Precipitation possible within 12 hrs. Increasing winds.',
        'Partly cloudy with little temperature change.',
        'Mostly clear with little temperature change.',
        'Mostly clear and warmer. Precipitation possible within 48 hrs.',
        'Mostly clear and warmer.',
        'Partly cloudy with little temperature change.',
        'Mostly clear with little temperature change.',
        'Increasing clouds with little temperature change. Precipitation possible within 24 to 48 hrs.',
        'Increasing clouds with little temperature change.',
        'Partly cloudy with little temperature change.',
        'Mostly clear with little temperature change.',
        'Increasing clouds and warmer. Precipitation possible within 12 to 24 hrs.',
        'Partly cloudy with little temperature change.',
        'Mostly clear with little temperature change.',
        'Increasing clouds and warmer. Precipitation possible within 12 to 24 hrs. Windy.',
        'Partly cloudy with little temperature change.',
        'Mostly clear with little temperature change.',
        'Increasing clouds and warmer. Precipitation possible within 12 to 24 hrs. Windy.',
        'Partly cloudy with little temperature change.',
        'Mostly clear with little temperature change.',
        'Increasing clouds and warmer. Precipitation possible within 6 to 12 hrs.',
        'Partly cloudy with little temperature change.',
        'Mostly clear with little temperature change.',
        'Increasing clouds and warmer. Precipitation possible within 6 to 12 hrs. Windy.',
        'Partly cloudy with little temperature change.',
        'Mostly clear with little temperature change.',
        'Increasing clouds and warmer. Precipitation possible within 12 to 24 hrs. Windy.',
        'Partly cloudy with little temperature change.',
        'Mostly clear with little temperature change.',
        'Increasing clouds and warmer. Precipitation possible within 12 hrs.',
        'Partly cloudy with little temperature change.',
        'Mostly clear with little temperature change.',
        'Increasing clouds and warmer. Precipitation likely.',
        'clearing and cooler. Precipitation ending within 6 hrs.',
        'Partly cloudy with little temperature change.',
        'clearing and cooler. Precipitation ending within 6 hrs.',
        'Mostly clear with little temperature change.',
        'Clearing and cooler. Precipitation ending within 6 hrs.',
        'Partly cloudy and cooler.',
        'Partly cloudy with little temperature change.',
        'Mostly clear and cooler.',
        'clearing and cooler. Precipitation ending within 6 hrs.',
        'Mostly clear with little temperature change.',
        'Clearing and cooler. Precipitation ending within 6 hrs.',
        'Mostly clear and cooler.',
        'Partly cloudy with little temperature change.',
        'Mostly clear with little temperature change.',
        'Increasing clouds with little temperature change. Precipitation possible within 24 hrs.',
        'Mostly cloudy and cooler. Precipitation continuing.',
        'Partly cloudy with little temperature change.',
        'Mostly clear with little temperature change.',
        'Mostly cloudy and cooler. Precipitation likely.',
        'Mostly cloudy with little temperature change. Precipitation continuing.',
        'Mostly cloudy with little temperature change. Precipitation likely.',
        'Partly cloudy with little temperature change.',
        'Mostly clear with little temperature change.',
        'Increasing clouds and cooler. Precipitation possible and windy within 6 hrs.',
        'Increasing clouds with little temperature change. Precipitation possible and windy within 6 hrs.',
        'Mostly cloudy and cooler. Precipitation continuing. Increasing winds.',
        'Partly cloudy with little temperature change.',
        'Mostly clear with little temperature change.',
        'Mostly cloudy and cooler. Precipitation likely. Increasing winds.',
        'Mostly cloudy with little temperature change. Precipitation continuing. Increasing winds.',
        'Mostly cloudy with little temperature change. Precipitation likely. Increasing winds.',
        'Partly cloudy with little temperature change.',
        'Mostly clear with little temperature change.',
        'Increasing clouds and cooler. Precipitation possible within 12 to 24 hrs. '
        'Possible wind shift to the W, NW, or N.',
        'Increasing clouds with little temperature change. Precipitation possible within 12 to 24 hrs. '
        'Possible wind shift to the W, NW, or N.',
        'Partly cloudy with little temperature change.',
        'Mostly clear with little temperature change.',
        'Increasing clouds and cooler. Precipitation possible within 6 hrs. '
        'Possible wind shift to the W, NW, or N.',
        'Increasing clouds with little temperature change. Precipitation possible within 6 hrs. '
        'Possible wind shift to the W, NW, or N.',
        'Mostly cloudy and cooler. Precipitation ending within 12 hrs. Possible wind shift to the W, NW, or N.',
        'Mostly cloudy and cooler. Possible wind shift to the W, NW, or N.',
        'Mostly cloudy with little temperature change. Precipitation ending within 12 hrs. '
        'Possible wind shift to the W, NW, or N.',
        'Mostly cloudy with little temperature change. Possible wind shift to the W, NW, or N.',
        'Mostly cloudy and cooler. Precipitation ending within 12 hrs. Possible wind shift to the W, NW, or N.',
        'Partly cloudy with little temperature change.',
        'Mostly clear with little temperature change.',
        'Mostly cloudy and cooler. Precipitation possible within 24 hrs. Possible wind shift to the W, NW, or N.',
        'Mostly cloudy with little temperature change. Precipitation ending within 12 hrs. '
        'Possible wind shift to the W, NW, or N.',
        'Mostly cloudy with little temperature change. Precipitation possible within 24 hrs. '
        'Possible wind shift to the W, NW, or N.',
        'clearing, cooler and windy. Precipitation ending within 6 hrs.',
        'clearing, cooler and windy.',
        'Mostly cloudy and cooler. Precipitation ending within 6 hrs. '
        'Windy with possible wind shift to the W, NW, or N.',
        'Mostly cloudy and cooler. Windy with possible wind shift to the W, NW, or N.',
        'clearing, cooler and windy.',
        'Partly cloudy with little temperature change.',
        'Mostly clear with little temperature change.',
        'Mostly cloudy with little temperature change. Precipitation possible within 12 hrs. Windy.',
        'Partly cloudy with little temperature change.',
        'Mostly clear with little temperature change.',
        'Increasing clouds and cooler. Precipitation possible within 12 hrs., possibly heavy at times. Windy.',
        'Mostly cloudy and cooler. Precipitation ending within 6 hrs. Windy.',
        'Partly cloudy with little temperature change.',
        'Mostly clear with little temperature change.',
        'Mostly cloudy and cooler. Precipitation possible within 12 hrs. Windy.',
        'Mostly cloudy and cooler. Precipitation ending in 12 to 24 hrs.',
        'Mostly cloudy and cooler.',
        'Mostly cloudy and cooler. Precipitation continuing, possible heavy at times. Windy.',
        'Partly cloudy with little temperature change.',
        'Mostly clear with little temperature change.',
        'Mostly cloudy and cooler. Precipitation possible within 6 to 12 hrs. Windy.',
        'Mostly cloudy with little temperature change. Precipitation continuing, possibly heavy at times. Windy.',
        'Partly cloudy with little temperature change.',
        'Mostly clear with little temperature change.',
        'Mostly cloudy with little temperature change. Precipitation possible within 6 to 12 hrs. Windy.',
        'Partly cloudy with little temperature change.',
        'Mostly clear with little temperature change.',
        'Increasing clouds with little temperature change. '
        'Precipitation possible within 12 hrs., possibly heavy at times. Windy.',
        'Mostly cloudy and cooler. Windy.',
        'Mostly cloudy and cooler. Precipitation continuing, possibly heavy at times. Windy.',
        'Partly cloudy with little temperature change.',
        'Mostly clear with little temperature change.',
        'Mostly cloudy and cooler. Precipitation likely, possibly heavy at times. Windy.',
        'Mostly cloudy with little temperature change. Precipitation continuing, possibly heavy at times. Windy.',
        'Mostly cloudy with little temperature change. Precipitation likely, possibly heavy at times. Windy.',
        'Partly cloudy with little temperature change.',
        'Mostly clear with little temperature change.',
        'Increasing clouds and cooler. Precipitation possible within 6 hrs. Windy.',
        'Increasing clouds with little temperature change. Precipitation possible within 6 hrs. windy',
        'Increasing clouds and cooler. Precipitation continuing. '
        'Windy with possible wind shift to the W, NW, or N.',
        'Partly cloudy with little temperature change.',
        'Mostly clear with little temperature change.',
        'Mostly cloudy and cooler. Precipitation likely. Windy with possible wind shift to the W, NW, or N.',
        'Mostly cloudy with little temperature change. Precipitation continuing. '
        'Windy with possible wind shift to the W, NW, or N.',
        'Mostly cloudy with little temperature change. Precipitation likely. '
        'Windy with possible wind shift to the W, NW, or N.',
        'Increasing clouds and cooler. Precipitation possible within 6 hrs. '
        'Windy with possible wind shift to the W, NW, or N.',
        'Partly cloudy with little temperature change.',
        'Mostly clear with little temperature change.',
        'Increasing clouds and cooler. Precipitation possible within 6 hrs. '
        'Possible wind shift to the W, NW, or N.',
        'Increasing clouds with little temperature change. Precipitation possible within 6 hrs. '
        'Windy with possible wind shift to the W, NW, or N.',
        'Increasing clouds with little temperature change. Precipitation possible within 6 hrs. '
        'Possible wind shift to the W, NW, or N.',
        'Partly cloudy with little temperature change.',
        'Mostly clear with little temperature change.',
        'Increasing clouds and cooler. Precipitation possible within 6 hrs. '
        'Windy with possible wind shift to the W, NW, or N.',
        'Increasing clouds with little temperature change. Precipitation possible within 6 hrs. '
        'Windy with possible wind shift to the W, NW, or N.',
        'Partly cloudy with little temperature change.',
        'Mostly clear with little temperature change.',
        'Increasing clouds and cooler. Precipitation possible within 12 to 24 hrs. '
        'Windy with possible wind shift to the W, NW, or N.',
        'Increasing clouds with little temperature change. Precipitation possible within 12 to 24 hrs. '
        'Windy with possible wind shift to the W, NW, or N.',
        'Mostly cloudy and cooler. Precipitation possibly heavy at times and ending within 12 hrs. '
        'Windy with possible wind shift to the W, NW, or N.',
        'Partly cloudy with little temperature change.',
        'Mostly clear with little temperature change.',
        'Mostly cloudy and cooler. Precipitation possible within 6 to 12 hrs., possibly heavy at times. '
        'Windy with possible wind shift to the W, NW, or N.',
        'Mostly cloudy with little temperature change. Precipitation ending within 12 hrs. '
        'Windy with possible wind shift to the W, NW, or N.',
        'Mostly cloudy with little temperature change. '
        'Precipitation possible within 6 to 12 hrs., possibly heavy at times. '
        'Windy with possible wind shift to the W, NW, or N.',
        'Mostly cloudy and cooler. Precipitation continuing.',
        'Partly cloudy with little temperature change.',
        'Mostly clear with little temperature change.',
        'Mostly cloudy and cooler. Precipitation likely, windy with possible wind shift to the W, NW, or N.',
        'Mostly cloudy with little temperature change. Precipitation continuing.',
        'Mostly cloudy with little temperature change. Precipitation likely.',
        'Partly cloudy with little temperature change.',
        'Mostly clear with little temperature change.',
        'Mostly cloudy and cooler. Precipitation possible within 12 hours, possibly heavy at times. Windy.',
        'FORECAST REQUIRES 3 HRS. OF RECENT DATA',
        'Mostly clear and cooler.',
    )

    def __init__(self):
        self._ser = serial.Serial()
        # noinspection PyTypeChecker
        self._sio = io.TextIOWrapper(io.BufferedRWPair(self._ser, self._ser, 1), newline='\r')
        self._communicating: bool = False

    def open_serial(self):
        self._communicating = False
        ports = serial.tools.list_ports.comports()
        for port in ports:
            if port.pid == 0xea60 and port.vid == 0x10c4:
                self._ser.port = port.device
                self._ser.baudrate = 19200
                self._ser.parity = serial.PARITY_NONE
                self._ser.bytesize = serial.EIGHTBITS
                self._ser.timeout = 1
                self._ser.write_timeout = 1
                try:
                    self._ser.open()
                except PermissionError:
                    print(f'Permission to open {self._ser.port} denied')
                    time.sleep(1)  # to be changed
                except serial.serialutil.SerialException as ex:
                    print(ex.strerror)
                else:
                    print(self._ser.port, "opened for the Davis Instruments Data Logger")
                    self._communicating = False
                    break
        if not self._ser.is_open:
            time.sleep(1)

    def close_serial(self):
        self._ser.close()

    def _block(self, timeout: float = 3.):
        i = 0
        dt = 0.1
        while self._communicating:
            time.sleep(dt)
            i += 1
            if dt * i > timeout:
                return False
        return True

    def read_text(self, cmd: str) -> Union[None, str]:
        if not self._block():
            print('controller is very busy to respond to', cmd)
            return None
        # print('command:', cmd)
        if not self._ser.is_open:
            self.open_serial()
        while self._ser.is_open:
            msg = cmd + '\n'
            try:
                self._communicating = True
                self._sio.write(msg)
                # print('written', msg.encode('ascii'))
                self._sio.flush()
                # print('reading...')
                resp = [l.strip() for l in self._sio.readlines()]
                self._sio.flush()
                self._communicating = False
            except (serial.SerialException, TypeError):
                self._communicating = False
                continue
            if len(resp) == 0:
                self.close_serial()
                print('restarting', self._ser.port)
                self.open_serial()
                continue
            if resp[1] != 'OK':
                print('wrong response:', msg, resp)
                continue
            # print(msg.encode('ascii'), resp)
            self.close_serial()
            return resp[2]
        return None

    def read_bytes(self, cmd, length=None):
        if not self._block():
            print('controller is very busy to respond to', cmd)
            return None
        # print('command:', cmd)
        resp = None
        if not self._ser.is_open:
            self.open_serial()
        while self._ser.is_open:
            msg = cmd + '\n'
            resp = b''
            try:
                self._communicating = True
                self._ser.write(msg.encode('ascii'))
                self._ser.flush()
                if length is None:
                    while self._ser.is_open and (len(resp) < 3
                                                 or self.crc.new(resp[1:-2]).crcValue != resp[-1] + 0x100 * resp[-2]):
                        resp += self._ser.read()
                else:
                    resp = self._ser.read(size=length)
                self._ser.flush()
                self._communicating = False
            except (serial.SerialException, TypeError):
                self._communicating = False
                continue
            # print('read', resp)
            if len(resp) == 0:
                self.close_serial()
                print('restarting ' + self._ser.port)
                self.open_serial()
                continue
            if (length is not None and len(resp) != length) or \
                    (len(resp) >= 2 and resp[0] != 0x06) or \
                    ((length is None or length > 2)  # ↓↓ ACK or checksum ↓↓
                     and (len(resp) < 3 or self.crc.new(resp[1:-2]).crcValue != resp[-1] + 0x100 * resp[-2])):
                print('wrong response:', msg.encode('ascii'), resp)
                continue
            self.close_serial()
            break
        return resp

    def get_time(self):
        r = self.read_bytes('GETTIME')
        t = {'seconds': r[1], 'minutes': r[2], 'hours': r[3], 'day': r[4], 'month': r[5], 'year': r[6] + 1900}
        return t

    def get_version(self):
        return self.read_text('VER')

    def get_model(self):
        model = self.read_bytes('WRD\022\115', 2)
        if model is not None and model[1] in self.models:
            return self.models[model[1]]
        else:
            return 'unknown'

    def get_realtime_data(self):
        r = self.read_bytes('LOOP 1')
        data = {}
        if len(r) == struct.calcsize(self.realtime_data_types):
            data = dict(zip(self.realtime_data_names, struct.unpack(self.realtime_data_types, r)))
            # correcting values to get human-readable format
            data['BarometerTrend'] = self.barometer_trends[data['BarometerTrend']] \
                if data['BarometerTrend'] in self.barometer_trends else None
            data['Barometer'] = data['Barometer'] * 0.0254 if data['Barometer'] else None
            data['RainRate'] /= 100.0
            data['UVLevel'] = None if data['UVLevel'] == 0xff else data['UVLevel'] / 100.0
            if data['SolarRad'] == 0x7fff:
                data['SolarRad'] = None
            if data['StormStart'] == 0xffff:
                data['StormStart'] = None
            if data['SoilMoist'] == 0xffffffff:
                data['SoilMoist'] = None
            if data['LeafWet'] == 0xffffff:
                data['LeafWet'] = None
            data['InsideTemp'] = round((data['InsideTemp'] / 10.0 - 32.0) / 9.0 * 5.0, 2)
            data['OutsideTemp'] = round((data['OutsideTemp'] / 10.0 - 32.0) / 9.0 * 5.0, 2)
            data['StormRain'] /= 100.0
            data['RainDay'] /= 100.0
            data['RainMonth'] /= 100.0
            data['RainYear'] /= 100.0
            data['BattLevel'] *= 3.0 / 512.0
            data['Sunrise'] = '{HH}:{MM}'.format(HH=int(data['Sunrise'] // 100), MM=data['Sunrise'] % 100) \
                if data['Sunrise'] not in (0x7fff, 0xffff) else None
            data['Sunset'] = '{HH}:{MM}'.format(HH=int(data['Sunset'] // 100), MM=data['Sunset'] % 100) \
                if data['Sunset'] not in (0x7fff, 0xffff) else None
            data['Forecast'] = self.forecast_sentences[data['Forecast']] \
                if data['Forecast'] < len(self.forecast_sentences) else None
            collect_keys(data)
            for key, default in [('XtraTemps', -1), ('SoilTemps', -1), ('LeafTemps', -1), ('XtraHums', 255)]:
                if isinstance(data[key], list):
                    for index, item in enumerate(data[key]):
                        if item == default:
                            data[key][index] = None
            data = dict((key, value)
                        for key, value in data.items()
                        if ((value is not None
                             or (isinstance(value, list) and any([item is not None for item in value])))
                            and key not in EXCLUDED_WEATHER_FIELDS))
        else:
            print('invalid data size:', len(r), struct.calcsize(self.realtime_data_types))
        return data

    def get_highlow_data(self):
        r = self.read_bytes('HILOWS')
        data = {}
        if len(r) == struct.calcsize(self.highlow_data_types):
            data = dict(zip(self.highlow_data_names, struct.unpack(self.highlow_data_types, r)))
            # correcting values to get human-readable format
            for key2 in ('LowDay', 'HighDay', 'LowMonth', 'HighMonth', 'LowYear', 'HighYear'):
                for key, denom in (('Baro', 1. / 0.0254),):
                    data[key + key2] /= denom
                for key, denom in (('InTemp', 10.0), ('Temp', 10.0)):
                    data[key + key2] = (data[key + key2] / denom - 32.0) / 9.0 * 5.0
            for key2 in ('HighDay', 'HighMonth', 'HighYear'):
                for key, denom in (('Solar', 10.0), ('UV', 10.0), ('Rain', 100.0)):
                    data[key + key2] /= denom
            for key in data:
                if key.endswith('Time'):
                    data[key] = '{HH}:{MM}'.format(HH=int(data[key] // 100), MM=data[key] % 100) \
                        if data[key] not in (0x7fff, 0xffff) else None
            collect_keys(data)
        else:
            print('invalid data size:', len(r), struct.calcsize(self.highlow_data_types))
        return data

    # TODO: there are more commands:
    #  EEBRD %X %X
    #  EEBWR %X %X
    #  NEWSETUP
    #  DMPAFT
    #  EEWR %X %X
    #  VER
    #  GETTIME
    #  SETTIME
    #  LOOP %d
    #  HILOWS
    #  SETPER %d
    #  PUTRAIN %d
    #  CLRHIGHS 2
    #  CLRHIGHS 1
    #  CLRHIGHS 0
    #  CLRLOWS 2
    #  CLRLOWS 1
    #  CLRLOWS 0
    #  CLRGRA
    #  CLRALM
    #  CLRCAL
    #  CLRVAR %d
    #  CLRLOG
    #  BAR=%hd %hd
    #  CALED
    #  CALFIX
    #  EEBWR %X 4
    #  RXCHECK
    #  BARDATA


if __name__ == '__main__':
    def main():
        ws = Dallas()
        ws.open_serial()
        for key, value in ws.get_realtime_data().items():
            print(key, '\t', value)
        ws.close_serial()


    main()
