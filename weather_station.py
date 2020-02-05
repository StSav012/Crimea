#!/usr/bin/python3
# -*- coding: utf-8 -*-

import argparse
import configparser
import datetime
import gzip
import json
import os
import time
import sys

from PyQt5.QtCore import QCoreApplication, QMetaObject, QSettings, QTimer, Qt
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import QApplication, QCheckBox, QDesktopWidget, QFormLayout, QGridLayout, QGroupBox, QLabel, \
    QMainWindow, QMessageBox, QSpinBox, QStatusBar, QWidget

try:
    import dallas_dummy as dallas
except ImportError:
    import dallas


class UiMainWindow(object):
    def __init__(self):
        self.central_widget = QWidget()
        self.grid_layout_main = QGridLayout(self.central_widget)
        self.group_temperature = QGroupBox(self.central_widget)
        self.grid_layout_temperature = QGridLayout(self.group_temperature)
        self.label_temperature_inside = QLabel(self.group_temperature)
        self.label_temperature_inside_value = QLabel(self.group_temperature)
        self.label_temperature_outside = QLabel(self.group_temperature)
        self.label_temperature_outside_value = QLabel(self.group_temperature)
        self.group_humidity = QGroupBox(self.central_widget)
        self.grid_layout_humidity = QGridLayout(self.group_humidity)
        self.label_humidity_inside = QLabel(self.group_humidity)
        self.label_humidity_inside_value = QLabel(self.group_humidity)
        self.label_humdity_outside = QLabel(self.group_humidity)
        self.label_humidity_outside_value = QLabel(self.group_humidity)
        self.group_wind = QGroupBox(self.central_widget)
        self.grid_layout_wind = QGridLayout(self.group_wind)
        self.label_wind_speed = QLabel(self.group_wind)
        self.label_wind_speed_value = QLabel(self.group_wind)
        self.label_wind_average = QLabel(self.group_wind)
        self.label_wind_average_value = QLabel(self.group_wind)
        self.label_wind_direction = QLabel(self.group_wind)
        self.label_wind_direction_value = QLabel(self.group_wind)
        self.group_rain = QGroupBox(self.central_widget)
        self.grid_layout_rain = QGridLayout(self.group_rain)
        self.label_rain_rate = QLabel(self.group_rain)
        self.label_rain_rate_value = QLabel(self.group_rain)
        self.label_rain_day = QLabel(self.group_rain)
        self.label_rain_day_value = QLabel(self.group_rain)
        self.label_rain_month = QLabel(self.group_rain)
        self.label_rain_month_value = QLabel(self.group_rain)
        self.form_layout_update = QFormLayout()
        self.check_update = QCheckBox(self.central_widget)
        self.spin_update_interval = QSpinBox(self.central_widget)
        self.status_bar = QStatusBar()
        self._translate = QCoreApplication.translate

    def setup_ui(self, main_window):
        main_window.resize(217, 474)
        _value_label_interaction_flags = (Qt.LinksAccessibleByKeyboard
                                          | Qt.LinksAccessibleByMouse
                                          | Qt.TextBrowserInteraction
                                          | Qt.TextSelectableByKeyboard
                                          | Qt.TextSelectableByMouse)
        icon = QIcon()
        icon.addPixmap(QPixmap(os.path.join(os.path.split(__file__)[0], 'crimea-eng-circle.svg')),
                       QIcon.Normal, QIcon.Off)
        main_window.setWindowIcon(icon)
        self.grid_layout_temperature.addWidget(self.label_temperature_inside, 0, 0, 1, 1)
        self.label_temperature_inside_value.setTextInteractionFlags(_value_label_interaction_flags)
        self.grid_layout_temperature.addWidget(self.label_temperature_inside_value, 0, 1, 1, 1)
        self.grid_layout_temperature.addWidget(self.label_temperature_outside, 1, 0, 1, 1)
        self.label_temperature_outside_value.setTextInteractionFlags(_value_label_interaction_flags)
        self.grid_layout_temperature.addWidget(self.label_temperature_outside_value, 1, 1, 1, 1)
        self.grid_layout_main.addWidget(self.group_temperature, 0, 0, 1, 1)
        self.grid_layout_humidity.addWidget(self.label_humidity_inside, 0, 0, 1, 1)
        self.label_humidity_inside_value.setTextInteractionFlags(_value_label_interaction_flags)
        self.grid_layout_humidity.addWidget(self.label_humidity_inside_value, 0, 1, 1, 1)
        self.grid_layout_humidity.addWidget(self.label_humdity_outside, 1, 0, 1, 1)
        self.label_humidity_outside_value.setTextInteractionFlags(_value_label_interaction_flags)
        self.grid_layout_humidity.addWidget(self.label_humidity_outside_value, 1, 1, 1, 1)
        self.grid_layout_main.addWidget(self.group_humidity, 1, 0, 1, 1)
        self.grid_layout_wind.addWidget(self.label_wind_speed, 0, 0, 1, 1)
        self.label_wind_speed_value.setTextInteractionFlags(_value_label_interaction_flags)
        self.grid_layout_wind.addWidget(self.label_wind_speed_value, 0, 1, 1, 1)
        self.grid_layout_wind.addWidget(self.label_wind_average, 1, 0, 1, 1)
        self.label_wind_average_value.setTextInteractionFlags(_value_label_interaction_flags)
        self.grid_layout_wind.addWidget(self.label_wind_average_value, 1, 1, 1, 1)
        self.grid_layout_wind.addWidget(self.label_wind_direction, 2, 0, 1, 1)
        self.label_wind_direction_value.setTextInteractionFlags(_value_label_interaction_flags)
        self.grid_layout_wind.addWidget(self.label_wind_direction_value, 2, 1, 1, 1)
        self.grid_layout_main.addWidget(self.group_wind, 2, 0, 1, 1)
        self.grid_layout_rain.addWidget(self.label_rain_rate, 0, 0, 1, 1)
        self.label_rain_rate_value.setTextInteractionFlags(_value_label_interaction_flags)
        self.grid_layout_rain.addWidget(self.label_rain_rate_value, 0, 1, 1, 1)
        self.grid_layout_rain.addWidget(self.label_rain_day, 1, 0, 1, 1)
        self.label_rain_day_value.setTextInteractionFlags(_value_label_interaction_flags)
        self.grid_layout_rain.addWidget(self.label_rain_day_value, 1, 1, 1, 1)
        self.grid_layout_rain.addWidget(self.label_rain_month, 2, 0, 1, 1)
        self.label_rain_month_value.setTextInteractionFlags(_value_label_interaction_flags)
        self.grid_layout_rain.addWidget(self.label_rain_month_value, 2, 1, 1, 1)
        self.grid_layout_main.addWidget(self.group_rain, 3, 0, 1, 1)
        self.form_layout_update.setWidget(0, QFormLayout.LabelRole, self.check_update)
        self.spin_update_interval.setRange(1, 1440)
        self.form_layout_update.setWidget(0, QFormLayout.FieldRole, self.spin_update_interval)
        self.grid_layout_main.addLayout(self.form_layout_update, 4, 0, 1, 1)
        main_window.setCentralWidget(self.central_widget)
        main_window.setStatusBar(self.status_bar)
        self.retranslate_ui(main_window)
        QMetaObject.connectSlotsByName(main_window)
        main_window.adjustSize()

    def retranslate_ui(self, main_window):
        main_window.setWindowTitle(self._translate('main_window', 'Dallas Meteo'))
        self.group_temperature.setTitle(self._translate('main_window', 'Temperature [°C]'))
        self.label_temperature_inside.setText(self._translate('main_window', 'Inside:'))
        self.label_temperature_outside.setText(self._translate('main_window', 'Outside:'))
        self.group_humidity.setTitle(self._translate('main_window', 'Humidity [%]'))
        self.label_humidity_inside.setText(self._translate('main_window', 'Inside:'))
        self.label_humdity_outside.setText(self._translate('main_window', 'Outside:'))
        self.group_wind.setTitle(self._translate('main_window', 'Wind'))
        self.label_wind_speed.setText(self._translate('main_window', 'Speed:'))
        self.label_wind_average.setText(self._translate('main_window', 'Average:'))
        self.label_wind_direction.setText(self._translate('main_window', 'Direction [°]:'))
        self.group_rain.setTitle(self._translate('main_window', 'Rain'))
        self.label_rain_rate.setText(self._translate('main_window', 'Rate:'))
        self.label_rain_day.setText(self._translate('main_window', 'This Day:'))
        self.label_rain_month.setText(self._translate('main_window', 'This Month:'))
        self.check_update.setText(self._translate('main_window', 'Update Every'))
        self.spin_update_interval.setSuffix(self._translate('main_window', ' min'))


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


def make_launcher(entry_path: str):
    if not os.path.exists(entry_path):
        try:
            import stat
            with open(entry_path, 'w') as fout:
                fout.write('\n'.join([
                    '[Desktop Entry]',
                    'Version=1.0',
                    'Name=Dallas Meteo',
                    f'Comment=Dallas Weather Station Logger, {time.localtime().tm_year}',
                    'Exec=python3 ' + os.path.abspath(__file__),
                    'Icon=' + os.path.join(os.path.split(os.path.abspath(__file__))[0], 'crimea-eng-circle.svg'),
                    'Path=' + os.path.split(os.path.abspath(__file__))[0],
                    'Terminal=true',
                    'Type=Application',
                    'Categories=Science;',
                ]))
            os.chmod(entry_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
            print('created shortcut', entry_path)
        except (ImportError, PermissionError, IOError) as ex:
            print(f'failed to create {entry_path}: {ex}')


def make_desktop_launcher():
    desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
    desktop_entry_path = os.path.join(desktop_path, 'Dallas Meteo.desktop')
    make_launcher(desktop_entry_path)


class App(QMainWindow, UiMainWindow):
    def __init__(self):
        super().__init__()
        self.setup_ui(self)
        self.settings = QSettings('SavSoft', 'Dallas Meteo Logger')
        self.timer = QTimer()
        self.meteo = dallas.Dallas()
        # add slots events
        self.check_update.stateChanged.connect(self.check_update_changed)
        self.spin_update_interval.valueChanged.connect(self.spin_update_interval_changed)
        # config
        self._loading: bool = False
        self.load_config()

    def closeEvent(self, event):
        """ senseless joke in the loop """
        close = QMessageBox.No
        while close == QMessageBox.No:
            close = QMessageBox()
            close.setText(self._translate('main_window', 'Are you sure?'))
            close.setIcon(QMessageBox.Question)
            close.setWindowIcon(self.windowIcon())
            close.setWindowTitle(self.windowTitle())
            close.setStandardButtons(QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            close = close.exec()

            if close == QMessageBox.Yes:
                self.settings.setValue('windowGeometry', self.saveGeometry())
                self.settings.setValue('windowState', self.saveState())
                with open(args.config, 'w') as cout:
                    config.write(cout)
                event.accept()
            elif close == QMessageBox.Cancel:
                event.ignore()
        return

    def load_config(self):
        self._loading = True
        # common settings
        if 'common' in config:
            self.spin_update_interval.setValue(config.getint('common', 'update interval', fallback=1))
            self.check_update.setCheckState(
                Qt.Checked if to_bool(config.get('common', 'update enabled', fallback='no')) else Qt.Unchecked)
        if self.settings.contains('windowGeometry'):
            self.restoreGeometry(self.settings.value('windowGeometry', ''))
        else:
            window_frame = self.frameGeometry()
            desktop_center = QDesktopWidget().availableGeometry().center()
            window_frame.moveCenter(desktop_center)
            self.move(window_frame.topLeft())
        _v = self.settings.value('windowState', '')
        if isinstance(_v, str):
            self.restoreState(_v.encode())
        else:
            self.restoreState(_v)
        self._loading = False
        return

    def set_config_value(self, section, key, value):
        if self._loading:
            return
        if section not in config:
            config[section] = {}
        config[section][key] = str(value)
        with open(args.config, 'w') as cout:
            config.write(cout)
        return

    def check_update_changed(self, new_state):
        new_state = bool(new_state == Qt.Checked)
        self.set_config_value('common', 'update enabled', new_state)
        try:
            self.timer.timeout.disconnect()
        except TypeError:
            pass
        if new_state:
            self.get_weather()
            self.timer.timeout.connect(self.get_weather)
            self.timer.setSingleShot(False)
            self.timer.start(self.spin_update_interval.value() * 60 * 1000)
            self.status_bar.showMessage(self._translate('main_window', 'Running'))
        else:
            self.timer.stop()
            self.status_bar.showMessage(self._translate('main_window', 'Done'))

    def spin_update_interval_changed(self, new_value):
        self.set_config_value('common', 'update interval', new_value)
        self.timer.setInterval(new_value * 60 * 1000)

    def get_weather(self):
        weather_data = self.meteo.get_realtime_data()
        if weather_data:
            output_folder = config.get('saving', 'folder', fallback=os.path.curdir)
            if not os.path.exists(output_folder):
                os.mkdir(output_folder, mode=0o700)
            if not os.path.exists(output_folder) or not os.path.isdir(output_folder):
                output_folder = os.path.curdir
            file_prefix = config.get('saving', 'prefix', fallback='')
            now = datetime.datetime.now()
            if not os.path.exists(output_folder):
                os.mkdir(output_folder)
            elif not os.path.isdir(output_folder):
                os.remove(output_folder)
                os.mkdir(output_folder)
            weather_data['time'] = now.isoformat()
            weather_data['timestamp'] = now.timestamp()
            with gzip.open(
                    os.path.join(
                        output_folder,
                        f'{file_prefix}{now.strftime("%Y%m%d%H%M%S%f")}.json.gz'
                    ), 'wb') as f:
                f.write(json.dumps(weather_data, indent=4).encode())
            self.label_temperature_inside_value.setText(f'{weather_data["InsideTemp"]:.1f}')
            self.label_temperature_outside_value.setText(f'{weather_data["OutsideTemp"]:.1f}')
            self.label_humidity_inside_value.setText(f'{weather_data["InsideHum"]:.0f}')
            self.label_humidity_outside_value.setText(f'{weather_data["OutsideHum"]:.0f}')
            self.label_wind_speed_value.setText(f'{weather_data["WindSpeed"]:.0f}')
            self.label_wind_average_value.setText(f'{weather_data["AvgWindSpeed"]:.0f}')
            self.label_wind_direction_value.setText(f'{weather_data["WindDir"]:.0f}')
            self.label_rain_rate_value.setText(f'{weather_data["RainRate"]:.2f}')
            self.label_rain_day_value.setText(f'{weather_data["RainDay"]:.2f}')
            self.label_rain_month_value.setText(f'{weather_data["RainMonth"]:.2f}')
            self.status_bar.showMessage(f'{self._translate("main_window", "Last Update")}: {weather_data["time"]}')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='Dallas Meteo Logger')

    ap.add_argument('-c', '--config', help='configuration file',
                    default=f'{os.path.splitext(__file__)[0]}.ini')

    args = ap.parse_args()

    config = configparser.ConfigParser()
    config.read(args.config)

    make_desktop_launcher()

    app = QApplication(sys.argv)
    window = App()
    window.show()
    app.exec_()
