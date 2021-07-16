#!/usr/bin/python3
# -*- coding: utf-8 -*-
import os
import os.path
import warnings
from datetime import datetime
from typing import BinaryIO, Dict, Iterable, List, Sequence, Set, Tuple, Union, Type, Optional, cast

import numpy as np
from PyQt5.QtCore import QSettings

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


class PrincipalAngles:
    def __init__(self, *, bb_angle: float = np.nan,
                 max_angle: float = np.nan,
                 min_angle: float = np.nan, min_angle_alt: float = np.nan,
                 magic_angle: float = np.nan, magic_angle_alt: float = np.nan) -> None:
        self.bb_angle: float = bb_angle
        self.max_angle: float = max_angle
        self.min_angle: float = min_angle
        self.min_angle_alt: float = min_angle_alt
        self.magic_angle: float = magic_angle
        self.magic_angle_alt: float = magic_angle_alt


class PrincipalAnglesIndices:
    def __init__(self, *, bb_angle: int,
                 max_angle: int,
                 min_angle: int, min_angle_alt: int,
                 magic_angle: int, magic_angle_alt: int) -> None:
        self.bb_angle: int = bb_angle
        self.max_angle: int = max_angle
        self.min_angle: int = min_angle
        self.min_angle_alt: int = min_angle_alt
        self.magic_angle: int = magic_angle
        self.magic_angle_alt: int = magic_angle_alt
        self._fields: List[str] = list(locals().keys())[1:]

    @property
    def fields(self) -> List[str]:
        return self._fields

    @property
    def values(self) -> List[int]:
        f: str
        return [getattr(self, f) for f in self._fields]


class PrincipalAnglesAbsorptionLabels:
    def __init__(self, bb_τ_label: str = '', bb_τ_label_alt: str = '',
                 leastsq_τ: str = '', leastsq_τ_error: str = '',
                 magic_angles_τ_label: str = '', magic_angles_τ_label_alt: str = ''):
        self.bb_τ_label: str = bb_τ_label
        self.bb_τ_label_alt: str = bb_τ_label_alt
        self.leastsq_τ: str = leastsq_τ
        self.leastsq_τ_error: str = leastsq_τ_error
        self.magic_angles_τ_label: str = magic_angles_τ_label
        self.magic_angles_τ_label_alt: str = magic_angles_τ_label_alt
        self._fields: List[str] = list(locals().keys())[1:]

    @property
    def values(self) -> List[str]:
        f: str
        return [getattr(self, f) for f in self._fields]


RawDataValueType = Union[
    None,
    bool,
    float,
    str,
    List[bool],
    List[float],
    List[List[float]],
    Dict[str, Union[int, float, str, List[int]]],
]


class DataItem:
    def __init__(self, data: Dict[str, RawDataValueType]) -> None:
        self.timestamp: float = data['timestamp']
        self.voltage: Optional[np.ndarray] = np.array(data.get('voltage')) if data.get('voltage', []) else None
        self.channels: int = self.voltage.shape[0] if self.voltage is not None else 0
        self.angle: float = data.get('angle', np.nan)

        self.weather: Dict[str, Union[None, int, float, str, List[int]]] = data.get('weather', dict())
        if self.weather:
            key: str
            for key in ('WindDir', 'AvgWindSpeed', 'OutsideHum', 'OutsideTemp', 'RainRate', 'UVLevel', 'SolarRad'):
                if key not in self.weather:
                    self.weather[key] = None

        self.temperatures: List[float] = data.get('temperatures', [])
        self.states: List[bool] = data.get('states', [])
        self.setpoints: List[int] = data.get('setpoints', [])
        self.enabled: Optional[bool] = data.get('enabled', None)


class Data(list):
    def __init__(self, data: Sequence[Dict[str, RawDataValueType]]) -> None:
        super().__init__()
        d: Dict[str, RawDataValueType]
        self.extend(DataItem(d) for d in data)

    def __getitem__(self, item: int) -> DataItem:
        return super().__getitem__(item)


class ProcessingResult:
    def __init__(self,
                 data: Dict[str, Union[RawDataValueType, datetime]],
                 absorption_labels: PrincipalAnglesAbsorptionLabels,
                 indices_closest_to_principal_angles: PrincipalAnglesIndices,
                 angles_closest_to_principal_angles: PrincipalAngles,
                 channels_count: int) -> None:
        self.data: Dict[str, Union[RawDataValueType, datetime]] = data
        self.absorption_labels: Optional[PrincipalAnglesAbsorptionLabels] = absorption_labels
        self.indices_closest_to_principal_angles: Optional[PrincipalAnglesIndices] = indices_closest_to_principal_angles
        self.angles_closest_to_principal_angles: Optional[PrincipalAngles] = angles_closest_to_principal_angles
        self.channels_count: int = channels_count


def calculate_bb_τ(loop_data: Dict[float, float], *,
                   min_angle: float, max_angle: float, bb_angle: float, precision: float = 5.) -> float:
    distance_to_max_angle: Optional[float] = None
    distance_to_min_angle: Optional[float] = None
    distance_to_bb_angle: Optional[float] = None
    closest_to_bb_angle: Optional[float] = None
    closest_to_max_angle: Optional[float] = None
    closest_to_min_angle: Optional[float] = None
    τ: float = np.nan
    angle: float
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
        d0: float = loop_data[closest_to_bb_angle]
        d1: float = loop_data[closest_to_max_angle]
        d2: float = loop_data[closest_to_min_angle]
        np.seterr(invalid='raise', divide='raise')
        try:
            if ((d0 > d1 and d0 > d2) or (d0 < d1 and d0 < d2)) and not np.isinf(d0) and not np.isinf(
                    d1) and not np.isinf(d2):
                τ = np.log((d0 - d1) / (d0 - d2)) / \
                    (1.0 / np.sin(np.radians(closest_to_min_angle))
                     - 1.0 / np.sin(np.radians(closest_to_max_angle)))
        except FloatingPointError:
            pass
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


def calculate_leastsq_τ(loop_data: Dict[float, float]) -> Tuple[float, float]:
    if not loop_data:
        return np.nan, np.nan
    h: np.ndarray = np.array(list(loop_data.keys()))
    d: np.ndarray = np.array(list(loop_data.values()))
    d0: np.float64 = d[np.argmin(np.abs(h))]
    inverted: bool = np.count_nonzero(d0 > d) < np.count_nonzero(d0 < d)
    good: np.ndarray
    if inverted:
        good = (h >= 15) & (d > d0)
    else:
        good = (h >= 15) & (d0 > d)
    if not np.any(good):
        return np.nan, np.nan
    h = h[good]
    d = d[good]
    x: np.ndarray = -1. / np.sin(np.deg2rad(h))
    y: np.ndarray
    if inverted:
        y = np.log(d - d0)
    else:
        y = np.log(d0 - d)
    with warnings.catch_warnings():
        warnings.filterwarnings('error')
        try:
            p: np.ndarray = cast(np.ndarray, np.polyfit(x, y, deg=1))
        except np.RankWarning:
            return np.nan, np.nan
    error: float
    if np.all(np.isnan(np.polyval(p, x) - y)):
        error = np.nan
    else:
        error = np.sqrt(np.nanmean(np.square(np.polyval(p, x) - y)))
    return p[0], error


def best_magic_angle(h: np.ndarray, lower_angle: Union[int, float], higher_angle: Union[int, float]) \
        -> Tuple[int, float]:
    i: int
    k: int
    if isinstance(lower_angle, int):
        i = lower_angle
    else:
        i = int(np.argmin(np.abs(h - lower_angle)))
    if isinstance(higher_angle, int):
        k = higher_angle
    else:
        k = int(np.argmin(np.abs(h - higher_angle)))
    z_a: float = float(np.deg2rad(h[k]))
    h_a: float = float(np.deg2rad(h[i]))
    j: int = -1
    min_diff: float = 1.
    _j: int
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


def calculate_magic_angles_τ(loop_data: Dict[float, float], lower_angle: float, higher_angle: float) -> float:
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
    j: int
    min_diff: float
    j, min_diff = best_magic_angle(h, i, k)
    if min_diff > 0.02:
        return np.nan
    τ: float = np.nan
    if (d[i] < d[j] < d[k] or d[i] > d[j] > d[k]) and h[i] != h[j] and not np.any(np.isinf([d[[i, j, k]]])):
        np.seterr(invalid='raise', divide='raise')
        try:
            τ = np.log((d[j] - d[k]) / (d[i] - d[j])) / (1. / np.sin(np.deg2rad(h[i])) - 1. / np.sin(np.deg2rad(h[j])))
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


def normalize(text) -> Data:
    """ make unified data structure for any data file version """
    import json

    try:
        data: Union[
            List[Dict[str, Union[float, str, List[List[float]]]]],  # old file version
            Dict[str, List[Dict[str, RawDataValueType]]]
        ] = json.loads(text)
    except json.decoder.JSONDecodeError:
        return Data([])

    raw_data: List[Dict[str, RawDataValueType]]
    if isinstance(data, dict) and 'raw_data' in data:
        raw_data = data['raw_data']
    else:
        if isinstance(data, list):
            raw_data = data
        elif isinstance(data, dict):
            return Data([{'weather': data, **data}])
        else:
            return Data([])

    # in some files, data were mistakenly repeated several times
    length: int = len(raw_data)
    if length > 2:
        pre_last_angle = raw_data[-2]['angle']
        for i in range(2, length):
            if raw_data[length - i - 1]['angle'] == pre_last_angle:
                return Data(raw_data[length - i:])
    return Data(raw_data)


def process(data: Data, ch: int, principal_angles: PrincipalAngles) -> ProcessingResult:
    channels_count: int = 0
    if ch < 0:
        raise ValueError('invalid channel number')

    angles_data: Dict[float, float] = {}
    item: DataItem
    # TODO: avoid repeating of `angles_data` keys
    for item in data:
        channels_count = max(channels_count, item.channels)
        if item.channels > ch and len(item.voltage[ch]) > 0:
            if np.any(item.voltage[ch] > 5.0) and np.any(item.voltage[ch] < -5.0):
                angles_data[item.angle] = np.nan
            elif np.any(item.voltage[ch] > 5.0):
                angles_data[item.angle] = np.inf
            elif np.any(item.voltage[ch] < -5.0):
                angles_data[item.angle] = -np.inf
            else:
                angles_data[item.angle] = float(np.mean(item.voltage[ch]))

    absorptions: Dict[str, float]
    absorption_labels: Optional[PrincipalAnglesAbsorptionLabels] = None
    indices_closest_to_principal_angles: Optional[PrincipalAnglesIndices] = None
    angles_closest_to_principal_angles: Optional[PrincipalAngles] = None
    if angles_data:
        absorption_labels, indices_closest_to_principal_angles, angles_closest_to_principal_angles = \
            get_absorption_labels(sorted(angles_data), principal_angles)

        leastsq_τ: float
        leastsq_τ_error: float
        leastsq_τ, leastsq_τ_error = calculate_leastsq_τ(angles_data)
        absorptions = {
            absorption_labels.bb_τ_label:
                calculate_bb_τ(angles_data,
                               min_angle=principal_angles.min_angle,
                               max_angle=principal_angles.max_angle,
                               bb_angle=principal_angles.bb_angle),
            absorption_labels.bb_τ_label_alt:
                calculate_bb_τ(angles_data,
                               min_angle=principal_angles.min_angle_alt,
                               max_angle=principal_angles.max_angle,
                               bb_angle=principal_angles.bb_angle),
            absorption_labels.leastsq_τ: leastsq_τ,
            absorption_labels.leastsq_τ_error: leastsq_τ_error,
            absorption_labels.magic_angles_τ_label:
                calculate_magic_angles_τ(angles_data,
                                         lower_angle=principal_angles.min_angle,
                                         higher_angle=principal_angles.max_angle),
            absorption_labels.magic_angles_τ_label_alt:
                calculate_magic_angles_τ(angles_data,
                                         lower_angle=principal_angles.min_angle_alt,
                                         higher_angle=principal_angles.max_angle)
        }
    else:
        absorptions = dict()
    # rename `angles_data` keys
    angles_data_str: Dict[str, float] = dict((f'θ = {90 - i:.3f}'.rstrip('0').rstrip('.') + '°', angles_data[i])
                                             for i in sorted(angles_data))

    weather: Dict[str, Union[None, str, int, float]] = {'WindDir': None, 'AvgWindSpeed': None, 'OutsideHum': None,
                                                        'OutsideTemp': None, 'RainRate': None, 'UVLevel': None,
                                                        'SolarRad': None}
    for item in data:
        if item.weather:
            weather.update(item.weather)
            break

    arduino_state: Dict[str, Union[int, float, bool]] = dict()
    index: int
    value: Union[bool, float, int]
    name: str
    for item in data:
        if item.temperatures:
            for index, value in enumerate(item.temperatures):
                name = f'Temperature {index + 1}'
                arduino_state[name] = cast(float, value)
            break
    for item in data:
        if item.states:
            for index, value in enumerate(item.states):
                name = f'Relay State {index + 1}'
                arduino_state[name] = cast(bool, value)
        break
    for item in data:
        if item.setpoints:
            for index, value in enumerate(item.setpoints):
                name = f'Setpoint {index + 1}'
                arduino_state[name] = cast(int, value)
            break
    for item in data:
        if item.enabled is not None:
            name = f'Auto Relay Mode'
            arduino_state[name] = cast(bool, item.enabled)
            break

    return ProcessingResult(
        {
            TIME_FIELD: datetime.fromtimestamp(cast(float, data[0].timestamp)),
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
            **angles_data_str,
            **arduino_state
        },
        absorption_labels,
        indices_closest_to_principal_angles,
        angles_closest_to_principal_angles,
        channels_count
    )


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


def take_webcam_shot() -> bytes:
    import cv2

    """ 
    use 
    v4l2-ctl -d /dev/video0 --all
    to get the supported properties
    """
    cap: cv2.VideoCapture = cv2.VideoCapture(0)

    params: List[int] = list()
    params.append(cv2.IMWRITE_JPEG_OPTIMIZE)
    params.append(1)

    image: bytes = bytes()

    try:
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 10000)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 10000)
            cap.set(cv2.CAP_PROP_AUTO_WB, 0)
            # Read picture. ret === True on success
            ret, frame = cap.read()
            if ret:
                image_np: np.ndarray
                ret, image_np = cv2.imencode('.jpg', frame, params)
                if not ret:
                    image = bytes()
                else:
                    image = image_np.tobytes()
    finally:
        # Close device
        cap.release()

    return image


def send_email(config_name: str, results_file_name: str) -> None:
    if not os.path.exists(config_name):
        return

    import socket
    import time
    import re
    from configparser import ConfigParser
    from email import encoders
    from email.mime.base import MIMEBase
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from smtplib import SMTP

    config: ConfigParser = ConfigParser()
    config.read(config_name)

    server_address: str = config.get('email', 'server', fallback='')
    port: int = config.getint('email', 'port', fallback=0)
    sender: str = config.get('email', 'login', fallback='')
    password: str = config.get('email', 'password', fallback='')
    cc: List[str] = re.findall(r"[\w.@]+", config.get('email', 'recipients', fallback=''))
    if not (server_address and port and sender and password and cc):
        return

    msg: MIMEMultipart = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = cc[0]
    msg['Cc'] = ','.join(cc[1:])
    msg['Subject'] = 'Qara Dag Daily'
    body: str = 'Qara Dag data summary for ' + datetime.isoformat(datetime.now(), sep=" ")
    msg.attach(MIMEText(body, 'plain'))
    attachment: BinaryIO
    part: MIMEBase
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

    photos: List[str] = list_files('/tmp/tmpfs', max_age=DAY, suffix='.jpg')
    photo_file_name: str
    photo: bytes
    if photos:
        for photo_file_name in photos:
            photo_file: BinaryIO
            with open(photo_file_name, 'rb') as photo_file:
                photo = photo_file.read()
                if photo:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(photo)
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition', 'attachment',
                                    filename=os.path.basename(photo_file_name))
                    msg.attach(part)
    else:
        photo = take_webcam_shot()
        if photo:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(photo)
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', 'attachment',
                            filename=f'webcam_photo_{time.strftime("%Y-%m-%d_%H-%M")}.jpg')
            msg.attach(part)

    mail_server_connected: bool = False
    # FIXME: sometimes, it becomes an infinite loop
    while not mail_server_connected:
        try:
            server: SMTP = SMTP(server_address, port)
            server.starttls()
            server.login(sender, password)
            server.sendmail(sender, cc + [sender], msg.as_string())
            server.quit()
        except OSError:
            print(socket.gethostbyname(server_address))
            time.sleep(60)
        else:
            mail_server_connected = True

    # if the email is sent, clean up
    for photo_file_name in photos:
        os.remove(photo_file_name)


def check_new_files_given(filenames: Sequence[str], timeout: float = DAY) -> bool:
    new_files_given: bool = False
    filename: str
    for filename in filenames:
        if filename.endswith('.json.gz') and os.path.exists(filename) and os.path.isfile(filename):
            mod_time: float = os.path.getmtime(filename)
            if CURRENT_TIME - mod_time < timeout:
                new_files_given = True
                break
    return new_files_given


def get_config_value(settings: QSettings, *, section: str = 'settings', key: str,
                     default: Union[bool, int, float, str],
                     _type: Union[Type[bool], Type[int], Type[float], Type[str]]) -> Union[bool, int, float, str]:
    if section not in settings.childGroups():
        return default
    settings.beginGroup(section)
    v: Union[bool, int, float, str]
    try:
        v = settings.value(key, default, _type)
        # print('get', section, key, v, _type)
    except TypeError:
        v = default
        # print('get', section, key, v, '(default)', _type)
    settings.endGroup()
    return v


def get_principal_angles() -> PrincipalAngles:
    settings: QSettings = QSettings("SavSoft", "Crimea Radiometer")

    return PrincipalAngles(
        bb_angle=cast(float, get_config_value(settings, key='black body position', default=0, _type=float)),
        max_angle=cast(float, get_config_value(settings, key='zenith position', default=90, _type=float)),
        min_angle=cast(float, get_config_value(settings, key='horizon position', default=15, _type=float)),
        min_angle_alt=cast(float, get_config_value(settings, key='horizon position alt', default=20, _type=float)),
        magic_angle=np.nan,
        magic_angle_alt=np.nan,
    )


def get_indices_closest_to_principal_angles(angles: np.ndarray,
                                            principal_angles: PrincipalAngles) \
        -> PrincipalAnglesIndices:
    max_angle = int(np.argmin(np.abs(angles - principal_angles.max_angle)))
    min_angle = int(np.argmin(np.abs(angles - principal_angles.min_angle)))
    min_angle_alt = int(np.argmin(np.abs(angles - principal_angles.min_angle_alt)))
    return PrincipalAnglesIndices(
        bb_angle=int(np.argmin(np.abs(angles - principal_angles.bb_angle))),
        max_angle=max_angle,
        min_angle=min_angle,
        min_angle_alt=min_angle_alt,
        magic_angle=best_magic_angle(angles, angles[min_angle], angles[max_angle])[0],
        magic_angle_alt=best_magic_angle(angles, angles[min_angle_alt], angles[max_angle])[0],
    )


def get_absorption_labels(angles_data: Sequence[float], principal_angles: PrincipalAngles) \
        -> Tuple[PrincipalAnglesAbsorptionLabels, PrincipalAnglesIndices, PrincipalAngles]:
    """ :returns absorption labels and the angles used in the labels"""
    h: np.ndarray = np.array(list(angles_data))
    indices_closest_to_principal_angles: PrincipalAnglesIndices = \
        get_indices_closest_to_principal_angles(h, principal_angles)
    angles_closest_to_principal_angles: PrincipalAngles = \
        PrincipalAngles(**dict(zip(indices_closest_to_principal_angles.fields,
                                   h[indices_closest_to_principal_angles.values])))
    return PrincipalAnglesAbsorptionLabels(
        bb_τ_label=(
         f'τ for θ = {90 - angles_closest_to_principal_angles.bb_angle:.3f}'.rstrip('0').rstrip('.') +
         f'°, {90 - angles_closest_to_principal_angles.min_angle:.3f}'.rstrip('0').rstrip('.') +
         f'°, {90 - angles_closest_to_principal_angles.max_angle:.3f}'.rstrip('0').rstrip('.') + '°'),
        bb_τ_label_alt=(
         f'τ for θ = {90 - angles_closest_to_principal_angles.bb_angle:.3f}'.rstrip('0').rstrip('.') +
         f'°, {90 - angles_closest_to_principal_angles.min_angle_alt:.3f}'.rstrip('0').rstrip('.') +
         f'°, {90 - angles_closest_to_principal_angles.max_angle:.3f}'.rstrip('0').rstrip('.') + '°'),
        leastsq_τ='leastsq τ',
        leastsq_τ_error='leastsq τ error',
        magic_angles_τ_label=(
         f'τ for θ = {90 - angles_closest_to_principal_angles.min_angle:.3f}'.rstrip('0').rstrip('.') +
         f'''°, {90 - h[best_magic_angle(
             h, angles_closest_to_principal_angles.min_angle,
             angles_closest_to_principal_angles.max_angle)[0]]:.3f}'''.rstrip('0').rstrip('.') +
         f'°, {90 - angles_closest_to_principal_angles.max_angle:.3f}'.rstrip('0').rstrip('.') + '°'),
        magic_angles_τ_label_alt=(
         f'τ for θ = {90 - angles_closest_to_principal_angles.min_angle_alt:.3f}'.rstrip('0').rstrip('.') +
         f'''°, {90 -
                 h[best_magic_angle(
                     h, angles_closest_to_principal_angles.min_angle_alt,
                     angles_closest_to_principal_angles.max_angle)[0]]:.3f}'''.rstrip('0').rstrip('.') +
         f'°, {90 - angles_closest_to_principal_angles.max_angle:.3f}'.rstrip('0').rstrip('.') + '°'),
    ), indices_closest_to_principal_angles, angles_closest_to_principal_angles


def main():
    import argparse
    from gzip import GzipFile

    from xlsxwriter import Workbook
    from xlsxwriter.format import Format
    from xlsxwriter.utility import xl_col_to_name
    from xlsxwriter.worksheet import Worksheet

    ap = argparse.ArgumentParser(description='extracts summary from raw data and writes it into an XLSX file')
    ap.add_argument('-I', '--ignore-existing', help='skip check whether the result file exists',
                    action='store_true', default=False)
    ap.add_argument('-c', '--config', help='configuration file', default=os.path.splitext(__file__)[0] + '.ini')
    ap.add_argument('-e', '--send-email', help='email the result file to the recipients listed in config',
                    action='store_true', default=False)
    ap.add_argument('-a', '--anyway', help='process files even if no new files given (younger than a day)',
                    action='store_true', default=False)
    ap.add_argument('-o', '--output-prefix', help='prefix for the result workbook; if in /tmp, gets removed afterwards',
                    default=(('/tmp/tmpfs/results_' if os.path.exists('/tmp/tmpfs') else 'results_')
                             + datetime.now().date().isoformat()))
    ap.add_argument('-m', '--max-age', help='maximal age of files to take into account (in days)',
                    default=-1., type=float)
    ap.add_argument('files', metavar='PATH', nargs='+', help='path to a file to process')
    args = ap.parse_args()

    results_file_name: str = args.output_prefix + '.xlsx'
    # print(results_file_name)
    if not args.ignore_existing and os.path.exists(results_file_name):
        exit(0)

    filenames: List[str] = []
    filename: str
    for filename in args.files:
        filenames.extend(list_files(filename, max_age=args.max_age * DAY, suffix='.json.gz'))

    def sorting_key(_fn: str) -> str:
        bn = os.path.basename(_fn)
        return bn if '-' not in bn else bn[bn.index('-') + 1:]  # hotfix; should be sorting by the timestamp

    filenames.sort(key=sorting_key, reverse=True)

    if not args.anyway and not check_new_files_given(filenames):
        # nothing to do
        exit(0)

    principal_angles: PrincipalAngles = get_principal_angles()

    fields_set: Set[Tuple[str, ...]] = set()

    settings: QSettings = QSettings("SavSoft", "Crimea Radiometer")
    section: str = 'labels'

    data: List[Dict[str, ProcessingResult]] = []
    channel_label: str
    data_piece: ProcessingResult
    for filename in filenames:
        if not os.path.isfile(filename):
            continue
        f_in: GzipFile
        with GzipFile(filename, 'r') as f_in:
            content: str = f_in.read().decode()
        json_data: Data = normalize(content)
        if not json_data:
            continue
        data.append(dict())
        channels_count: int = 1
        channel: int = 0
        while channel < channels_count:
            channel_label = get_config_value(settings, section=section,
                                             key=str(channel),
                                             default=f'Channel {channel + 1}',
                                             _type=str)
            # if channel_label.startswith('_'):  # do not process hidden channels
            #     channel += 1
            #     continue
            data_piece = process(json_data, channel, principal_angles)
            channels_count = data_piece.channels_count
            data[-1][channel_label] = data_piece
            fields_set.add(tuple(data_piece.data))
            channel += 1

    def all_fields() -> List[str]:
        class TwoSides:
            def __init__(self, to_the_left: Iterable[str] = (), to_the_right: Iterable[str] = ()) -> None:
                self.to_the_left: set[str] = set(to_the_left)
                self.to_the_right: set[str] = set(to_the_right)

            def __repr__(self) -> str:
                return f'{{to the left: {self.to_the_left}, to the right: {self.to_the_right}}}'

        other_fields: dict[str, TwoSides] = {}
        index: int
        field: str
        chunk: str
        for chunk in fields_set:
            for index, field in enumerate(chunk):
                if field not in other_fields:
                    other_fields[field] = TwoSides(to_the_left=chunk[:index], to_the_right=chunk[index + 1:])
                else:
                    other_fields[field].to_the_left.update(chunk[:index])
                    other_fields[field].to_the_right.update(chunk[index + 1:])

        already_sorted_fields: Set[str] = set()

        def sort(s: set[str], excluded: set[str]) -> list[str]:
            s -= already_sorted_fields
            if not s:
                return []
            f: str = s.pop()
            already_sorted_fields.add(f)
            if not s:
                return [f]
            return (sort(other_fields[f].to_the_left - excluded, other_fields[f].to_the_right.union(excluded))
                    + [f]
                    + sort(other_fields[f].to_the_right - excluded, other_fields[f].to_the_left.union(excluded)))

        return sort(set(other_fields.keys()), set())

    header_fields: List[str] = all_fields()

    def write_header(worksheet: Worksheet, header: Sequence[str], text_format: Format) -> None:
        index: int
        caption: str
        for index, caption in enumerate(header):
            worksheet.write_string(0, index, caption, text_format)

    def write_row(worksheet: Worksheet, row_number: int,
                  row_dict: Dict[str, Union[RawDataValueType, datetime]], keys: Sequence[str]) -> None:
        index: int
        key: str
        for index, key in enumerate(keys):
            if key not in row_dict:
                worksheet.write(row_number, index, None)
            elif isinstance(row_dict[key], float) and np.isnan(row_dict[key]):
                worksheet.write(row_number, index, None)
            else:
                worksheet.write(row_number, index, row_dict[key])

    workbook: Workbook = Workbook(results_file_name,
                                  {'default_date_format': 'dd.mm.yyyy hh:mm:ss',
                                   'nan_inf_to_errors': True,
                                   'constant_memory': True})
    header_format: Format = workbook.add_format({'bold': True})

    written_rows: List[int] = []
    row: int
    data_row: Dict[str, ProcessingResult]
    for row, data_row in enumerate(data):
        for channel, (channel_label, data_piece) in enumerate(data_row.items()):
            if len(workbook.worksheets()) <= channel:
                if channel_label not in workbook.sheetnames:
                    workbook.add_worksheet(channel_label)
                else:
                    i: int = 2
                    while f'{channel_label} [{i}]' in workbook.sheetnames:
                        i += 1
                    workbook.add_worksheet(f'{channel_label} [{i}]')
                write_header(workbook.worksheets()[channel], header_fields, header_format)
                workbook.worksheets()[channel].freeze_panes(1, 1)  # freeze first row and first column
                if len(written_rows) <= channel:
                    written_rows.append(1)

            write_row(workbook.worksheets()[channel], written_rows[channel], data_piece.data, header_fields)
            if data_piece.absorption_labels is not None:
                # for bb_τ_label
                formula: str = '=LN((${d0_c}{row} - ${d2_c}{row})/(${d0_c}{row} - ${d1_c}{row})) ' \
                               '/ (1/COS(RADIANS({θ1})) - 1/COS(RADIANS({θ2})))' \
                    .format(d0_c=xl_col_to_name(len(GENERAL_FIELDS) + len(data_piece.absorption_labels.values)
                                                + data_piece.indices_closest_to_principal_angles.bb_angle),
                            d1_c=xl_col_to_name(len(GENERAL_FIELDS) + len(data_piece.absorption_labels.values)
                                                + data_piece.indices_closest_to_principal_angles.min_angle),
                            d2_c=xl_col_to_name(len(GENERAL_FIELDS) + len(data_piece.absorption_labels.values)
                                                + data_piece.indices_closest_to_principal_angles.max_angle),
                            row=written_rows[channel] + 1,
                            θ1=90 - data_piece.angles_closest_to_principal_angles.min_angle,
                            θ2=90 - data_piece.angles_closest_to_principal_angles.max_angle)
                # print(formula)
                label: str = data_piece.absorption_labels.bb_τ_label
                if data_piece.data[label] is not None and not np.isnan(data_piece.data[label]):
                    workbook.worksheets()[channel].write_formula(
                        written_rows[channel],
                        len(GENERAL_FIELDS) + data_piece.absorption_labels.values.index(label),
                        formula,
                        value=data_piece.data[label])
                # for bb_τ_label_alt
                formula: str = '=LN((${d0_c}{row} - ${d2_c}{row})/(${d0_c}{row} - ${d1_c}{row})) ' \
                               '/ (1/COS(RADIANS({θ1})) - 1/COS(RADIANS({θ2})))' \
                    .format(d0_c=xl_col_to_name(len(GENERAL_FIELDS) + len(data_piece.absorption_labels.values)
                                                + data_piece.indices_closest_to_principal_angles.bb_angle),
                            d1_c=xl_col_to_name(len(GENERAL_FIELDS) + len(data_piece.absorption_labels.values)
                                                + data_piece.indices_closest_to_principal_angles.min_angle_alt),
                            d2_c=xl_col_to_name(len(GENERAL_FIELDS) + len(data_piece.absorption_labels.values)
                                                + data_piece.indices_closest_to_principal_angles.max_angle),
                            row=written_rows[channel] + 1,
                            θ1=90 - data_piece.angles_closest_to_principal_angles.min_angle_alt,
                            θ2=90 - data_piece.angles_closest_to_principal_angles.max_angle)
                # print(formula)
                label: str = data_piece.absorption_labels.bb_τ_label_alt
                if data_piece.data[label] is not None and not np.isnan(data_piece.data[label]):
                    workbook.worksheets()[channel].write_formula(
                        written_rows[channel],
                        len(GENERAL_FIELDS) + data_piece.absorption_labels.values.index(label),
                        formula,
                        value=data_piece.data[label])
                # for magic_angles_τ_label
                formula: str = '=LN((${d2_c}{row} - ${d3_c}{row})/(${d1_c}{row} - ${d2_c}{row})) ' \
                               '/ (1/COS(RADIANS({θ1})) - 1/COS(RADIANS({θ2})))' \
                    .format(d1_c=xl_col_to_name(len(GENERAL_FIELDS) + len(data_piece.absorption_labels.values)
                                                + data_piece.indices_closest_to_principal_angles.min_angle),
                            d2_c=xl_col_to_name(len(GENERAL_FIELDS) + len(data_piece.absorption_labels.values)
                                                + data_piece.indices_closest_to_principal_angles.magic_angle),
                            d3_c=xl_col_to_name(len(GENERAL_FIELDS) + len(data_piece.absorption_labels.values)
                                                + data_piece.indices_closest_to_principal_angles.max_angle),
                            row=written_rows[channel] + 1,
                            θ1=90 - data_piece.angles_closest_to_principal_angles.min_angle,
                            θ2=90 - data_piece.angles_closest_to_principal_angles.magic_angle)
                # print(formula)
                label: str = data_piece.absorption_labels.magic_angles_τ_label
                if data_piece.data[label] is not None and not np.isnan(data_piece.data[label]):
                    workbook.worksheets()[channel].write_formula(
                        written_rows[channel],
                        len(GENERAL_FIELDS) + data_piece.absorption_labels.values.index(label),
                        formula,
                        value=data_piece.data[label])
                # for magic_angles_τ_label_alt
                formula: str = '=LN((${d2_c}{row} - ${d3_c}{row})/(${d1_c}{row} - ${d2_c}{row})) ' \
                               '/ (1/COS(RADIANS({θ1})) - 1/COS(RADIANS({θ2})))' \
                    .format(d1_c=xl_col_to_name(len(GENERAL_FIELDS) + len(data_piece.absorption_labels.values)
                                                + data_piece.indices_closest_to_principal_angles.min_angle_alt),
                            d2_c=xl_col_to_name(len(GENERAL_FIELDS) + len(data_piece.absorption_labels.values)
                                                + data_piece.indices_closest_to_principal_angles.magic_angle_alt),
                            d3_c=xl_col_to_name(len(GENERAL_FIELDS) + len(data_piece.absorption_labels.values)
                                                + data_piece.indices_closest_to_principal_angles.max_angle),
                            row=written_rows[channel] + 1,
                            θ1=90 - data_piece.angles_closest_to_principal_angles.min_angle_alt,
                            θ2=90 - data_piece.angles_closest_to_principal_angles.magic_angle_alt)
                # print(formula)
                label: str = data_piece.absorption_labels.magic_angles_τ_label_alt
                if data_piece.data[label] is not None and not np.isnan(data_piece.data[label]):
                    workbook.worksheets()[channel].write_formula(
                        written_rows[channel],
                        len(GENERAL_FIELDS) + data_piece.absorption_labels.values.index(label),
                        formula,
                        value=data_piece.data[label])

            written_rows[channel] += 1

    workbook.close()
    if args.send_email and any(written_rows):
        send_email(args.config, results_file_name)
    if results_file_name.startswith('/tmp/') and os.path.exists(results_file_name):
        os.remove(results_file_name)


if __name__ == '__main__':
    main()
