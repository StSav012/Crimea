#!/usr/bin/python3
# -*- coding: utf-8 -*-
import sys
import os.path
import json
import gzip
import xlsxwriter
from datetime import datetime
import argparse
import configparser
import urllib.request
import io
import zipfile
# from numpy import radians, array, unique
# from matplotlib import pyplot as plt
# from windrose import wrscatter  # , wrbar, wrcontourf

# sending email
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

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


ap = argparse.ArgumentParser(description='extracts summary from raw data and writes it into an XLSX file',
                             epilog='ISO format means ‘YYYY-MM-DD[*HH[:MM[:SS[.mmm[mmm]]]][+HH:MM[:SS[.ffffff]]]]’, '
                                    'where ‘*’ matches any single symbol'
                             if sys.version_info >= (3, 7) else
                             'ISO format means ‘YYYY-MM-DD[THH[:MM[:SS[.mmmmmm]]][+HHMM[SS]]’, '
                             'where ‘T’ means literal ‘T‘ character')
ap.add_argument('--from', help='time moment to extract the data from (ISO format)',
                default=None, dest='from_', metavar='FROM')
ap.add_argument('--to', help='time moment to extract the data to (ISO format)', default=None)
ap.add_argument('-I', '--ignore-existing', help='skip check whether the result file exists',
                action='store_true', default=False)
ap.add_argument('-c', '--config', help='configuration file', default=f'{os.path.splitext(__file__)[0]}.ini')
ap.add_argument('-e', '--send-email', help='email the result file to the recipients listed in config',
                action='store_true', default=False)
ap.add_argument('-o', '--output-prefix', help='prefix for the result file, without an extension', required=True)
args = ap.parse_args()

config = configparser.ConfigParser()
config.read(args.config)

if sys.version_info >= (3, 7):
    time_from = datetime.fromisoformat(args.from_) if args.from_ else None
    time_to = datetime.fromisoformat(args.to) if args.to else None
else:
    formats = [
            '%Y-%m-%dT%H:%M:%S.%f%z',
            '%Y-%m-%dT%H:%M:%S%z',
            '%Y-%m-%dT%H:%M%z',
            '%Y-%m-%dT%H%z',
            '%Y-%m-%d%z',
            '%Y-%m-%dT%H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M',
            '%Y-%m-%dT%H',
            '%Y-%m-%d',
            ]
    time_from = None
    if args.from_ is not None:
        for tf in formats:
            try:
                time_from = datetime.strptime(args.from_, tf)
            except ValueError:
                pass
            else:
                break
    time_to = None
    if args.to is not None:
        for tf in formats:
            try:
                time_to = datetime.strptime(args.to, tf)
            except ValueError:
                pass
            else:
                break


def preprocess(text):
    try:
        data = json.loads(text)
    except json.decoder.JSONDecodeError:
        return None
    # print([_d['angle'] for _d in data['raw_data']])
    if 'raw_data' in data:
        raw_data = data['raw_data']
    else:
        raw_data = data
    pre_last_angle = raw_data[-2]['angle'] if len(raw_data) > 2 else None
    length = len(raw_data)
    for i in range(2, length):
        if raw_data[length-i-1]['angle'] == pre_last_angle:
            return {'raw_data': raw_data[length-i:],
                    'τ': data['τ'] if 'τ' in data else [None] * len(raw_data[0]['voltage'])}
    #     else:
    #         print(raw_data[length-i-1]['angle'], pre_last_angle, end='\t')
    # print('')
    return {'raw_data': raw_data,
            'τ': data['τ'] if 'τ' in data else [None] * len(raw_data[0]['voltage'])}


def process(data, ch):
    if ch < 0 or ch >= len(data['\u03c4']):
        raise ValueError('invalid channel value')
    angles_data = {}
    if 'raw_data' in data:
        raw_data = data['raw_data']
    else:
        raw_data = data
    for a in raw_data:
        angles_data[a['angle']] = sum(a['voltage'][ch]) / len(a['voltage'][ch])
    angles_data = dict(('Angle {}'.format(i), angles_data[i])
                       for i in sorted(angles_data))
    _fields = ['Angle {}'.format(a) for a in sorted(item['angle'] for item in raw_data)]
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


def write_row(worksheet, row, row_dict, keys):
    for key in keys:
        if key not in row_dict:
            print('wrong keys:', list(row_dict), end='\t')
            print('missing', key, end='\t')
            return False
    for index, key in enumerate(keys):
        worksheet.write(row, index, row_dict[key])
    return True


# ws = []
# wd = []

results_file_name = '{prefix}.xlsx'.format(prefix=args.output_prefix)
if not args.ignore_existing and os.path.exists(results_file_name):
    print(f'file already exists: {results_file_name}')
    exit(0)
workbook = None
channels = 1
written_rows = []
header_fields = []

url = 'https://www.dropbox.com/sh/p5vsfazrqbv72cn/AABHqtRFiQFdLECPaXIJnNN1a?dl=1'
print('downloading...')
response = urllib.request.urlopen(url)
zip_archive = response.read()
z = zipfile.ZipFile(io.BytesIO(zip_archive))

for filename in z.namelist():
    if filename.endswith('.json.gz'):
        print('file', filename, end='\t', flush=True)
        with gzip.GzipFile(fileobj=io.BytesIO(z.read(filename)), mode='r') as fin:
            content = fin.read().decode()
            json_data = preprocess(content)
            channel = 0
            processed = False
            while json_data is not None and channel < channels:
                d, f, channels = process(json_data, channel)
                # print(f)
                # f = [f[index] for index in sorted(unique(f, return_index=True)[1])]
                # if d['Wind Speed'] is not None and d['Wind Direction [°]'] is not None:
                #     ws.append(d['Wind Speed'])
                #     wd.append(radians(d['Wind Direction [°]']))
                if 'Time' not in d:
                    raise RuntimeWarning(f'\'Time\' key is not found in the file {filename}')
                if ('Time' not in d) or (
                        (time_from is None or time_from <= d['Time']) and (time_to is None or d['Time'] <= time_to)):
                    if workbook is None:
                        workbook = xlsxwriter.Workbook(results_file_name,
                                                       {'default_date_format': 'dd.mm.yyyy hh:mm:ss.000'})
                        header_format = workbook.add_format({'bold': True})
                    if len(workbook.worksheets()) <= channel:
                        workbook.add_worksheet('Channel {channel}'.format(channel=channel+1))
                        if len(header_fields) <= channel:
                            header_fields.append(fields+f)
                        write_header(workbook.worksheets()[channel], header_fields[channel], header_format)
                        if len(written_rows) <= channel:
                            written_rows.append(1)
                    if write_row(workbook.worksheets()[channel], written_rows[channel], d, header_fields[channel]):
                        written_rows[channel] += 1
                    processed = True
                channel += 1
            print('processed' if processed else 'discarded')
z.close()
if workbook is not None:
    print('saving...', end='\t', flush=True)
    workbook.close()
    print('done')
    if args.send_email:
        print('sending e-mail...', end='\t', flush=True)
        server = config.get('email', 'login', fallback='')
        port = config.getint('email', 'port', fallback=0)
        sender = config.get('email', 'login', fallback='')
        password = config.get('email', 'password', fallback='')
        cc = config.get('email', 'recipients', fallback='').splitlines()
        # cc = ['bubn10@mail.ru', 'agfn@nirfi.unn.ru', 'alp@ipmras.ru', 'igra6119@yandex.ru']
        if server and port and sender and password and cc:
            msg = MIMEMultipart()
            msg['From'] = sender
            msg['To'] = cc[0]
            msg['Cc'] = ','.join(cc[1:])
            msg['Subject'] = 'Qara Dag Daily'
            body = f'Qara Dag data for {datetime.isoformat(datetime.now(), sep=" ", timespec="seconds")}'
            msg.attach(MIMEText(body, 'plain'))
            with open(results_file_name, 'rb') as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f'attachment; filename={results_file_name}')
                msg.attach(part)
                server = smtplib.SMTP(server, port)
                server.starttls()
                server.login(sender, password)
                server.sendmail(sender, cc + [sender], msg.as_string())
                server.quit()
            print('done')
        else:
            print('failed')
else:
    print('no file saved')

# wrscatter(-array(wd)+radians(90), ws, alpha=0.03, edgecolors='none').set_title('Wind Rose')
# wrbar(wd, array(ws)/sum(ws), opening=1, normed=True, nsector=360).set_title('Wind Rose')
# wrcontourf(wd, array(ws)/sum(ws), normed=True, nsector=360).set_title('Wind Rose')
# plt.show()
