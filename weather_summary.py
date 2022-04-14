#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import configparser
import gzip
import json
import os.path
import re
from datetime import datetime
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple, Union

# sending email
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

CURRENT_TIME: float = datetime.now().timestamp()

DAY: float = 86400.
TIME_FIELD: str = 'Time'
GENERAL_FIELDS: List[str] = [TIME_FIELD]

EXCLUDED_WEATHER_FIELDS: List[str] = [
    'time',
    'timestamp',
    'PacketType',
    'NextRec',
    'BarometerTrend',
    'SoilMoist',
    'LeafWet',
    'AlarmInside',
    'AlarmRain',
    'AlarmOut',
    'AlarmSL',
    'XmitBatt',
    'ForecastIcon',
]


class TableWriter:
    def __init__(self, file_name: str, sep: str = '\t', date_format: str = '%Y-%m-%dT%H:%M:%S.%f'):
        self.sep: str = sep
        self.date_format: str = date_format

        self._file_name: str = file_name
        if os.path.exists(self._file_name):
            with open(self._file_name, 'wt'):
                pass

    def write_row(self, values: Iterable[Any]):
        strings: List[str] = []
        for value in values:
            if value is None:
                strings.append('')
            elif isinstance(value, str):
                strings.append(value)
            elif isinstance(value, datetime):
                strings.append(value.strftime(self.date_format))
            else:
                strings.append(repr(value))
        with open(self._file_name, 'at') as f_out:
            f_out.write(self.sep.join(strings) + '\n')


def preprocess(text) -> Optional[Dict[str, List[Dict[str, Union[str, float, int, List[int]]]]]]:
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


def process(data) -> Iterator[Tuple[Dict, List[str]]]:
    def get_weather(timestamp: float, weather_dict: Dict):
        weather = dict((key, value)
                       for key, value in weather_dict.items()
                       if not isinstance(value, list) and key not in EXCLUDED_WEATHER_FIELDS)
        if 'Barometer' not in weather or not weather['Barometer']:
            weather['Barometer'] = None
        elif weather['Barometer'] > 1000:
            weather['Barometer'] = weather['Barometer'] * 0.0254
        for key in weather:
            if ('Rain' in key or 'ET' in key) and weather[key] is not None:
                weather[key] *= 25.4
        for key in ('Barometer', 'InsideTemp', 'OutsideTemp', 'ETDay', 'ETMonth', 'ETYear', 'BattLevel'):
            if weather[key] is not None:
                weather[key] = round(weather[key], 1)
        # move Forecast to the end
        fc: str = weather['Forecast']
        del weather['Forecast']
        weather['Forecast'] = fc

        _fields = list(weather.keys())
        return {
                   TIME_FIELD: datetime.fromtimestamp(timestamp),
                   **weather,
               }, _fields

    if 'raw_data' in data:
        raw_data = data['raw_data']
        for _d in reversed(raw_data):
            if 'weather' in _d:
                yield get_weather(_d['timestamp'], _d['weather'])
    else:
        yield get_weather(data['timestamp'], data)


def write_row(worksheet: TableWriter, row_dict: Dict, keys: List):
    for key in keys:
        if key not in row_dict:
            return False
    worksheet.write_row([row_dict[key] for key in keys])
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


def list_files(path, *, max_age: float = -1., suffix: str = '') -> List[str]:
    files: List[str] = []
    if os.path.isdir(path):
        for file in os.listdir(path):
            full_path: str = os.path.join(path, file)
            files.extend(list_files(full_path, max_age=max_age, suffix=suffix))
    elif os.path.isfile(path) and (not suffix or path.endswith(suffix)):
        new_enough: bool = True
        if max_age > 0.:
            mod_time: float = os.path.getmtime(path)
            if CURRENT_TIME - mod_time > max_age:
                new_enough = False
        if new_enough:
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


def check_new_files_given(filenames: List[str], timeout: float = DAY) -> bool:
    new_files_given = False
    current_time = datetime.now().timestamp()
    for filename in filenames:
        if filename.endswith('.json.gz') and os.path.exists(filename) and os.path.isfile(filename):
            mod_time = os.path.getmtime(filename)
            if current_time - mod_time < timeout:
                new_files_given = True
                break
    return new_files_given


def main():
    ap = argparse.ArgumentParser(description='extracts summary from raw data and writes it into an CSV file')
    ap.add_argument('-I', '--ignore-existing', help='skip check whether the result file exists',
                    action='store_true', default=False)
    ap.add_argument('-c', '--config', help='configuration file', default=os.path.splitext(__file__)[0] + '.ini')
    ap.add_argument('-e', '--send-email', help='email the result file to the recipients listed in config',
                    action='store_true', default=False)
    ap.add_argument('-m', '--max-age', help='maximal age of files to take into account (in days)',
                    default=-1., type=float)
    ap.add_argument('-a', '--anyway', help='process files even if no new files given (younger than a day)',
                    action='store_true', default=False)
    ap.add_argument('-o', '--output-prefix', help='prefix for the result files',
                    default='weather_' + datetime.date(datetime.now()).isoformat())
    ap.add_argument('files', metavar='PATH', nargs='+', help='path to a file to process')
    args = ap.parse_args()

    results_file_name: str = args.output_prefix + '.csv'
    # print(results_file_name)
    if not args.ignore_existing and os.path.exists(results_file_name):
        exit(0)

    index: int
    filename: str
    filenames: List[str] = []
    for filename in args.files:
        filenames.extend(list_files(filename, max_age=args.max_age * DAY, suffix='.json.gz'))

    def sorting_key(_fn: str) -> str:
        bn = os.path.basename(_fn)
        return bn if '-' not in bn else bn[bn.index('-') + 1:]  # hotfix; should be sorting by the timestamp

    filenames.sort(key=sorting_key, reverse=True)

    if not args.anyway and not check_new_files_given(filenames):
        # nothing to do
        exit(0)

    writer: TableWriter = TableWriter(results_file_name)
    header_fields: List[str] = []
    initial_fields: List[str] = []

    for index, filename in enumerate(filenames):
        if os.path.exists(filename) and os.path.isfile(filename):
            print(f'{(index + 1) / len(filenames):.2%}\t{filename}')
            with gzip.GzipFile(filename, 'r') as fin:
                content = fin.read().decode()
                json_data = preprocess(content)
                if json_data is not None:
                    for d, f in process(json_data):
                        # print(f)
                        if not initial_fields:
                            initial_fields = f.copy()
                        else:
                            if not same_lists(f, initial_fields):
                                d = fit_dict(d, GENERAL_FIELDS + initial_fields)

                        if not any(fit_dict(d, initial_fields).values()):
                            continue

                        if TIME_FIELD not in d:
                            raise RuntimeWarning(f'\'{TIME_FIELD}\' key is not found in the file {filename}')

                        if not header_fields:
                            header_fields = GENERAL_FIELDS + initial_fields
                            writer.write_row(header_fields)

                        write_row(writer, d, header_fields)

    if args.send_email and header_fields:
        send_email(args.config, results_file_name)


if __name__ == '__main__':
    main()
