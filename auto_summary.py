#!/usr/bin/python3
# -*- coding: utf-8 -*-
import argparse
import configparser
import gzip
import json
import os.path
import re
import warnings
from collections import namedtuple
from datetime import datetime
from typing import Any, Dict, List, Union
# sending email
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import numpy as np
import xlsxwriter
from PyQt5.QtCore import QSettings
from xlsxwriter.format import Format
from xlsxwriter.utility import xl_col_to_name

CURRENT_TIME: float = datetime.now().timestamp()

DAY: float = 86400.
TIME_FIELD: str = 'Time'
GENERAL_FIELDS: List[str] = [TIME_FIELD]

WEATHER_FIELDS: List[str] = [
    'Wind Direction [°]',
    'Wind Speed',
    'Humidity [%]',
    'Temperature [°C]',
    'Rain Rate',
    'UV Level',
    'Solar Radiation',
]

PrincipialAngles = namedtuple('PrincipialAngles',
                              ['bb_angle',
                               'max_angle',
                               'min_angle', 'min_angle_alt',
                               'magic_angle', 'magic_angle_alt'])
PrincipialAnglesLabels = namedtuple('PrincipialAnglesLabels',
                                    ['bb_τ_label', 'bb_τ_label_alt',
                                     'leastsq_τ', 'leastsq_τ_error',
                                     'magic_angles_τ_label', 'magic_angles_τ_label_alt'])


def calculate_bb_τ(loop_data, *, min_angle: float, max_angle: float, bb_angle: float, precision: float = 5.):
    distance_to_max_angle: Union[None, float] = None
    distance_to_min_angle: Union[None, float] = None
    distance_to_bb_angle: Union[None, float] = None
    closest_to_bb_angle: Union[None, float] = None
    closest_to_max_angle: Union[None, float] = None
    closest_to_min_angle: Union[None, float] = None
    τ = np.nan
    for angle in loop_data:
        if abs(angle - max_angle) < precision and (distance_to_max_angle is None
                                                   or distance_to_max_angle > abs(angle - max_angle)):
            distance_to_max_angle = abs(angle - max_angle)
            closest_to_max_angle = angle
        if abs(angle - min_angle) < precision and (distance_to_min_angle is None
                                                   or distance_to_min_angle > abs(angle - min_angle)):
            distance_to_min_angle = abs(angle - min_angle)
            closest_to_min_angle = angle
        if abs(angle - bb_angle) < precision and (distance_to_bb_angle is None
                                                  or distance_to_bb_angle > abs(angle - bb_angle)):
            distance_to_bb_angle = abs(angle - bb_angle)
            closest_to_bb_angle = angle
    if closest_to_bb_angle is not None and closest_to_max_angle is not None \
            and closest_to_min_angle is not None and closest_to_max_angle != closest_to_min_angle:
        d0 = loop_data[closest_to_bb_angle]
        d1 = loop_data[closest_to_max_angle]
        d2 = loop_data[closest_to_min_angle]
        np.seterr(invalid='raise', divide='raise')
        try:
            if (d0 > d1 and d0 > d2) or (d0 < d1 and d0 < d2):
                τ = np.log((d0 - d1) / (d0 - d2)) / \
                    (1.0 / np.sin(np.radians(closest_to_min_angle))
                     - 1.0 / np.sin(np.radians(closest_to_max_angle)))
        finally:
            np.seterr(invalid='warn', divide='warn')
        # if np.isnan(τ):
        #     print('τ = ln(({d0} - {d1})/({d0} - {d2})) / (1/cos({θ2}°) - 1/cos({θ1}°))'.format(
        #         d0=d0,
        #         d1=d1,
        #         d2=d2,
        #         θ1=90 - closest_to_min_angle,
        #         θ2=90 - closest_to_max_angle))
    return τ


def calculate_leastsq_τ(loop_data) -> (float, float):
    h: np.ndarray = np.array(list(loop_data))
    d: np.ndarray = np.array([loop_data[a] for a in loop_data])
    if not any(d):
        return np.nan, np.nan
    d0: np.float64 = d[np.argmin(np.abs(h))]
    inverted: bool = np.count_nonzero(d0 > d) < np.count_nonzero(d0 < d)
    if inverted:
        good: np.ndarray = (h >= 15) & (d > d0)
    else:
        good: np.ndarray = (h >= 15) & (d0 > d)
    if not np.any(good):
        return np.nan, np.nan
    h = h[good]
    d = d[good]
    x = -1. / np.sin(np.deg2rad(h))
    if inverted:
        y = np.log(d - d0)
    else:
        y = np.log(d0 - d)
    with warnings.catch_warnings():
        warnings.filterwarnings('error')
        try:
            p = np.polyfit(x, y, deg=1)
        except np.RankWarning:
            return np.nan, np.nan
    error = np.sqrt(np.nanmean(np.square(np.polyval(p, x) - y)))
    return p[0], error


def best_magic_angle(h: np.ndarray, lower_angle: Union[int, float], higher_angle: Union[int, float]) -> (int, float):
    if isinstance(lower_angle, int):
        i: int = lower_angle
    else:
        i: int = int(np.argmin(np.abs(h - lower_angle)))
    if isinstance(higher_angle, int):
        k: int = higher_angle
    else:
        k: int = int(np.argmin(np.abs(h - higher_angle)))
    z_a: float = float(np.deg2rad(h[k]))
    h_a: float = float(np.deg2rad(h[i]))
    j: int = -1
    min_diff: float = 1.
    for _j in range(h.size):
        if _j in (i, k):
            continue
        np.seterr(invalid='raise', divide='raise')
        try:
            diff = np.abs(1. / np.sin(z_a) - 2. / np.sin(np.deg2rad(h[_j])) + 1. / np.sin(h_a))
        except FloatingPointError:
            continue
        finally:
            np.seterr(invalid='warn', divide='warn')
        if min_diff > diff:
            j = _j
            min_diff = diff
    return j, min_diff


def calculate_magic_angles_τ(loop_data, lower_angle: float, higher_angle: float) -> float:
    h: np.ndarray = np.array(list(loop_data))
    d: np.ndarray = np.array([loop_data[a] for a in loop_data])
    good: np.ndarray = (h >= 10)
    h = h[good]
    d = d[good]
    if not np.any(good):
        return np.nan
    k: int = int(np.argmin(np.abs(h - higher_angle)))
    i: int = int(np.argmin(np.abs(h - lower_angle)))
    if i == k:
        return np.nan
    j, min_diff = best_magic_angle(h, i, k)
    if min_diff > 0.02:
        return np.nan
    np.seterr(invalid='raise', divide='raise')
    τ = np.nan
    try:
        if d[i] < d[j] < d[k] or d[i] > d[j] > d[k]:
            τ = np.log((d[j] - d[k]) / (d[i] - d[j])) / \
                (1. / np.sin(np.deg2rad(h[i])) - 1. / np.sin(np.deg2rad(h[j])))
    finally:
        np.seterr(invalid='warn', divide='warn')
    # if np.isnan(τ):
    #     print('τ = ln(({d1} - {d0})/({d2} - {d1})) / (1/cos({θ2}°) - 1/cos({θ1}°))'.format(
    #         d0=d[k],
    #         d1=d[j],
    #         d2=d[i],
    #         θ1=90 - h[j],
    #         θ2=90 - h[i]))
    return τ


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
            return {'raw_data': [{'weather': data, 'angle': 90, 'voltage': [[]], **data}]}
    length = len(raw_data)
    if length > 2:
        pre_last_angle = raw_data[-2]['angle']
        for i in range(2, length):
            if raw_data[length - i - 1]['angle'] == pre_last_angle:
                return {'raw_data': raw_data[length - i:]}
    return {'raw_data': raw_data}


def process(data, ch: int, principial_angles: PrincipialAngles) \
        -> (Dict, List[str], PrincipialAnglesLabels, PrincipialAngles, int):
    if 'raw_data' in data:
        raw_data = data['raw_data']
    else:
        raw_data = data
    channels_count: int = len(raw_data[0]['voltage'])
    if ch < 0 or ch >= channels_count:
        raise ValueError('invalid channel number')

    angles_data: Dict[Union[str, float], Union[None, float]] = {}
    for item in raw_data:
        if len(item['voltage'][ch]) > 0:
            angles_data[item['angle']] = sum(item['voltage'][ch]) / len(item['voltage'][ch])
        else:
            angles_data[item['angle']] = None
    al, ic2pa, ac2pa = get_absorption_labels(dict((i, angles_data[i]) for i in sorted(angles_data)),
                                             principial_angles)
    _fields = list(al)
    if any(angles_data.values()):
        leastsq_τ = calculate_leastsq_τ(angles_data)
        absorptions = {
            al.bb_τ_label: calculate_bb_τ(angles_data,
                                          min_angle=principial_angles.min_angle,
                                          max_angle=principial_angles.max_angle,
                                          bb_angle=principial_angles.bb_angle),
            al.bb_τ_label_alt: calculate_bb_τ(angles_data,
                                              min_angle=principial_angles.min_angle_alt,
                                              max_angle=principial_angles.max_angle,
                                              bb_angle=principial_angles.bb_angle),
            al.leastsq_τ: leastsq_τ[0],
            al.leastsq_τ_error: leastsq_τ[1],
            al.magic_angles_τ_label: calculate_magic_angles_τ(angles_data,
                                                              lower_angle=principial_angles.min_angle,
                                                              higher_angle=principial_angles.max_angle),
            al.magic_angles_τ_label_alt: calculate_magic_angles_τ(angles_data,
                                                                  lower_angle=principial_angles.min_angle_alt,
                                                                  higher_angle=principial_angles.max_angle)
        }
    else:
        absorptions = dict()
    # rename `angles_data` keys
    # TODO: avoid repeating
    angles_data = dict((f'θ = {90 - i}°', angles_data[i])
                       for i in sorted(angles_data))
    _fields.extend(angles_data.keys())

    weather: Dict[str, Union[None, str, int, float]] = {'WindDir': None, 'AvgWindSpeed': None, 'OutsideHum': None,
                                                        'OutsideTemp': None, 'RainRate': None, 'UVLevel': None,
                                                        'SolarRad': None}
    for _d in raw_data:
        if 'weather' in _d:
            weather = _d['weather']
            _fields.extend(WEATHER_FIELDS)
            break

    arduino_state: Dict[str, Union[int, float, bool]] = dict()
    for _d in raw_data:
        if 'temperatures' in _d:
            for index, value in enumerate(_d['temperatures']):
                _name: str = f'Temperature {index + 1}'
                arduino_state[_name] = value
                _fields.append(_name)
            break
    for _d in raw_data:
        if 'states' in _d:
            for index, value in enumerate(_d['states']):
                _name = f'Relay State {index + 1}'
                arduino_state[_name] = value
                _fields.append(_name)
        break
    for _d in raw_data:
        if 'setpoints' in _d:
            for index, value in enumerate(_d['setpoints']):
                _name = f'Setpoint {index + 1}'
                arduino_state[_name] = value
                _fields.append(_name)
            break
    for _d in raw_data:
        if 'enabled' in _d:
            _name = f'Auto Relay Mode'
            arduino_state[_name] = _d['enabled']
            _fields.append(_name)
            break

    return {TIME_FIELD: datetime.fromtimestamp(raw_data[0]['timestamp']),
            **absorptions,
            **dict(zip(WEATHER_FIELDS, [
                weather['WindDir'],
                weather['AvgWindSpeed'],
                weather['OutsideHum'],
                weather['OutsideTemp'],
                weather['RainRate'],
                weather['UVLevel'],
                weather['SolarRad'],
            ])),
            **angles_data,
            **arduino_state
            }, _fields, al, ic2pa, ac2pa, channels_count


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


def list_files(path, *, max_age: float = -1.):
    files: List[str] = []
    if os.path.isdir(path):
        for file in os.listdir(path):
            if os.path.isfile(os.path.join(path, file)):
                ok: bool = True
                if max_age > 0.:
                    mod_time: float = os.path.getmtime(os.path.join(path, file))
                    if CURRENT_TIME - mod_time > max_age:
                        ok = False
                if ok:
                    files.append(os.path.join(path, file))
            elif os.path.isdir(os.path.join(path, file)):
                files.extend(list_files(os.path.join(path, file)))
    elif os.path.isfile(path):
        files.append(path)
    return files


def take_screenshot() -> bytes:
    from PyQt5.QtWidgets import QApplication
    from PyQt5.Qt import QBuffer, QIODevice
    app = QApplication([])
    buffer = QBuffer()
    buffer.open(QIODevice.ReadWrite)
    app.primaryScreen().grabWindow(app.desktop().winId()).save(buffer, 'png')
    buffer.seek(0)
    data: bytes = buffer.readAll().data()
    buffer.close()
    del app
    return data


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
                part.add_header('Content-Disposition', 'attachment', filename=os.path.split(results_file_name)[-1])
                msg.attach(part)

                screenshot: bytes = take_screenshot()
                if screenshot:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(screenshot)
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition', 'attachment', filename='screenshot.png')
                    msg.attach(part)

                server = smtplib.SMTP(server, port)
                server.starttls()
                server.login(sender, password)
                server.sendmail(sender, cc + [sender], msg.as_string())
                server.quit()


def check_new_files_given(filenames: List[str], timeout: float = DAY) -> bool:
    new_files_given = False
    for filename in filenames:
        if filename.endswith('.json.gz') and os.path.exists(filename) and os.path.isfile(filename):
            mod_time: float = os.path.getmtime(filename)
            if CURRENT_TIME - mod_time < timeout:
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


def get_principial_angles() -> PrincipialAngles:
    settings = QSettings("SavSoft", "Crimea Radiometer")

    return PrincipialAngles(
        bb_angle=get_config_value(settings, key='black body position', default=0, _type=float),
        max_angle=get_config_value(settings, key='zenith position', default=90, _type=float),
        min_angle=get_config_value(settings, key='horizon position', default=15, _type=float),
        min_angle_alt=get_config_value(settings, key='horizon position alt', default=20, _type=float),
        magic_angle=np.nan,
        magic_angle_alt=np.nan,
    )


def get_indices_closest_to_principial_angles(angles_data: Dict[float, float],
                                             principial_angles: PrincipialAngles) \
        -> PrincipialAngles:
    h: np.ndarray = np.array(list(angles_data))
    max_angle = int(np.argmin(np.abs(h - principial_angles.max_angle)))
    min_angle = int(np.argmin(np.abs(h - principial_angles.min_angle)))
    min_angle_alt = int(np.argmin(np.abs(h - principial_angles.min_angle_alt)))
    return PrincipialAngles(
        bb_angle=int(np.argmin(np.abs(h - principial_angles.bb_angle))),
        max_angle=max_angle,
        min_angle=min_angle,
        min_angle_alt=min_angle_alt,
        magic_angle=best_magic_angle(h, h[min_angle], h[max_angle])[0],
        magic_angle_alt=best_magic_angle(h, h[min_angle_alt], h[max_angle])[0],
    )


def get_absorption_labels(angles_data: Dict[float, float], principial_angles: PrincipialAngles) \
        -> (PrincipialAnglesLabels, PrincipialAngles):
    """ :returns absorption labels and the angles used in the labels"""
    h: np.ndarray = np.array(list(angles_data))
    ic2pa: PrincipialAngles = get_indices_closest_to_principial_angles(angles_data, principial_angles)
    ac2pa: PrincipialAngles = PrincipialAngles(**dict(zip(ic2pa._fields, h[list(ic2pa)])))
    return PrincipialAnglesLabels(
        bb_τ_label=f'τ for θ = {90 - ac2pa.bb_angle}, '
                   f'{90 - ac2pa.min_angle}, {90 - ac2pa.max_angle}',
        bb_τ_label_alt=f'τ for θ = {90 - ac2pa.bb_angle}, '
                       f'{90 - ac2pa.min_angle_alt}, {90 - ac2pa.max_angle}',
        leastsq_τ='leastsq τ',
        leastsq_τ_error='leastsq τ error',
        magic_angles_τ_label=''
                             f'τ for θ = {90 - ac2pa.min_angle}, '
                             f'{90 - h[best_magic_angle(h, ac2pa.min_angle, ac2pa.max_angle)[0]]}, '
                             f'{90 - ac2pa.max_angle}',
        magic_angles_τ_label_alt=''
                                 f'τ for θ = {90 - ac2pa.min_angle_alt}, '
                                 f'{90 - h[best_magic_angle(h, ac2pa.min_angle_alt, ac2pa.max_angle)[0]]}, '
                                 f'{90 - ac2pa.max_angle}',
    ), ic2pa, ac2pa


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
                    default='results_' + datetime.date(datetime.now()).isoformat())
    ap.add_argument('-m', '--max-age', help='maximal age of files to take into account (in days)',
                    default=-1., type=float)
    ap.add_argument('files', metavar='PATH', nargs='+', help='path to a file to process')
    args = ap.parse_args()

    results_file_name: str = args.output_prefix + '.xlsx'
    # print(results_file_name)
    if not args.ignore_existing and os.path.exists(results_file_name):
        exit(0)

    filenames: List[str] = []
    for filename in args.files:
        filenames.extend(list_files(filename, max_age=args.max_age * DAY))
    filenames.sort(key=lambda fn: os.path.basename(fn), reverse=True)

    if not args.anyway and not check_new_files_given(filenames):
        # nothing to do
        exit(0)

    principial_angles: PrincipialAngles = get_principial_angles()

    workbook = None
    written_rows: List[int] = []
    header_fields: List[List[str]] = []
    initial_fields: Union[None, List[str]] = None

    for filename in filenames:
        if filename.endswith('.json.gz') and os.path.exists(filename) and os.path.isfile(filename):
            # print(filename)
            with gzip.GzipFile(filename, 'r') as fin:
                content = fin.read().decode()
                json_data = preprocess(content)
                channels: int = 1
                channel: int = 0
                while json_data is not None and channel < channels:
                    d, f, al, ic2pa, ac2pa, channels = process(json_data, channel, principial_angles)
                    lal = list(al)
                    # print(f)
                    if initial_fields is None:
                        initial_fields = f.copy()
                    else:
                        if not same_lists(f, initial_fields):
                            d = fit_dict(d, GENERAL_FIELDS + initial_fields)

                    absorptions = fit_dict(d, lal)
                    if not any(absorptions.values()):
                        channel += 1
                        continue

                    if TIME_FIELD not in d:
                        raise RuntimeWarning(f'\'{TIME_FIELD}\' key is not found in the file {filename}')

                    if workbook is None:
                        workbook = xlsxwriter.Workbook(results_file_name,
                                                       {'default_date_format': 'dd.mm.yyyy hh:mm:ss'})
                        header_format: Format = workbook.add_format({'bold': True})
                    if len(workbook.worksheets()) <= channel:
                        workbook.add_worksheet(f'Channel {channel + 1}')
                        if len(header_fields) <= channel:
                            header_fields.append(GENERAL_FIELDS + initial_fields)
                        write_header(workbook.worksheets()[channel], header_fields[channel], header_format)
                        workbook.worksheets()[channel].freeze_panes(1, 1)  # freeze first row and first column
                        if len(written_rows) <= channel:
                            written_rows.append(1)

                    if write_row(workbook.worksheets()[channel], written_rows[channel], d, header_fields[channel]):
                        # for bb_τ_label
                        formula: str = '=LN((${d0_c}{row} - ${d2_c}{row})/(${d0_c}{row} - ${d1_c}{row})) ' \
                                       '/ (1/COS(RADIANS({θ1})) - 1/COS(RADIANS({θ2})))'\
                            .format(d0_c=xl_col_to_name(len(GENERAL_FIELDS) + len(lal) + ic2pa.bb_angle),
                                    d1_c=xl_col_to_name(len(GENERAL_FIELDS) + len(lal) + ic2pa.min_angle),
                                    d2_c=xl_col_to_name(len(GENERAL_FIELDS) + len(lal) + ic2pa.max_angle),
                                    row=written_rows[channel]+1,
                                    θ1=90 - ac2pa.min_angle,
                                    θ2=90 - ac2pa.max_angle)
                        # print(formula)
                        label: str = al.bb_τ_label
                        if absorptions[label] is not None and not np.isnan(absorptions[label]):
                            workbook.worksheets()[channel].write_formula(
                                written_rows[channel],
                                len(GENERAL_FIELDS) + lal.index(label),
                                formula,
                                value=absorptions[label])
                        # for bb_τ_label_alt
                        formula: str = '=LN((${d0_c}{row} - ${d2_c}{row})/(${d0_c}{row} - ${d1_c}{row})) ' \
                                       '/ (1/COS(RADIANS({θ1})) - 1/COS(RADIANS({θ2})))'\
                            .format(d0_c=xl_col_to_name(len(GENERAL_FIELDS) + len(lal) + ic2pa.bb_angle),
                                    d1_c=xl_col_to_name(len(GENERAL_FIELDS) + len(lal) + ic2pa.min_angle_alt),
                                    d2_c=xl_col_to_name(len(GENERAL_FIELDS) + len(lal) + ic2pa.max_angle),
                                    row=written_rows[channel]+1,
                                    θ1=90 - ac2pa.min_angle_alt,
                                    θ2=90 - ac2pa.max_angle)
                        # print(formula)
                        label: str = al.bb_τ_label_alt
                        if absorptions[label] is not None and not np.isnan(absorptions[label]):
                            workbook.worksheets()[channel].write_formula(
                                written_rows[channel],
                                len(GENERAL_FIELDS) + lal.index(label),
                                formula,
                                value=absorptions[label])
                        # for magic_angles_τ_label
                        formula: str = '=LN((${d2_c}{row} - ${d3_c}{row})/(${d1_c}{row} - ${d2_c}{row})) ' \
                                       '/ (1/COS(RADIANS({θ1})) - 1/COS(RADIANS({θ2})))'\
                            .format(d1_c=xl_col_to_name(len(GENERAL_FIELDS) + len(lal) + ic2pa.min_angle),
                                    d2_c=xl_col_to_name(len(GENERAL_FIELDS) + len(lal) + ic2pa.magic_angle),
                                    d3_c=xl_col_to_name(len(GENERAL_FIELDS) + len(lal) + ic2pa.max_angle),
                                    row=written_rows[channel]+1,
                                    θ1=90 - ac2pa.min_angle,
                                    θ2=90 - ac2pa.magic_angle)
                        # print(formula)
                        label: str = al.magic_angles_τ_label
                        if absorptions[label] is not None and not np.isnan(absorptions[label]):
                            workbook.worksheets()[channel].write_formula(
                                written_rows[channel],
                                len(GENERAL_FIELDS) + lal.index(label),
                                formula,
                                value=absorptions[label])
                        # for magic_angles_τ_label_alt
                        formula: str = '=LN((${d2_c}{row} - ${d3_c}{row})/(${d1_c}{row} - ${d2_c}{row})) ' \
                                       '/ (1/COS(RADIANS({θ1})) - 1/COS(RADIANS({θ2})))'\
                            .format(d1_c=xl_col_to_name(len(GENERAL_FIELDS) + len(lal) + ic2pa.min_angle_alt),
                                    d2_c=xl_col_to_name(len(GENERAL_FIELDS) + len(lal) + ic2pa.magic_angle_alt),
                                    d3_c=xl_col_to_name(len(GENERAL_FIELDS) + len(lal) + ic2pa.max_angle),
                                    row=written_rows[channel]+1,
                                    θ1=90 - ac2pa.min_angle_alt,
                                    θ2=90 - ac2pa.magic_angle_alt)
                        # print(formula)
                        label: str = al.magic_angles_τ_label_alt
                        if absorptions[label] is not None and not np.isnan(absorptions[label]):
                            workbook.worksheets()[channel].write_formula(
                                written_rows[channel],
                                len(GENERAL_FIELDS) + lal.index(label),
                                formula,
                                value=absorptions[label])

                        written_rows[channel] += 1

                    channel += 1

    # print('data collected')
    if workbook is not None:
        workbook.close()
        if args.send_email and any(written_rows):
            send_email(args.config, results_file_name)


if __name__ == '__main__':
    main()
