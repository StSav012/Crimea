#!/usr/bin/python3
# -*- coding: utf-8 -*-

# sending email
import calendar
import sys

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
            mask: np.ndarray = ((data.index.month >= start_month) & (data.index.month <= end_month))
        else:
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


if __name__ == '__main__':
    main()
