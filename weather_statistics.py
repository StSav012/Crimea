#!/usr/bin/python3
# -*- coding: utf-8 -*-

# sending email
import calendar
import sys
from datetime import timedelta
from typing import Optional

import numpy as np
import pandas as pd

TIME_FIELD: str = 'Time'


def main():
    data: pd.DataFrame = pd.read_table(sys.argv[1],
                                       index_col='Time',
                                       parse_dates=True,
                                       usecols=[
                                           'Time',
                                           # 'Barometer',
                                           # 'InsideTemp',
                                           # 'InsideHum',
                                           'OutsideTemp',
                                           'WindSpeed',
                                           'AvgWindSpeed',
                                           # 'WindDir',
                                           'OutsideHum',
                                           'RainRate',
                                           'UVLevel',
                                           'SolarRad',
                                           'StormRain',
                                           'RainDay',
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

    data.describe().to_csv(f'/tmp/statistics for all time.txt', sep='\t')

    for month in range(1, 13):
        mask: np.ndarray = (data.index.month == month)
        if not mask.any():
            continue
        data.loc[data.index.month == month].describe()\
            .to_csv(f'/tmp/statistics for {calendar.month_name[month]} of any year.txt', sep='\t')

    for year in range(2018, 2022):
        for month in range(1, 13):
            mask: np.ndarray = (data.index.month == month) & (data.index.year == year)
            if not mask.any():
                continue
            data.loc[mask].describe()\
                .to_csv(f'/tmp/statistics for {calendar.month_name[month]} {year}.txt', sep='\t')

    for year in range(2018, 2022):
        mask: np.ndarray = (data.index.year == year)
        if not mask.any():
            continue
        data.loc[mask].describe()\
            .to_csv(f'/tmp/statistics for all months of {year}.txt', sep='\t')

    for year in range(2018, 2022):
        for start_month, end_month in ([5, 9], [11, 3]):
            if end_month >= start_month:
                mask: np.ndarray = ((data.index.year == year)
                                    & (data.index.month >= start_month) & (data.index.month <= end_month))
                fn: str = f'/tmp/statistics from {calendar.month_name[start_month]} ' \
                          f'to {calendar.month_name[end_month]} {year}.txt'
            else:
                mask: np.ndarray = (((data.index.year == year) & (data.index.month >= start_month))
                                    | ((data.index.year == year + 1) & (data.index.month <= end_month)))
                fn: str = f'/tmp/statistics from {calendar.month_name[start_month]} {year} ' \
                          f'to {calendar.month_name[end_month]} {year + 1}.txt'
            if not mask.any():
                continue
            data.loc[mask].describe().to_csv(fn, sep='\t')

    for start_month, end_month in ([5, 9], [11, 3]):
        if end_month >= start_month:
            # noinspection PyTypeChecker
            mask: np.ndarray = ((data.index.month >= start_month) & (data.index.month <= end_month))
        else:
            # noinspection PyTypeChecker
            mask: np.ndarray = ((data.index.month >= start_month) | (data.index.month <= end_month))
        if not mask.any():
            continue
        data.loc[mask].describe().to_csv(f'/tmp/statistics from {calendar.month_name[start_month]} '
                                         f'to {calendar.month_name[end_month]} of any year.txt', sep='\t')

    mask: np.ndarray = (data.index.hour <= 4)
    if mask.any():
        data.loc[mask].describe() \
            .to_csv(f'/tmp/statistics for all time 0AM to 4AM.txt', sep='\t')

    for month in range(1, 13):
        mask: np.ndarray = (data.index.month == month) & (data.index.hour <= 4)
        if not mask.any():
            continue
        data.loc[mask].describe()\
            .to_csv(f'/tmp/statistics for {calendar.month_name[month]} of any year 0AM to 4AM.txt', sep='\t')

    for year in range(2018, 2022):
        for month in range(1, 13):
            mask: np.ndarray = (data.index.month == month) & (data.index.year == year) & (data.index.hour <= 4)
            if not mask.any():
                continue
            data.loc[mask].describe()\
                .to_csv(f'/tmp/statistics for {calendar.month_name[month]} {year} 0AM to 4AM.txt', sep='\t')

    for year in range(2018, 2022):
        mask: np.ndarray = (data.index.year == year) & (data.index.hour <= 4)
        if not mask.any():
            continue
        data.loc[mask].describe()\
            .to_csv(f'/tmp/statistics for all months of {year} 0AM to 4AM.txt', sep='\t')

    for year in range(2018, 2022):
        for start_month, end_month in ([5, 9], [11, 3]):
            if end_month >= start_month:
                mask: np.ndarray = ((data.index.year == year)
                                    & (data.index.month >= start_month) & (data.index.month <= end_month)
                                    & (data.index.hour <= 4))
                fn: str = f'/tmp/statistics from {calendar.month_name[start_month]} ' \
                          f'to {calendar.month_name[end_month]} {year} 0AM to 4AM.txt'
            else:
                mask: np.ndarray = ((((data.index.year == year) & (data.index.month >= start_month))
                                     | ((data.index.year == year + 1) & (data.index.month <= end_month)))
                                    & (data.index.hour <= 4))
                fn: str = f'/tmp/statistics from {calendar.month_name[start_month]} {year} ' \
                          f'to {calendar.month_name[end_month]} {year + 1} 0AM to 4AM.txt'
            if not mask.any():
                continue
            data.loc[mask].describe().to_csv(fn, sep='\t')

    for start_month, end_month in ([5, 9], [11, 3]):
        if end_month >= start_month:
            mask: np.ndarray = ((data.index.month >= start_month) & (data.index.month <= end_month)
                                & (data.index.hour <= 4))
        else:
            mask: np.ndarray = (((data.index.month >= start_month) | (data.index.month <= end_month))
                                & (data.index.hour <= 4))
        if not mask.any():
            continue
        data.loc[mask].describe().to_csv(f'/tmp/statistics from {calendar.month_name[start_month]} '
                                         f'to {calendar.month_name[end_month]} of any year 0AM to 4AM.txt', sep='\t')


def match_rp5():
    an_hour_and_a_half: timedelta = timedelta(minutes=90)
    data: pd.DataFrame = pd.read_table(sys.argv[1],
                                       index_col='Time',
                                       parse_dates=True,
                                       usecols=[
                                           'Time',
                                           'Barometer',
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
                                           'StormRain',
                                           'RainDay',
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
    rp5_data: pd.DataFrame = pd.read_table(sys.argv[2],
                                           index_col=0,
                                           sep=';',
                                           comment='#'
                                           )
    # noinspection PyTypeChecker
    rp5_data.index = pd.to_datetime(rp5_data.index, format='%d.%m.%Y %H:%M')
    rp5_data = rp5_data.dropna(axis=1, how='all')
    averaged_data: Optional[pd.DataFrame] = None
    for rp5_ts, rp5_line in rp5_data.iterrows():
        print(rp5_ts)
        # noinspection PyTypeChecker
        data_piece: pd.DataFrame = data.loc[(rp5_ts - an_hour_and_a_half < data.index)
                                            & (data.index < rp5_ts + an_hour_and_a_half)]
        averaged_data_piece: pd.DataFrame = pd.DataFrame(data_piece.median(), columns=[rp5_ts])
        if data_piece.size:
            wind_sin: float = (data_piece['WindSpeed'] * np.sin(data_piece['WindDir'])).sum()
            wind_cos: float = (data_piece['WindSpeed'] * np.cos(data_piece['WindDir'])).sum()
            averaged_data_piece.loc['WindDir', rp5_ts] = np.rad2deg(np.arctan2(wind_sin, wind_cos))
        else:
            averaged_data_piece.loc['WindDir', rp5_ts] = np.nan
        if averaged_data is None:
            averaged_data = averaged_data_piece
        else:
            averaged_data = pd.concat((averaged_data, averaged_data_piece), axis=1)
    total_averaged_data: pd.DataFrame = pd.concat((averaged_data.T, rp5_data), axis=1)
    total_averaged_data.to_excel('/tmp/rp5 comparison.xlsx', sheet_name='Weather', freeze_panes=(1, 1))


if __name__ == '__main__':
    if len(sys.argv) == 2:
        main()
    elif len(sys.argv) == 3:
        match_rp5()
