#!/usr/bin/python3
# -*- coding: utf-8 -*-
import argparse
import configparser
import csv
import gzip
import json
import os.path
import re
# sending email
import smtplib
from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List, Union

import ephem
import numpy as np
import xlsxwriter
from pytz import timezone

FIELDS = [
    'Time',
    'Wind Direction [°]',
    'Wind Speed',
    'Humidity [%]',
    'Temperature [°C]',
    'Rain Rate',
    'UV Level',
    'Solar Radiation',
    'Humidity Indoors [%]',
    'Temperature Indoors [°C]',
    'Last Sunrise',
    'Next Sunset'
]

SUMMARY_FIELDS = [
    'Date',
    'Humidity [%]',
    'Max Temperature [°C]',
    'Mean Temperature [°C]',
    'Min Temperature [°C]',
    'Average Wind Direction [°]',
    'Average Wind Speed',
    'Average UV Level',
    'Average Solar Radiation',
    'Precipitation',
    'Last Sunrise',
    'Next Sunset'
]

ap = argparse.ArgumentParser(description='extracts summary from raw data and writes it into an XLSX file')
ap.add_argument('-I', '--ignore-existing', help='skip check whether the result file exists',
                action='store_true', default=False)
ap.add_argument('-c', '--config', help='configuration file', default=os.path.splitext(__file__)[0] + '.ini')
ap.add_argument('-e', '--send-email', help='email the result file to the recipients listed in config',
                action='store_true', default=False)
ap.add_argument('-a', '--anyway', help='process files even if no new files given (younger than a day)',
                action='store_true', default=False)
ap.add_argument('-v', '--verbose', help='include every point into the report, not just daily averages',
                action='store_true', default=False)
ap.add_argument('-o', '--output-prefix', help='prefix for the result files',
                default='', type=str)
ap.add_argument('files', metavar='PATH', nargs='+', help='path to a file to process')
args = ap.parse_args()

config = configparser.ConfigParser()
config.read(args.config)

o = ephem.Observer()
o.name = 'QaraDag'
o.lat, o.lon = '44.9258269', '35.1912671'
sun = ephem.Sun(o)


def preprocess(text):
    try:
        data = json.loads(text)
    except json.decoder.JSONDecodeError:
        return None
    if 'raw_data' in data:
        return data['raw_data']
    else:
        return data


def process(data):
    weather: Dict[str, Union[None, int, float]] = {'timestamp': 0,
                                                   'WindDir': None, 'AvgWindSpeed': None, 'OutsideHum': None,
                                                   'OutsideTemp': None, 'RainRate': None, 'UVLevel': None,
                                                   'SolarRad': None, 'InsideHum': None, 'InsideTemp': None}
    for key in weather.keys():
        if key in data:
            weather[key] = data[key]
    date: datetime = datetime.fromtimestamp(weather['timestamp'], tz=timezone('Europe/Moscow'))
    o.date = date
    return dict(zip(FIELDS, [
        date,
        weather['WindDir'],
        weather['AvgWindSpeed'],
        weather['OutsideHum'],
        weather['OutsideTemp'],
        weather['RainRate'],
        weather['UVLevel'],
        weather['SolarRad'],
        weather['InsideHum'],
        weather['InsideTemp'],
        o.previous_rising(sun).datetime(),
        o.next_setting(sun).datetime()
    ]))


def json_mean(data_array, key):
    mean_data = None
    for item in data_array:
        if mean_data is None:
            mean_data = item[key]
        else:
            if isinstance(item[key], float) or isinstance(item[key], int):
                mean_data += item[key]
    if mean_data is not None:
        mean_data /= len(data_array)
    return mean_data


def json_max(data_array, key):
    max_data = None
    for item in data_array:
        if max_data is None:
            max_data = item[key]
        else:
            if max_data < item[key]:
                max_data = item[key]
    return max_data


def json_min(data_array, key):
    min_data = None
    for item in data_array:
        if min_data is None:
            min_data = item[key]
        else:
            if min_data > item[key]:
                min_data = item[key]
    return min_data


def json_mean_wind(data_array, speed_key, direction_key):
    sum_wind_cos = 0
    sum_wind_sin = 0
    for item in data_array:
        sum_wind_cos += item[speed_key] * np.cos(np.radians(item[direction_key]))
        sum_wind_sin += item[speed_key] * np.sin(np.radians(item[direction_key]))
    sum_wind_cos /= len(data_array)
    sum_wind_sin /= len(data_array)
    return np.degrees(np.arctan2(sum_wind_sin, sum_wind_cos)), np.hypot(sum_wind_sin, sum_wind_cos)


def process_stat(data_array, timestamp=None):
    date: datetime = datetime.fromtimestamp(json_mean(data_array, 'timestamp') if timestamp is None else timestamp,
                                            tz=timezone('Europe/Moscow'))
    o.date = date
    return dict(zip(SUMMARY_FIELDS, [
        date,
        json_mean(data_array, 'OutsideHum'),
        json_max(data_array, 'OutsideTemp'),
        json_mean(data_array, 'OutsideTemp'),
        json_min(data_array, 'OutsideTemp'),
        *json_mean_wind(data_array, 'AvgWindSpeed', 'WindDir'),
        json_mean(data_array, 'UVLevel'),
        json_mean(data_array, 'SolarRad'),
        json_mean(data_array, 'RainDay'),
        o.previous_rising(sun).datetime(),
        o.next_setting(sun).datetime()
    ]))


def write_header(worksheet, header, text_format):
    for index, caption in enumerate(header):
        worksheet.write_string(0, index, caption, text_format)
    return


def write_row(worksheet, row, row_dict, keys):
    for key in keys:
        if key not in row_dict:
            return False
    for index, key in enumerate(keys):
        if isinstance(row_dict[key], datetime):
            offset = datetime.utcoffset(row_dict[key])
            if offset is not None:
                value = row_dict[key].replace(tzinfo=None) + offset
            else:
                value = row_dict[key]
        else:
            value = row_dict[key]
        worksheet.write(row, index, value)
    return True


def list_files(path):
    files: List[str] = []
    if os.path.isdir(path):
        for file in os.listdir(path):
            if os.path.isfile(os.path.join(path, file)):
                files.append(os.path.join(path, file))
            elif os.path.isdir(os.path.join(path, file)):
                files.extend(list_files(os.path.join(path, file)))
    elif os.path.isfile(path):
        files.append(path)
    return sorted(files)


def timestamp_day(ts):
    return datetime.fromtimestamp(ts, tz=timezone('Europe/Moscow')).day


filenames: List[str] = []
for filename in args.files:
    filenames.extend(list_files(filename))

max_mod_time = 0
new_files_given = args.anyway
current_time = datetime.now().timestamp()
for filename in filenames:
    if filename.endswith('.json.gz') and os.path.exists(filename) and os.path.isfile(filename):
        mod_time = os.path.getmtime(filename)
        if max_mod_time < mod_time:
            max_mod_time = mod_time
        if current_time - mod_time < 86400:
            new_files_given = True
if not new_files_given:
    # nothing to do
    exit(0)
print(f'processing {len(filenames)} files')

if not max_mod_time:
    max_mod_time = datetime.now()
prefix: str = args.output_prefix if args.output_prefix \
    else 'daily_weather_' + datetime.date(datetime.fromtimestamp(max_mod_time)).isoformat()
results_file_name: str = prefix + '.xlsx'
if not args.ignore_existing and os.path.exists(results_file_name):
    exit(0)
workbook: Union[None, xlsxwriter.Workbook] = None
csv_file = None
csv_table: Union[None, csv.writer] = None
written_rows: int = 0

if args.verbose:
    for filename in filenames:
        if filename.endswith('.json.gz') and os.path.exists(filename) and os.path.isfile(filename):
            with gzip.GzipFile(filename, 'r') as fin:
                content = fin.read().decode()
                json_data = preprocess(content)
                if json_data is not None:
                    d = process(json_data)
                    if 'Time' not in d:
                        raise RuntimeWarning('\'Time\' key is not found in the file ' + filename)
                    if workbook is None:
                        workbook = xlsxwriter.Workbook(results_file_name,
                                                       {'default_date_format': 'dd.mm.yyyy hh:mm:ss.000'})
                        header_format = workbook.add_format({'bold': True})
                    if csv_file is None:
                        csv_file = open(prefix + '.csv', 'w', newline='')
                    if csv_table is None:
                        csv_table = csv.writer(csv_file)
                        csv_table.writerow(FIELDS)
                    csv_table.writerow([d[key] for key in FIELDS])
                    if not len(workbook.worksheets()):
                        workbook.add_worksheet('QaraDag Weather')
                        write_header(workbook.worksheets()[0], FIELDS, header_format)
                        written_rows = 1
                    if write_row(workbook.worksheets()[0], written_rows, d, FIELDS):
                        written_rows += 1
else:
    last_timestamp = None
    day_data = []
    for filename in filenames:
        if filename.endswith('.json.gz') and os.path.exists(filename) and os.path.isfile(filename):
            with gzip.GzipFile(filename, 'r') as fin:
                content = fin.read().decode()
                json_data = preprocess(content)
                if json_data is not None:
                    if isinstance(json_data, list):
                        json_data_has_weather = list(filter(lambda j: 'weather' in j, json_data))
                        if not json_data_has_weather:
                            continue
                        json_data_piece = {**json_data_has_weather[0]['weather'],
                                           'timestamp': json_data_has_weather[0]['timestamp']}
                    else:
                        json_data_piece = json_data
                    if 'OutsideHum' not in \
                            (json_data_piece['weather'] if 'weather' in json_data_piece else json_data_piece):
                        print(filename)
                    if last_timestamp is None:
                        day_data.append(json_data_piece)
                        last_timestamp = json_data_piece['timestamp']
                    elif timestamp_day(json_data_piece['timestamp']) != timestamp_day(last_timestamp):
                        try:
                            d = process_stat(day_data)
                        except KeyError as ex:
                            # print(filename, ex.args)
                            pass
                        else:
                            if 'Date' not in d:
                                raise RuntimeWarning('\'Date\' key is not found in the file ' + filename)
                            if workbook is None:
                                workbook = xlsxwriter.Workbook(results_file_name,
                                                               {'default_date_format': 'dd.mm.yyyy'})
                                header_format = workbook.add_format({'bold': True})
                            if csv_file is None:
                                csv_file = open(prefix + '.csv', 'w', newline='')
                            if csv_table is None:
                                csv_table = csv.writer(csv_file)
                                csv_table.writerow(SUMMARY_FIELDS)
                            csv_table.writerow([d[key] for key in SUMMARY_FIELDS])
                            if not len(workbook.worksheets()):
                                workbook.add_worksheet('QaraDag Weather Summary')
                                write_header(workbook.worksheets()[0], SUMMARY_FIELDS, header_format)
                                written_rows = 1
                            if write_row(workbook.worksheets()[0], written_rows, d, SUMMARY_FIELDS):
                                written_rows += 1
                        day_data = [json_data_piece]
                        last_timestamp = json_data_piece['timestamp']
                    else:
                        day_data.append(json_data_piece)
                        last_timestamp = json_data_piece['timestamp']
if workbook is not None:
    workbook.close()
    if args.send_email:
        server = config.get('email', 'server', fallback='')
        port = config.getint('email', 'port', fallback=0)
        sender = config.get('email', 'login', fallback='')
        password = config.get('email', 'password', fallback='')
        cc = re.findall(r"[\w.@]+", config.get('email', 'recipients', fallback=''))
        if server and port and sender and password and cc:
            msg = MIMEMultipart()
            msg['From'] = sender
            msg['To'] = cc[0]
            msg['Cc'] = ','.join(cc[1:])
            msg['Subject'] = 'Qara Dag Weather'
            body = 'Qara Dag weather summary for ' + datetime.isoformat(datetime.now(), sep=" ")
            msg.attach(MIMEText(body, 'plain'))
            with open(results_file_name, 'rb') as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', 'attachment; filename=' + results_file_name)
                msg.attach(part)
                server = smtplib.SMTP(server, port)
                server.starttls()
                server.login(sender, password)
                server.sendmail(sender, cc + [sender], msg.as_string())
                server.quit()
if csv_file is not None:
    csv_file.close()
