#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os
import sys
import configparser
import argparse
from PyQt5.QtCore import Qt, QMetaObject, QCoreApplication, QTimer, QSettings
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import QApplication, \
    QMainWindow, QWidget, QDesktopWidget, \
    QGridLayout, QFormLayout, \
    QGroupBox, QLabel, QCheckBox, QSpinBox, QStatusBar, QMessageBox
from datetime import datetime

import temperature_backend


class UiMainWindow(object):
    def __init__(self):
        self.labels_temperature = []
        self.labels_temperature_value = []
        self.central_widget = QWidget()
        self.grid_layout_main = QGridLayout(self.central_widget)
        self.group_temperature = QGroupBox(self.central_widget)
        self.grid_layout_temperature = QGridLayout(self.group_temperature)
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
        icon.addPixmap(QPixmap(os.path.join(os.path.split(__file__)[0], 'crimea-eng-circle.svg')), QIcon.Normal,
                       QIcon.Off)
        main_window.setWindowIcon(icon)

        for i in range(5):
            self.labels_temperature.append(QLabel(self.group_temperature))
            self.grid_layout_temperature.addWidget(self.labels_temperature[-1], i, 0, 1, 1)
            self.labels_temperature_value.append(QLabel(self.group_temperature))
            self.labels_temperature_value[-1].setTextInteractionFlags(_value_label_interaction_flags)
            self.grid_layout_temperature.addWidget(self.labels_temperature_value[-1], i, 1, 1, 1)

        self.grid_layout_main.addWidget(self.group_temperature, 0, 0, 1, 1)
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
        main_window.setWindowTitle(self._translate('main_window', 'Arduino Temperature'))
        self.group_temperature.setTitle(self._translate('main_window', 'Temperature [°C]'))
        for i in range(len(self.labels_temperature)):
            self.labels_temperature[i].setText(self._translate('main_window', 'Sensor') + ' {i}:'.format(i=i+1))
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


def make_desktop_launcher():
    desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
    desktop_entry_path = os.path.join(desktop_path, 'Arduino Temperature.desktop')
    if not os.path.exists(desktop_entry_path):
        try:
            import stat
            with open(desktop_entry_path, 'w') as fout:
                fout.writelines('\n'.join([
                    '[Desktop Entry]',
                    'Version=1.0',
                    'Name=Arduino Temperature',
                    'Comment=Arduino Temperature Logger, 2019',
                    'Exec=python3 ' + os.path.abspath(__file__),
                    'Icon=' + os.path.join(os.path.split(os.path.abspath(__file__))[0], 'crimea-eng-circle.svg'),
                    'Path=' + os.path.split(os.path.abspath(__file__))[0],
                    'Terminal=true',
                    'Type=Application',
                    'Categories=Science;Utility;',
                ]))
            os.chmod(desktop_entry_path, stat.S_IRUSR | stat.S_IXUSR)
        except (ImportError, PermissionError, IOError):
            pass
        else:
            print('created shortcut', desktop_entry_path)


class App(QMainWindow, UiMainWindow):
    def __init__(self):
        super().__init__()
        self.setup_ui(self)
        self.settings = QSettings('SavSoft', 'Arduino Temperature Logger')
        self.timer = QTimer()
        self.arduino = temperature_backend.Dallas18B20()
        self.arduino.start()
        # add slots events
        self.check_update.stateChanged.connect(self.check_update_changed)
        self.spin_update_interval.valueChanged.connect(self.spin_update_interval_changed)
        self._loading = False
        # config
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
                self.arduino.join(timeout=1)
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
            self.check_update.setCheckState(Qt.Checked if to_bool(config.get('common', 'update enabled', fallback='no'))
                                            else Qt.Unchecked)
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
            self.timer.timeout.connect(self.get_temperatures)
            self.timer.setSingleShot(False)
            self.timer.start(self.spin_update_interval.value() * 60 * 1000)
            self.status_bar.showMessage(self._translate('main_window', 'Running'))
        else:
            self.timer.stop()
            self.status_bar.showMessage(self._translate('main_window', 'Done'))

    def spin_update_interval_changed(self, new_value):
        self.set_config_value('common', 'update interval', new_value)
        self.timer.setInterval(new_value * 60 * 1000)

    def get_temperatures(self):
        temperatures = self.arduino.temperatures
        time = datetime.now().ctime()
        if temperatures:
            for i in range(len(self.labels_temperature_value)):
                if i < len(temperatures):
                    self.labels_temperature_value[i].setText('{:.2f}'.format(temperatures[i]))
                else:
                    self.labels_temperature_value[i].setText('N/A')
            self.status_bar.showMessage('{label}: {value}'.format(label=self._translate('main_window', 'Last Update'),
                                                                  value=time))
            with open('Dallas18B20.csv', 'a') as fout:
                fout.write(time + '\t' + '\t'.join(map(lambda t: '{:.2f}'.format(t), temperatures)) + '\n')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='Arduino Temperature Logger')

    ap.add_argument('-c', '--config', help='configuration file',
                    default='{filename}.ini'.format(filename=os.path.splitext(__file__)[0]))

    args = ap.parse_args()

    config = configparser.ConfigParser()
    config.read(args.config)

    make_desktop_launcher()

    app = QApplication(sys.argv)
    window = App()
    window.show()
    app.exec_()
