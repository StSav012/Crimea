#!/usr/bin/env python
# coding: utf-8
import bisect
import datetime
from pathlib import Path
from typing import Dict, Final

import numpy as np
import pandas as pd
from astral import LocationInfo
from astral.sun import sun

WEATHER_LOG: Final[Path] = Path('weather_2021-03-25.tsv')

TIME_FIELD: Final[str] = 'Time'


def main() -> None:
    location: LocationInfo = LocationInfo(timezone='Europe/Moscow',
                                          latitude=44.926435993854746, longitude=35.191896915012684)
    data: pd.DataFrame = pd.read_table(WEATHER_LOG,
                                       index_col=TIME_FIELD,
                                       parse_dates=True,
                                       usecols=[
                                           TIME_FIELD,
                                           # 'Barometer',
                                           # 'InsideTemp',
                                           # 'InsideHum',
                                           'OutsideTemp',
                                           'WindSpeed',
                                           # 'AvgWindSpeed',
                                           'WindDir',
                                           'OutsideHum',
                                           'RainRate',
                                           'UVLevel',
                                           'SolarRad',
                                           # 'StormRain',
                                           # 'RainDay',
                                           # 'RainMonth',
                                           # 'RainYear',
                                           'ETDay',
                                           # 'ETMonth',
                                           # 'ETYear',
                                           # 'BattLevel',
                                           # 'Sunrise',
                                           # 'Sunset',
                                           # 'Forecast'
                                       ]
                                       )

    data = data[::-1]
    date: datetime.date = data.index[0].date()
    last_date: Final[datetime.date] = data.index[-1].date()
    one_day: Final[datetime.timedelta] = datetime.timedelta(days=1)
    statistics = pd.DataFrame(columns=['Humidity', 'MaxTemperature', 'AvgTemperature', 'MinTemperature',
                                       'AvgWindDirection', 'AvgWindSpeed', 'AvgUVLevel', 'AvgSolarRad', 'RainDay',
                                       'Sunrise', 'Sunset'])
    index: np.ndarray = data.index.date
    while date <= last_date:
        print(f'{date}, {(last_date - date).days} days left')
        indices: slice = slice(bisect.bisect_left(index, date), bisect.bisect_right(index, date))
        data_piece: pd.DataFrame = data[indices]
        wind_sin: pd.Series = data_piece['WindSpeed'] * np.sin(np.deg2rad(data_piece['WindDir']))
        wind_cos: pd.Series = data_piece['WindSpeed'] * np.cos(np.deg2rad(data_piece['WindDir']))
        s: Dict[str, datetime.datetime] = sun(location.observer, date=date)
        statistics.loc[date] = {
            'Humidity': data_piece['OutsideHum'].mean(),
            'MaxTemperature': data_piece['OutsideTemp'].max(),
            'AvgTemperature': data_piece['OutsideTemp'].mean(),
            'MinTemperature': data_piece['OutsideTemp'].min(),
            'AvgWindDirection': np.rad2deg(np.arctan2(np.mean(wind_sin), np.mean(wind_cos))),
            'AvgWindSpeed': np.hypot(np.mean(wind_sin), np.mean(wind_cos)),
            'AvgUVLevel': data_piece['UVLevel'].mean(),
            'AvgSolarRad': data_piece['SolarRad'].mean(),
            'RainDay': data_piece['RainRate'].mean() * 24.0,
            'Sunrise': s['sunrise'].replace(tzinfo=None) + datetime.timedelta(hours=3),
            'Sunset': s['sunset'].replace(tzinfo=None) + datetime.timedelta(hours=3),
        }
        date += one_day
        # break
    statistics.to_excel('daily weather.xlsx', freeze_panes=(1, 1))


if __name__ == '__main__':
    main()
