# -*- coding: utf-8 -*-

import os.path
from datetime import date
from typing import Any, Iterable, List

import matplotlib
from PyQt5.QtGui import QIcon
from matplotlib.lines import Line2D


def get_icon(name):
    basedir = os.path.join(matplotlib.get_data_path(), 'images')
    return QIcon(os.path.join(basedir, name))


def make_launcher(entry_path: str, file_path: str):
    if not os.path.exists(entry_path):
        try:
            import stat
            with open(entry_path, 'w') as f_out:
                f_out.writelines('\n'.join([
                    '[Desktop Entry]',
                    'Version=1.1',
                    'Name=Crimea Radiometer',
                    f'Comment=Crimea Radiometer Controller, {date.today().year}',
                    'Exec=python3 ' + file_path,
                    'Icon=' + os.path.join(os.path.split(file_path)[0], 'crimea-eng-circle.svg'),
                    'Path=' + os.path.split(file_path)[0],
                    'Terminal=true',
                    'Type=Application',
                    'Categories=Science;',
                ]))
            os.chmod(entry_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
            print('created shortcut', entry_path)
        except (ImportError, PermissionError, IOError) as ex:
            print(f'failed to create {entry_path}: {ex}')


def make_desktop_launcher(file_path: str):
    desktop_path: str = os.path.join(os.path.expanduser('~'), 'Desktop')
    desktop_entry_path: str = os.path.join(desktop_path, 'Crimea Radiometer.desktop')
    make_launcher(desktop_entry_path, file_path)


def make_autostart_launcher(file_path: str):
    autostart_path: str = os.path.join(os.path.expanduser('~'), '.config', 'autostart')
    autostart_entry_path: str = os.path.join(autostart_path, 'Crimea Radiometer.desktop')
    make_launcher(autostart_entry_path, file_path)


def to_int(x, limits=None):
    try:
        if limits:
            return min(max(int(x), min(limits)), max(limits))
        else:
            return int(x)
    except ValueError:
        return 0


def to_bool(value):
    if isinstance(value, str):
        if value.lower() in ('1', 'yes', 'true', 'on'):
            return True
        elif value.lower() in ('0', 'no', 'false', 'off'):
            return False
        else:
            raise ValueError
    else:
        return bool(value)


def stringify_list(values: List[Any], sep: str = ' '):
    return sep.join([str(v) if not isinstance(v, bool) else ('yes' if v else 'no') for v in values])


def label_lines(lines: List[Line2D], labels: Iterable[str], suffix: str = ''):
    for line, label in zip(lines, labels):
        line.set_label(f'{label} ({suffix})' if suffix else label)
