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
from typing import List, Dict, Union, Any

import numpy as np
import xlsxwriter
from xlsxwriter.format import Format

TIME_FIELD: str = 'Time'
GENERAL_FIELDS: List[str] = [TIME_FIELD]

EXCLUDED_WEATHER_FIELDS: List[str] = [
    'time',
    'timestamp',
    'PacketType',
    'SoilMoist',
    'LeafWet',
    'AlarmInside',
    'AlarmRain',
    'AlarmOut',
    'AlarmSL',
    'XmitBatt',
]


def preprocess(text):
    try:
        data = json.loads(text)
    except json.decoder.JSONDecodeError:
        return None
    if 'raw_data' in data:
        raw_data = data['raw_data']
    else:
        if isinstance(data, list):
            raw_data = data
        else:
            return {'raw_data': [{'weather': data, **data}]}
    length = len(raw_data)
    if length > 2:
        pre_last_angle = raw_data[-2]['angle']
        for i in range(2, length):
            if raw_data[length - i - 1]['angle'] == pre_last_angle:
                return {'raw_data': raw_data[length - i:]}
    return {'raw_data': raw_data}


def process(data) -> (Dict, List[str], int):
    raw_data = data['raw_data']
    _fields = list()
    weather: Dict[str, Union[None, str, int, float, List[int]]] = dict()
    for _d in raw_data:
        if 'weather' in _d:
            weather = dict((key, value)
                           for key, value in _d['weather'].items()
                           if not isinstance(value, list) and key not in EXCLUDED_WEATHER_FIELDS)
            _fields = list(weather.keys())
            break

    return {TIME_FIELD: datetime.fromtimestamp(raw_data[0]['timestamp']),
            **weather,
            }, _fields


def write_header(worksheet, header: List[str], text_format: Format):
    for index, caption in enumerate(header):
        worksheet.write_string(0, index, caption, text_format)


def write_row(worksheet, row: int, row_dict: Dict, keys: List):
    for key in keys:
        if key not in row_dict:
            return False
    for index, key in enumerate(keys):
        if isinstance(row_dict[key], float) and np.isnan(row_dict[key]):
            worksheet.write(row, index, None)
        else:
            if isinstance(row_dict[key], tuple):
                print(key, row_dict[key])
            worksheet.write(row, index, row_dict[key])
    return True


def same_lists(list1: List, list2: List) -> bool:
    if len(list1) != len(list2):
        return False
    for i1, i2 in zip(list1, list2):
        if type(i1) != type(i2) or i1 != i2:
            return False
    return True


def fit_dict(_d: Dict, keys: List, default: Any = None) -> Dict:
    new_dict: Dict = dict((k, default) for k in keys)
    for key, value in _d.items():
        if key in keys:
            new_dict[key] = value
    return new_dict


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
    return files


def send_email(config_name: str, results_file_name: str):
    if os.path.exists(config_name):
        config = configparser.ConfigParser()
        config.read(config_name)
    else:
        return

    if config is not None:
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


def check_new_files_given(filenames: List[str], timeout: float = 86400) -> bool:
    new_files_given = False
    current_time = datetime.now().timestamp()
    for filename in filenames:
        if filename.endswith('.json.gz') and os.path.exists(filename) and os.path.isfile(filename):
            mod_time = os.path.getmtime(filename)
            if current_time - mod_time < timeout:
                new_files_given = True
                break
    return new_files_given


def get_config_value(settings, *, section='settings', key, default, _type) -> Union[bool, int, float, str]:
    if section not in settings.childGroups():
        return default
    settings.beginGroup(section)
    try:
        v = settings.value(key, default, _type)
        # print('get', section, key, v, _type)
    except TypeError:
        v = default
        # print('get', section, key, v, '(default)', _type)
    settings.endGroup()
    return v


def main():
    ap = argparse.ArgumentParser(description='extracts summary from raw data and writes it into an XLSX file')
    ap.add_argument('-I', '--ignore-existing', help='skip check whether the result file exists',
                    action='store_true', default=False)
    ap.add_argument('-c', '--config', help='configuration file', default=os.path.splitext(__file__)[0] + '.ini')
    ap.add_argument('-e', '--send-email', help='email the result file to the recipients listed in config',
                    action='store_true', default=False)
    ap.add_argument('-a', '--anyway', help='process files even if no new files given (younger than a day)',
                    action='store_true', default=False)
    ap.add_argument('-o', '--output-prefix', help='prefix for the result files',
                    default='weather_' + datetime.date(datetime.now()).isoformat())
    ap.add_argument('files', metavar='PATH', nargs='+', help='path to a file to process')
    args = ap.parse_args()

    results_file_name: str = args.output_prefix + '.xlsx'
    # print(results_file_name)
    if not args.ignore_existing and os.path.exists(results_file_name):
        exit(0)

    filenames: List[str] = []
    for filename in args.files:
        filenames.extend(list_files(filename))

    def sorting_key(_fn: str) -> str:
        bn = os.path.basename(_fn)
        return bn if '-' not in bn else bn[bn.index('-') + 1:]  # hotfix; should be sorting by the timestamp

    filenames.sort(key=sorting_key, reverse=True)

    if not args.anyway and not check_new_files_given(filenames):
        # nothing to do
        exit(0)

    workbook = None
    worksheet = None
    written_rows: int = 0
    header_fields: List[str] = []
    initial_fields: Union[None, List[str]] = None

    for filename in filenames:
        if filename.endswith('.json.gz') and os.path.exists(filename) and os.path.isfile(filename):
            # print(filename)
            with gzip.GzipFile(filename, 'r') as fin:
                content = fin.read().decode()
                json_data = preprocess(content)
                if json_data is not None:
                    d, f = process(json_data)
                    # print(f)
                    if initial_fields is None:
                        initial_fields = f.copy()
                    else:
                        if not same_lists(f, initial_fields):
                            d = fit_dict(d, GENERAL_FIELDS + initial_fields)

                    if TIME_FIELD not in d:
                        raise RuntimeWarning(f'\'{TIME_FIELD}\' key is not found in the file {filename}')

                    if workbook is None:
                        workbook = xlsxwriter.Workbook(results_file_name,
                                                       {'default_date_format': 'dd.mm.yyyy hh:mm:ss'})
                        header_format: Format = workbook.add_format({'bold': True})
                    if worksheet is None:
                        worksheet = workbook.add_worksheet(f'Weather')
                        worksheet.freeze_panes(1, 1)  # freeze first row and first column
                        header_fields = GENERAL_FIELDS + initial_fields
                        write_header(worksheet, header_fields, header_format)
                        written_rows = 1

                    if write_row(worksheet, written_rows, d, header_fields):
                        written_rows += 1

    if workbook is not None:
        workbook.close()
        if args.send_email and written_rows:
            send_email(args.config, results_file_name)


if __name__ == '__main__':
    main()
