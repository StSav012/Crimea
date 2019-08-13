#!/usr/bin/python3
# -*- coding: utf-8 -*-
import argparse
import configparser
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
from typing import List, Dict, Union

import xlsxwriter

fields = [
    'Time',
    '\u03c4',
    'Wind Direction [°]',
    'Wind Speed',
    'Humidity [%]',
    'Temperature [°C]',
    'Rain Rate',
    'UV Level',
    'Solar Radiation',
]

ap = argparse.ArgumentParser(description='extracts summary from raw data and writes it into an XLSX file')
ap.add_argument('-I', '--ignore-existing', help='skip check whether the result file exists',
                action='store_true', default=False)
ap.add_argument('-c', '--config', help='configuration file', default=os.path.splitext(__file__)[0] + '.ini')
ap.add_argument('-e', '--send-email', help='email the result file to the recipients listed in config',
                action='store_true', default=False)
ap.add_argument('-a', '--anyway', help='process files even if no new files given (younger than a day)',
                action='store_true', default=False)
ap.add_argument('-o', '--output-prefix', help='prefix for the result files',
                default='results_' + datetime.date(datetime.now()).isoformat())
ap.add_argument('files', metavar='PATH', nargs='+', help='path to a file to process')
args = ap.parse_args()

if os.path.exists(args.config):
    config = configparser.ConfigParser()
    config.read(args.config)
else:
    config = None


def preprocess(text):
    try:
        data = json.loads(text)
    except json.decoder.JSONDecodeError:
        return None
    if 'raw_data' in data:
        raw_data = data['raw_data']
    else:
        raw_data = data
    pre_last_angle = raw_data[-2]['angle'] if len(raw_data) > 2 else None
    length = len(raw_data)
    for i in range(2, length):
        if raw_data[length - i - 1]['angle'] == pre_last_angle:
            return {'raw_data': raw_data[length - i:],
                    'τ': data['τ'] if 'τ' in data else [None] * len(raw_data[0]['voltage'])}
    return {'raw_data': raw_data,
            'τ': data['τ'] if 'τ' in data else [None] * len(raw_data[0]['voltage'])}


def process(data, ch: int) -> (Dict, List[str], int):
    if ch < 0 or ch >= len(data['\u03c4']):
        raise ValueError('invalid channel value')
    angles_data = {}
    if 'raw_data' in data:
        raw_data = data['raw_data']
    else:
        raw_data = data
    _fields = [f'Angle h {a}' for a in sorted(item['angle']
                                              for item in raw_data if item['voltage'][ch])]
    for item in raw_data:
        if len(item['voltage'][ch]) > 0:
            angles_data[item['angle']] = sum(item['voltage'][ch]) / len(item['voltage'][ch])
        else:
            angles_data[item['angle']] = None
    angles_data = dict((f'Angle {i}', angles_data[i])
                       for i in sorted(angles_data))
    weather = {'WindDir': None, 'AvgWindSpeed': None, 'OutsideHum': None, 'OutsideTemp': None,
               'RainRate': None, 'UVLevel': None, 'SolarRad': None}
    for _d in raw_data:
        if 'weather' in _d:
            weather = _d['weather']
            break
    return {**dict(zip(fields, [
        datetime.fromtimestamp(raw_data[0]['timestamp']),
        data['\u03c4'][ch] if '\u03c4' in data else None,
        weather['WindDir'],
        weather['AvgWindSpeed'],
        weather['OutsideHum'],
        weather['OutsideTemp'],
        weather['RainRate'],
        weather['UVLevel'],
        weather['SolarRad'],
    ])), **angles_data}, _fields, len(data['\u03c4'])


def write_header(worksheet, header, text_format):
    for index, caption in enumerate(header):
        worksheet.write_string(0, index, caption, text_format)
    return


def write_row(worksheet, row: int, row_dict, keys):
    for key in keys:
        if key not in row_dict:
            return False
    for index, key in enumerate(keys):
        worksheet.write(row, index, row_dict[key])
    return True


def same_lists(list1: List, list2: List) -> bool:
    if len(list1) != len(list2):
        return False
    for i1, i2 in zip(list1, list2):
        if type(i1) != type(i2) or i1 != i2:
            return False
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


filenames: List[str] = []
for filename in args.files:
    filenames.extend(list_files(filename))
filenames.reverse()

results_file_name: str = args.output_prefix + '.xlsx'
if not args.ignore_existing and os.path.exists(results_file_name):
    exit(0)
workbook = None
channels: int = 1
written_rows = []
header_fields = []

if not args.anyway:
    new_files_given = False
    current_time = datetime.now().timestamp()
    for filename in filenames:
        if filename.endswith('.json.gz') and os.path.exists(filename) and os.path.isfile(filename):
            mod_time = os.path.getmtime(filename)
            if current_time - mod_time < 86400:
                new_files_given = True
                break
    if not new_files_given:
        # nothing to do
        exit(0)

initial_fields: Union[None, List[str]] = None

for filename in filenames:
    if filename.endswith('.json.gz') and os.path.exists(filename) and os.path.isfile(filename):
        with gzip.GzipFile(filename, 'r') as fin:
            content = fin.read().decode()
            json_data = preprocess(content)
            channel: int = 0
            while json_data is not None and channel < channels:
                d, f, channels = process(json_data, channel)
                if initial_fields is None:
                    initial_fields = f.copy()
                else:
                    if not same_lists(f, initial_fields):
                        break
                if 'Time' not in d:
                    raise RuntimeWarning(f'\'Time\' key is not found in the file {filename}')
                if workbook is None:
                    workbook = xlsxwriter.Workbook(results_file_name,
                                                   {'default_date_format': 'dd.mm.yyyy hh:mm:ss.000'})
                    header_format = workbook.add_format({'bold': True})
                if len(workbook.worksheets()) <= channel:
                    workbook.add_worksheet(f'Channel {channel + 1}')
                    if len(header_fields) <= channel:
                        header_fields.append(fields + f)
                    write_header(workbook.worksheets()[channel], header_fields[channel], header_format)
                    if len(written_rows) <= channel:
                        written_rows.append(1)
                if write_row(workbook.worksheets()[channel], written_rows[channel], d, header_fields[channel]):
                    written_rows[channel] += 1
                channel += 1

if workbook is not None:
    workbook.close()
    if args.send_email and config is not None:
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
            msg['Subject'] = 'Qara Dag Daily'
            body = 'Qara Dag data summary for ' + datetime.isoformat(datetime.now(), sep=" ")
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
