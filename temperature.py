#!/usr/bin/python3
# -*- coding: utf-8 -*-

import argparse
import os
import sys
from datetime import datetime
from typing import List

from PyQt5.QtCore import Qt, QMetaObject, QCoreApplication, QTimer, QSettings
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import QApplication, \
    QMainWindow, QWidget, QDesktopWidget, \
    QGridLayout, QFormLayout, \
    QGroupBox, QLabel, QCheckBox, QSpinBox, QStatusBar, QMessageBox

import temperature_backend


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
                    f'Comment=Arduino Temperature Logger, {datetime.now().year}',
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


class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.central_widget: QWidget = QWidget()
        self.grid_layout_main: QGridLayout = QGridLayout(self.central_widget)

        self.group_temperature: QGroupBox = QGroupBox(self.central_widget)
        self.grid_layout_temperature: QGridLayout = QGridLayout(self.group_temperature)
        self.labels_sensor: List[QLabel] = []
        self.label_temperature_label: QLabel = QLabel(self.group_temperature)
        self.labels_temperature_value: List[QLabel] = []
        self.label_state_label: QLabel = QLabel(self.group_temperature)
        self.checks_state_value: List[QCheckBox] = []
        self.label_setpoint_label: QLabel = QLabel(self.group_temperature)
        self.spins_setpoint_value: List[QSpinBox] = []

        self.check_auto_mode: QCheckBox = QCheckBox(self.group_temperature)

        self.form_layout_update: QFormLayout = QFormLayout()
        self.check_update: QCheckBox = QCheckBox(self.group_temperature)
        self.spin_update_interval: QSpinBox = QSpinBox(self.group_temperature)

        self.status_bar: QStatusBar = QStatusBar()
        self._translate = QCoreApplication.translate

        self.setup_ui(self)
        self.settings = QSettings('SavSoft', 'Arduino Temperature Logger')
        self.timer = QTimer()
        self.arduino = temperature_backend.Dallas18B20()
        self.arduino.start()
        # add slots events
        self.check_auto_mode.blockSignals(True)
        self.check_auto_mode.stateChanged.connect(self.check_auto_mode_changed)
        self.check_auto_mode.blockSignals(False)
        self.check_update.stateChanged.connect(self.check_update_changed)
        self.spin_update_interval.valueChanged.connect(self.spin_update_interval_changed)
        self._loading = False
        # config
        self.load_config()

        QTimer().singleShot(7654, self.update_values)

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
            self.labels_sensor.append(QLabel(self.group_temperature))
            self.grid_layout_temperature.addWidget(self.labels_sensor[-1], i + 1, 0, 1, 1)
            self.labels_temperature_value.append(QLabel(self.group_temperature))
            self.labels_temperature_value[-1].setTextInteractionFlags(_value_label_interaction_flags)
            self.grid_layout_temperature.addWidget(self.labels_temperature_value[-1], i + 1, 1, 1, 1)
            self.checks_state_value.append(QCheckBox(self.group_temperature))
            self.checks_state_value[-1].toggled.connect(self.check_state_value_toggled)
            self.checks_state_value[-1].setEnabled(False)
            self.grid_layout_temperature.addWidget(self.checks_state_value[-1], i + 1, 2, 1, 1)
            self.spins_setpoint_value.append(QSpinBox(self.group_temperature))
            self.spins_setpoint_value[-1].setMaximum(42)
            self.spins_setpoint_value[-1].blockSignals(True)
            self.spins_setpoint_value[-1].valueChanged.connect(self.spin_setpoint_value_changed)
            self.spins_setpoint_value[-1].blockSignals(False)
            self.grid_layout_temperature.addWidget(self.spins_setpoint_value[-1], i + 1, 3, 1, 1)

        self.grid_layout_temperature.addWidget(self.label_temperature_label, 0, 1, 1, 1)
        self.grid_layout_temperature.addWidget(self.label_state_label, 0, 2, 1, 1)
        self.grid_layout_temperature.addWidget(self.label_setpoint_label, 0, 3, 1, 1)

        self.grid_layout_temperature.addWidget(self.check_auto_mode, 6, 0, 1, 4)

        self.grid_layout_main.addWidget(self.group_temperature, 0, 0, 1, 1)
        self.form_layout_update.setWidget(0, QFormLayout.LabelRole, self.check_update)
        self.spin_update_interval.setRange(1, 1440)
        self.form_layout_update.setWidget(0, QFormLayout.FieldRole, self.spin_update_interval)
        self.grid_layout_temperature.addLayout(self.form_layout_update, 7, 0, 1, 4)
        main_window.setCentralWidget(self.central_widget)
        main_window.setStatusBar(self.status_bar)
        self.retranslate_ui(main_window)
        QMetaObject.connectSlotsByName(main_window)
        main_window.adjustSize()

    def retranslate_ui(self, main_window):
        main_window.setWindowTitle(self._translate('main_window', 'Arduino Temperature'))
        self.label_temperature_label.setText(self._translate('main_window', 'T [°C]'))
        self.label_state_label.setText(self._translate('main_window', 'State'))
        self.label_setpoint_label.setText(self._translate('main_window', 'SP [°C]'))
        for i in range(len(self.labels_sensor)):
            self.labels_sensor[i].setText(self._translate('main_window', 'Sensor') + f' {i + 1}:')
        self.check_auto_mode.setText(self._translate('main_window', 'Automatic'))
        self.check_update.setText(self._translate('main_window', 'Update Every'))
        self.spin_update_interval.setSuffix(self._translate('main_window', ' min'))

    def closeEvent(self, event):
        """ senseless joke in the loop """
        close_code = QMessageBox.No
        while close_code == QMessageBox.No:
            try:
                close = QMessageBox()
                close.setText(self._translate('main_window', 'Are you sure?'))
                close.setIcon(QMessageBox.Question)
                close.setWindowIcon(self.windowIcon())
                close.setWindowTitle(self.windowTitle())
                close.setStandardButtons(QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
                close_code = close.exec()
            except (KeyboardInterrupt, SystemExit):
                close_code = QMessageBox.Yes
            if close_code == QMessageBox.Yes:
                self.arduino.join(timeout=1)
                self.settings.setValue('windowGeometry', self.saveGeometry())
                self.settings.setValue('windowState', self.saveState())
                self.settings.sync()
                event.accept()
            elif close_code == QMessageBox.Cancel:
                event.ignore()
        return

    def load_config(self):
        self._loading = True
        # common settings
        self.spin_update_interval.setValue(self.get_config_value('update', 'interval', 1, int))
        self.check_update.setCheckState(Qt.Checked if self.get_config_value('update', 'enabled', False, bool)
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

    def get_config_value(self, section, key, default, _type):
        if section not in self.settings.childGroups():
            return default
        self.settings.beginGroup(section)
        # print('get', section, key)
        try:
            v = self.settings.value(key, default, _type)
        except TypeError:
            v = default
        self.settings.endGroup()
        return v

    def set_config_value(self, section, key, value):
        if self._loading:
            return
        self.settings.beginGroup(section)
        # print('set', section, key, value, type(value))
        self.settings.setValue(key, value)
        self.settings.endGroup()

    def check_auto_mode_changed(self, new_state):
        if new_state in (Qt.Unchecked, Qt.Checked):
            {Qt.Unchecked: self.arduino.disable, Qt.Checked: self.arduino.enable}[new_state]()
            for cb in self.checks_state_value:
                cb.setEnabled(new_state == Qt.Unchecked)
            for sb in self.spins_setpoint_value:
                sb.setEnabled(new_state == Qt.Checked)

    def check_update_changed(self, new_state):
        new_state = bool(new_state == Qt.Checked)
        self.set_config_value('update', 'enabled', new_state)
        try:
            self.timer.timeout.disconnect()
        except TypeError:
            pass
        if new_state:
            self.timer.timeout.connect(self.update_values)
            self.timer.setSingleShot(False)
            self.timer.start(self.spin_update_interval.value() * 60 * 1000)
            self.status_bar.showMessage(self._translate('main_window', 'Running'))
        else:
            self.timer.stop()
            self.status_bar.showMessage(self._translate('main_window', 'Done'))

    def spin_update_interval_changed(self, new_value):
        self.set_config_value('update', 'interval', new_value)
        self.timer.setInterval(new_value * 60 * 1000)

    def check_state_value_toggled(self, new_state):
        index: int = self.arduino.D_MAX - self.checks_state_value.index(self.sender())
        if self.arduino.D_MIN <= index <= self.arduino.D_MAX:
            self.arduino.set_digital(index,
                                     new_state == Qt.Unchecked)  # remember the reversed logic

    def spin_setpoint_value_changed(self, new_value: int):
        self.arduino.set_setpoint(self.spins_setpoint_value.index(self.sender()), new_value)

    def update_values(self):
        temperatures: List[float] = self.arduino.temperatures
        states = self.arduino.states
        setpoints = self.arduino.setpoints
        enabled = self.arduino.enabled
        time = datetime.now().ctime()
        for i in range(len(self.labels_temperature_value)):
            if i < len(temperatures):
                self.labels_temperature_value[i].setNum(round(temperatures[i], 2))
            else:
                self.labels_temperature_value[i].setText('N/A')
        for i in range(len(self.checks_state_value)):
            self.checks_state_value[i].blockSignals(True)
            if i < len(states):
                self.checks_state_value[i].setCheckState(Qt.Checked if states[i] else Qt.Unchecked)
            else:
                self.checks_state_value[i].setCheckState(Qt.PartiallyChecked)
            self.checks_state_value[i].blockSignals(False)
        for i in range(len(self.spins_setpoint_value)):
            if i < len(setpoints):
                self.spins_setpoint_value[i].blockSignals(True)
                self.spins_setpoint_value[i].setValue(setpoints[i])
                self.spins_setpoint_value[i].blockSignals(False)
        if temperatures:
            with open('Dallas18B20.csv', 'a') as fout:
                sep: str = ','
                fout.write(time + sep + sep.join(map(lambda t: f'{t:.2f}', temperatures)) + '\n')
        self.check_auto_mode.blockSignals(True)
        self.check_auto_mode.setTristate(enabled is None)
        self.check_auto_mode.setCheckState({False: Qt.Unchecked, None: Qt.PartiallyChecked, True: Qt.Checked}[enabled])
        self.check_auto_mode.blockSignals(False)
        if enabled in (Qt.Unchecked, Qt.Checked):
            for cb in self.checks_state_value:
                cb.setEnabled(enabled == Qt.Unchecked)
            for sb in self.spins_setpoint_value:
                sb.setEnabled(enabled == Qt.Checked)
        self.status_bar.showMessage(f'{self._translate("main_window", "Last Update")}: {time}')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='Arduino Temperature Logger')
    ap.parse_args()

    make_desktop_launcher()

    app = QApplication(sys.argv)
    window = App()
    window.show()
    app.exec_()
