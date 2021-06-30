#!/usr/bin/python3
# -*- coding: utf-8 -*-

# TODO: emulate “ldevio” app with a Python script to check the re-connection when the number of the channels changes
# TODO: translate most of the stuff into Russian

import argparse
import csv
import gzip
import json
import os
import socket
import sys
import time
from datetime import datetime
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Union

import matplotlib.style
import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QCheckBox, QDesktopWidget, QDoubleSpinBox, \
    QHBoxLayout, QMessageBox, \
    QTableWidgetItem, QTableWidgetSelectionRange, QWidget
from matplotlib import rcParams as PlotParams
from matplotlib.axes import Axes
from matplotlib.dates import date2num
from matplotlib.legend import Legend
from matplotlib.lines import Line2D

from backend import ADCAcquisition
from dallas import Dallas
from gui import GUI
from temperature_backend import Dallas18B20
from utils import label_lines, make_desktop_launcher, stringify_list, to_bool

try:
    import smsd_dummy as smsd
except ImportError:
    import smsd
from smsd import MicrosteppingMode

matplotlib.style.use('fast')

try:
    import cycler

    PlotParams['axes.prop_cycle'] = cycler.cycler(color='brgcmyk')
except (ImportError, KeyError):
    pass

LINE_PROPERTIES: List[str] = ['color', 'dash_capstyle', 'dash_joinstyle', 'drawstyle', 'fillstyle', 'linestyle',
                              'linewidth', 'marker', 'markeredgecolor', 'markeredgewidth', 'markerfacecolor',
                              'markerfacecoloralt', 'markersize', 'markevery', 'solid_capstyle', 'solid_joinstyle']


class App(GUI):
    def __init__(self) -> None:
        super().__init__()

        self.resuming: bool = self.get_config_value('common', 'power', False, bool)

        # current schedule table row being measured
        self._current_row: Optional[int] = None
        self._init_angle: float = 0.0
        #
        self.last_loop_data = {}
        # prevent config from being re-written while loading
        self._loading: bool = True
        # config
        self.load_config_1()
        # backend
        self.bbox_to_anchor: Tuple[float, float] = (1.10, 1)

        self.adc_channels: List[int] = list(range(self.spin_channels.value()))
        self._adc_channels_names: List[str] = list(f'ch {ch + 1}' for ch in self.adc_channels)

        self.plot: Axes = self.figure.add_subplot(2, 1, 1)
        self.plot.autoscale()
        box = self.plot.get_position()
        self.plot.set_position([box.x0, box.y0, box.width * 0.8, box.height])
        self.plot.set_xlabel('Time')
        self.plot.set_ylabel('Voltage [V]')
        self.plot.set_label('Voltage')
        self.plot.set_autoscale_on(True)
        self.plot.format_coord = lambda x, y: f'voltage = {y:.3f} V'
        self.plot.callbacks.connect('xlim_changed', self.on_xlim_changed)
        self.plot.callbacks.connect('ylim_changed', self.on_ylim_changed)

        self.τ_plot: Axes = self.figure.add_subplot(2, 1, 2, sharex=self.plot)
        self.τ_plot.autoscale()
        box = self.τ_plot.get_position()
        self.τ_plot.set_position([box.x0, box.y0, box.width * 0.8, box.height])
        self.τ_plot.set_xlabel('Time')
        self.τ_plot.set_ylabel('τ')
        self.τ_plot.set_label('Absorption')
        # self.τ_plot.callbacks.connect('xlim_changed', self.on_xlim_changed)
        self.τ_plot.callbacks.connect('ylim_changed', self.on_ylim_changed)

        self._plot_lines: List[Line2D] = [self.plot.plot_date(np.empty(0), np.empty(0), label=f'ch {ch + 1}')[0]
                                          for ch in self.adc_channels]
        self._τ_plot_lines: List[Line2D] = [self.τ_plot.plot_date(np.empty(0), np.empty(0),
                                                                  label=f'ch {ch + 1}',
                                                                  color=self._plot_lines[ch].get_color(),
                                                                  ls='-')[0]
                                            for ch in range(len(self._plot_lines))]
        self._τ_plot_alt_lines: List[Line2D] = [self.τ_plot.plot_date(np.empty(0), np.empty(0),
                                                                      label=f'ch {ch + 1}',
                                                                      color=self._plot_lines[ch].get_color(),
                                                                      ls='--')[0]
                                                for ch in range(len(self._plot_lines))]
        self._τ_plot_alt_bb_lines: List[Line2D] = [self.τ_plot.plot_date(np.empty(0), np.empty(0),
                                                                         label=f'ch {ch + 1}',
                                                                         color=self._plot_lines[ch].get_color(),
                                                                         ls='--')[0]
                                                   for ch in range(len(self._plot_lines))]
        self._τ_plot_leastsq_lines: List[Line2D] = [self.τ_plot.plot_date(np.empty(0), np.empty(0),
                                                                          label=f'ch {ch + 1}',
                                                                          color=self._plot_lines[ch].get_color(),
                                                                          ls=':')[0]
                                                    for ch in range(len(self._plot_lines))]
        self._τ_plot_magic_lines: List[Line2D] = [self.τ_plot.plot_date(np.empty(0), np.empty(0),
                                                                        label=f'ch {ch + 1}',
                                                                        color=self._plot_lines[ch].get_color(),
                                                                        ls='-.')[0]
                                                  for ch in range(len(self._plot_lines))]
        # self._τ_plot_magic_alt_lines: List[Line2D] = [self.τ_plot.plot_date(np.empty(0), np.empty(0),
        #                                                                      label=f'ch {ch + 1}',
        #                                                                      color=self._plot_lines[ch].get_color(),
        #                                                                      ls='-.')[0]
        #                                               for ch in range(len(self._plot_lines))]

        self._plot_legend: Legend = self.plot.legend(loc='upper left', bbox_to_anchor=self.bbox_to_anchor)
        self._τ_plot_legend: Legend = self.τ_plot.legend(loc='upper left', bbox_to_anchor=self.bbox_to_anchor)

        self.adc_channels_names = self.adc_channels_names  # update the values

        self._wind_plot: Axes = self.τ_plot.twinx()
        self._wind_plot.set_position([box.x0, box.y0, box.width * 0.8, box.height])
        self._wind_plot.set_navigate(False)
        self.τ_plot.set_zorder(self._wind_plot.get_zorder() + 1)
        self.τ_plot.patch.set_visible(False)
        self._wind_plot.patch.set_visible(True)
        self._wind_plot.set_ylabel('Wind')
        self._wind_plot.set_label('Wind')
        self.τ_plot.format_coord = lambda x, y: 'τ = {:.3f}\nwind speed = {:.3f}'.format(
            y, self._wind_plot.transData.inverted().transform(self.τ_plot.transData.transform((x, y)))[-1])
        self._wind_plot_line, = self._wind_plot.plot_date(np.empty(0), np.empty(0), 'k:')

        def on_pick(event) -> None:
            # on the pick event, find the orig line corresponding to the
            # legend proxy line, and toggle the visibility
            _legend_line = event.artist
            if _legend_line in self._plot_legend.get_lines():
                _legend = '_plot_legend'
                _lines = self._plot_lines
                _axes = self.plot
            elif _legend_line in self._τ_plot_legend.get_lines():
                _legend = '_τ_plot_legend'
                _lines = self.τ_plot_lines
                _axes = self.τ_plot
            else:
                return
            _index = getattr(self, _legend).get_lines().index(_legend_line)
            _orig_line = _lines[_index]
            vis = not _orig_line.get_visible()
            if vis:
                _alpha = 1.0
            else:
                _alpha = 0.2
            visible_states: List[bool] = [_line.get_visible() for _line in _lines]
            for _line in _lines:
                _line.set_visible(True)
            _orig_line.set_alpha(_alpha)
            setattr(self, _legend, _axes.legend(loc='upper left', bbox_to_anchor=self.bbox_to_anchor))
            for _legend_line in getattr(self, _legend).get_lines():
                _legend_line.set_picker(True)
                _legend_line.set_pickradius(5)
            for _line, _vis in zip(_lines, visible_states):
                _line.set_visible(_vis)
            _orig_line.set_visible(vis)
            event.canvas.draw()

        self.figure.canvas.mpl_connect('pick_event', on_pick)

        self.x: np.ndarray = np.empty(0)
        self.y: List[np.ndarray] = [np.empty(0)] * len(self.adc_channels)
        self.τx: List[np.ndarray] = [np.empty(0)] * len(self.adc_channels)
        self.τy: List[np.ndarray] = [np.empty(0)] * len(self.adc_channels)
        self.τx_alt: List[np.ndarray] = [np.empty(0)] * len(self.adc_channels)
        self.τy_alt: List[np.ndarray] = [np.empty(0)] * len(self.adc_channels)
        self.τx_bb_alt: List[np.ndarray] = [np.empty(0)] * len(self.adc_channels)
        self.τy_bb_alt: List[np.ndarray] = [np.empty(0)] * len(self.adc_channels)
        self.τx_leastsq: List[np.ndarray] = [np.empty(0)] * len(self.adc_channels)
        self.τy_leastsq: List[np.ndarray] = [np.empty(0)] * len(self.adc_channels)
        # self.τy_error_leastsq: List[np.ndarray] = [np.empty(0)] * len(self.adc_channels)
        self.τx_magic: List[np.ndarray] = [np.empty(0)] * len(self.adc_channels)
        self.τy_magic: List[np.ndarray] = [np.empty(0)] * len(self.adc_channels)
        # self.τx_magic_alt: List[np.ndarray] = [np.empty(0)] * len(self.adc_channels)
        # self.τy_magic_alt: List[np.ndarray] = [np.empty(0)] * len(self.adc_channels)
        self.wind_x: np.ndarray = np.empty(0)
        self.wind_y: np.ndarray = np.empty(0)

        self._measured: bool = False

        self.motor = smsd.Motor(device='/dev/ttyS0',
                                microstepping_mode=MicrosteppingMode(index=self.spin_step_fraction.value()),
                                speed=self.spin_settings_speed.value(),
                                ratio=self.spin_settings_gear_1.value() / self.spin_settings_gear_2.value())
        self.motor.start()
        self.motor.open()

        self._measurement_delay: float = self.spin_measurement_delay.value()
        self._current_angle: float = self._init_angle

        self.weather_station: Dallas = Dallas()

        self.arduino: Dallas18B20 = Dallas18B20()
        self.arduino.start()

        self.output_folder: str = self.get_config_value('settings', 'output folder',
                                                        os.path.join(os.path.curdir, 'data'), str)
        self.summary_file_prefix: str = time.strftime("%Y%m%d%H%M%S")
        if self.summary_file_prefix:
            print('summary is stored into', ', '.join(f'{self.summary_file_prefix}.{ch + 1}.csv'
                                                      for ch in range(len(self.adc_channels))))
        self.data: List[dict] = []

        self.adc_thread: ADCAcquisition = ADCAcquisition(self.adc_channels, self.set_point)
        self.adc_thread.start()
        self.load_config_2()

        self.setup_actions()

    def setup_actions(self) -> None:
        # common
        self.tab_widget.currentChanged.connect(self.tab_widget_changed)
        # tab 1
        self.check_auto_temperature_mode.blockSignals(True)
        self.check_auto_temperature_mode.stateChanged.connect(self.check_auto_mode_changed)
        self.check_auto_temperature_mode.blockSignals(False)
        self.button_schedule_action_add.clicked.connect(self.button_schedule_action_add_clicked)
        self.button_schedule_action_remove.clicked.connect(self.button_schedule_action_remove_clicked)
        self.button_schedule_action_up.clicked.connect(self.button_schedule_action_up_clicked)
        self.button_schedule_action_down.clicked.connect(self.button_schedule_action_down_clicked)
        self.button_power.toggled.connect(self.button_power_toggled)
        self.button_power_shortcut.activated.connect(self.button_power.click)
        self.button_go.toggled.connect(self.button_go_toggled)
        self.button_go_shortcut.activated.connect(self.button_go.click)
        # tab 2
        self.spin_step_fraction.valueChanged.connect(self.step_fraction_changed)
        self.spin_settings_speed.valueChanged.connect(self.spin_settings_speed_changed)
        self.spin_settings_gear_1.valueChanged.connect(self.spin_settings_gear_1_changed)
        self.spin_settings_gear_2.valueChanged.connect(self.spin_settings_gear_2_changed)
        self.button_move_home.clicked.connect(self.button_move_home_clicked)
        self.button_move_90degrees.clicked.connect(self.button_move_90degrees_clicked)
        self.button_move_1step_right.clicked.connect(self.button_move_1step_right_clicked)
        self.button_move_1step_left.clicked.connect(self.button_move_1step_left_clicked)
        self.button_move_360degrees_right.clicked.connect(self.button_move_360degrees_right_clicked)
        self.button_move_360degrees_left.clicked.connect(self.button_move_360degrees_left_clicked)
        self.spin_channels.valueChanged.connect(self.spin_channels_changed)
        self.spin_measurement_delay.valueChanged.connect(self.spin_measurement_delay_changed)
        self.spin_bb_angle.valueChanged.connect(self.spin_bb_angle_changed)
        self.spin_bb_angle_alt.valueChanged.connect(self.spin_bb_angle_alt_changed)
        self.spin_max_angle.valueChanged.connect(self.spin_max_angle_changed)
        self.spin_min_angle.valueChanged.connect(self.spin_min_angle_changed)
        self.spin_min_angle_alt.valueChanged.connect(self.spin_min_angle_alt_changed)
        # dirty hack: the event doesn't work directly for subplots
        self.canvas.mpl_connect('button_press_event', self.on_click)

    def closeEvent(self, event) -> None:
        """ senseless joke in the loop """
        close = QMessageBox.No
        while close == QMessageBox.No:
            close = QMessageBox()
            close.setText('Are you sure?')
            close.setIcon(QMessageBox.Question)
            close.setWindowIcon(self.windowIcon())
            close.setWindowTitle(self.windowTitle())
            close.setStandardButtons(QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            close = close.exec()

            if close == QMessageBox.Yes:
                self.save_plot_config()
                self.set_config_value('common', 'power', False)
                self.table_schedule_changed()
                self.settings.setValue('windowGeometry', self.saveGeometry())
                self.settings.setValue('windowState', self.saveState())
                self.settings.sync()
                self.pd.reset()
                self.adc_thread.close()
                self.adc_thread.join()
                self.motor.disable()
                self.motor.join()
                self.arduino.stop()
                # FIXME: the following line causes double channel count changes
                # self.arduino.join(timeout=1)
                event.accept()
            elif close == QMessageBox.Cancel:
                event.ignore()
        return

    def load_config_1(self) -> None:
        self._loading = True
        # common settings
        self.tab_widget.setCurrentIndex(self.get_config_value('common', 'current tab', 0, int))
        self._init_angle = self.get_config_value('common', 'last angle', 0, float)
        if self.settings.contains('windowGeometry'):
            self.restoreGeometry(self.settings.value("windowGeometry", ""))
        else:
            window_frame = self.frameGeometry()
            desktop_center = QDesktopWidget().availableGeometry().center()
            window_frame.moveCenter(desktop_center)
            self.move(window_frame.topLeft())
        _v = self.settings.value("windowState", "")
        if isinstance(_v, str):
            self.restoreState(_v.encode())
        else:
            self.restoreState(_v)
        # tab 2
        self.spin_step_fraction.setValue(self.get_config_value('motor', 'step fraction', 0, int))
        self.spin_settings_speed.setValue(self.get_config_value('motor', 'speed', 42, int))
        self.spin_settings_gear_1.setValue(self.get_config_value('motor', 'gear 1 size', 100, int))
        self.spin_settings_gear_2.setValue(self.get_config_value('motor', 'gear 2 size', 98, int))
        self.spin_measurement_delay.setValue(self.get_config_value('settings', 'delay before measuring', 8, float))
        self.spin_channels.setValue(self.get_config_value('settings', 'number of channels', 1, int))
        self._loading = False
        return

    def load_config_2(self) -> None:
        self._loading = True
        # tab 1
        table_text: str = self.get_config_value('schedule', 'table', '', str)
        if table_text:
            self.table_schedule.setRowCount(0)
            table: List[str] = table_text.splitlines()[self.get_config_value('schedule', 'skip lines', 0, int):]
            conversions = [to_bool, float, float]
            for row in table:
                cells = row.split()
                cells = [f(x) for f, x in zip(conversions, cells)]
                self.add_table_row(values=cells)
        self.button_power.setChecked(self.resuming)
        self.button_go.setEnabled(bool(self.button_power.isChecked() and table_text))
        self.table_schedule_row_enabled(Qt.Unchecked)
        # tab 2
        self.spin_bb_angle.setValue(self.get_config_value('settings', 'black body position', 0, float))
        self.spin_bb_angle_alt.setValue(self.get_config_value('settings', 'black body position alt', 0, float))
        self.spin_max_angle.setValue(self.get_config_value('settings', 'zenith position', 90, float))
        self.spin_min_angle.setValue(self.get_config_value('settings', 'horizon position', 15, float))
        self.spin_min_angle_alt.setValue(self.get_config_value('settings', 'horizon position alt', 20, float))

        check_states = [to_bool(b) for b in self.get_config_value('settings', 'voltage channels', '', str).split()]
        self.plot_lines_visibility = check_states
        check_states = [to_bool(b) for b in self.get_config_value('settings', 'absorption channels', '', str).split()]
        self.τ_plot_lines_visibility = check_states
        props: List[Dict[str, Union[str, float, None]]] = self.plot_lines_styles
        for index, p in enumerate(props):
            for key, value in p.items():
                if 'color' in key:
                    p[key] = self.get_config_value('settings', f'voltage line {index} {key}', value,
                                                   Union[str, Tuple[float, ...]])
                else:
                    p[key] = self.get_config_value('settings', f'voltage line {index} {key}', value, type(value))
        self.plot_lines_styles = props
        props: List[Dict[str, Union[str, float, None]]] = self.τ_plot_lines_styles
        for index, p in enumerate(props):
            for key, value in p.items():
                if 'color' in key:
                    p[key] = self.get_config_value('settings', f'absorption line {index} {key}', value,
                                                   Union[str, Tuple[float, ...]])
                else:
                    p[key] = self.get_config_value('settings', f'absorption line {index} {key}', value, type(value))
        self.τ_plot_lines_styles = props

        props: Dict[str, float] = self.subplotpars
        for key, value in props.items():
            props[key] = self.get_config_value('subplots', key, value, float)
        self.subplotpars = props

        self.move_legends((self.get_config_value('plotLegendsPosition', 'left', 1.1, float),
                           self.get_config_value('plotLegendsPosition', 'top', 1.0, float)))

        self.adc_channels_names = [self.get_config_value('labels', str(ch), '', str)
                                   for ch in range(self.spin_channels.value())]

        self._loading = False
        self.button_power_toggled(self.resuming)

    def save_plot_config(self) -> None:
        self.set_config_value('settings', 'voltage channels',
                              stringify_list(self.plot_lines_visibility))
        self.set_config_value('settings', 'absorption channels',
                              stringify_list(self.τ_plot_lines_visibility))
        props: List[Dict[str, Union[str, float, None]]] = self.plot_lines_styles
        for index, p in enumerate(props):
            for key, value in p.items():
                self.set_config_value('settings', f'voltage line {index} {key}', value)
        props: List[Dict[str, Union[str, float, None]]] = self.τ_plot_lines_styles
        for index, p in enumerate(props):
            for key, value in p.items():
                self.set_config_value('settings', f'absorption line {index} {key}', value)

        props: Dict[str, float] = self.subplotpars
        for key, value in props.items():
            self.set_config_value('subplots', key, value)

        self.set_config_value('plotLegendsPosition', 'left', round(float(self.bbox_to_anchor[0]), 3))
        self.set_config_value('plotLegendsPosition', 'top', round(float(self.bbox_to_anchor[1]), 3))

        for ch in range(self.spin_channels.value()):
            self.set_config_value('labels', str(ch), self.adc_channels_names[ch])

    def get_config_value(self, section, key, default, _type) -> Union[bool, int, float, str, Tuple[float, ...]]:
        if section not in self.settings.childGroups():
            return default
        self.settings.beginGroup(section)
        if _type is Union[str, Tuple[float, ...]]:
            v = self.settings.value(key, default, str)
            vs = v.split()
            if len(vs) > 1:
                v = tuple(map(float, vs))
            # print('get', section, key, v, _type)
        else:
            try:
                v = self.settings.value(key, default, _type)
                # print('get', section, key, v, _type)
            except TypeError:
                v = default
                # print('get', section, key, v, '(default)', _type)
        self.settings.endGroup()
        return v

    def set_config_value(self, section, key, value) -> None:
        if self._loading:
            return
        self.settings.beginGroup(section)
        # print('set', section, key, value, type(value))
        if isinstance(value, tuple):
            self.settings.setValue(key, ' '.join(map(str, value)))
        else:
            self.settings.setValue(key, value)
        self.settings.endGroup()

    def stringify_table(self) -> Tuple[str, int]:
        header = 'enabled angle delay'
        lines = [header]
        for r in range(self.table_schedule.rowCount()):
            values = []
            w = self.table_schedule.cellWidget(r, 0)
            if w is not None:
                w2 = w.findChild(QCheckBox, '', Qt.FindDirectChildrenOnly)
                if w2 is not None:
                    values.append(w2.checkState() == Qt.Checked)
                    for c in range(1, self.table_schedule.columnCount()):
                        w1 = self.table_schedule.cellWidget(r, c)
                        if w1 is not None:
                            values.append(w1.value())
            lines += [stringify_list(values)]
        return os.linesep.join(lines), len(header.splitlines())

    def tab_widget_changed(self, index) -> None:
        self.set_config_value('common', 'current tab', index)
        return

    def check_auto_mode_changed(self, new_state) -> None:
        if new_state in (Qt.Unchecked, Qt.Checked):
            {Qt.Unchecked: self.arduino.disable, Qt.Checked: self.arduino.enable}[new_state]()
            for cb in self.checks_state_value:
                cb.setEnabled(new_state == Qt.Unchecked)
            for sb in self.spins_setpoint_value:
                sb.setEnabled(new_state == Qt.Checked)

    def button_schedule_action_add_clicked(self) -> None:
        self.add_table_row(self.table_schedule.currentRow() + 1)
        return

    def check_state_value_toggled(self, new_state: Qt.CheckState) -> None:
        # noinspection PyTypeChecker
        index: int = self.arduino.D_MAX - self.checks_state_value.index(self.sender())
        if self.arduino.D_MIN <= index <= self.arduino.D_MAX:
            self.arduino.set_digital(index, new_state == Qt.Unchecked)  # remember the reversed logic

    def spin_setpoint_value_changed(self, new_value: int) -> None:
        # noinspection PyTypeChecker
        self.arduino.set_setpoint(self.spins_setpoint_value.index(self.sender()), new_value)

    def update_temperature_values(self) -> None:
        temperatures: List[float] = self.arduino.temperatures
        states = self.arduino.states
        setpoints = self.arduino.setpoints
        enabled = self.arduino.enabled
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
        self.check_auto_temperature_mode.blockSignals(True)
        self.check_auto_temperature_mode.setTristate(enabled is None)
        self.check_auto_temperature_mode.setCheckState(
            {False: Qt.Unchecked, None: Qt.PartiallyChecked, True: Qt.Checked}[enabled])
        self.check_auto_temperature_mode.blockSignals(False)
        if enabled in (Qt.Unchecked, Qt.Checked):
            for cb in self.checks_state_value:
                cb.setEnabled(enabled == Qt.Unchecked)
            for sb in self.spins_setpoint_value:
                sb.setEnabled(enabled == Qt.Checked)

    def add_table_row(self, row_position: Optional[int] = None, values=None) -> None:
        if row_position is None or row_position < 0:
            row_position = self.table_schedule.rowCount()
        self.table_schedule.insertRow(row_position)

        step: float = self.motor.step

        item: QDoubleSpinBox = QDoubleSpinBox()
        item.setRange(-180, 180)
        item.setDecimals(2)
        item.setSuffix('°')
        item.setSingleStep(step)
        angle: float
        if values and isinstance(values, (list, tuple)) and len(values) > 1:
            angle = round(values[1] / step) * step
        elif row_position > 0:
            angle = round((self.table_schedule.cellWidget(row_position - 1, 1).value()
                           + item.singleStep() * 10) / step) * step
        elif row_position == 0:
            angle = 0.0
        else:
            raise ValueError('Invalid position')
        item.setValue(angle)
        self.table_schedule.setCellWidget(row_position, 1, item)
        item.editingFinished.connect(self.table_schedule_changed)

        item: QDoubleSpinBox = QDoubleSpinBox()
        item.setRange(1, 86400)
        item.setDecimals(1)
        item.setSuffix(' s')
        item.setSingleStep(1)
        if values and (isinstance(values, tuple) or isinstance(values, list)) and len(values) > 2:
            item.setValue(values[2])
        elif row_position > 0:
            item.setValue(self.table_schedule.cellWidget(row_position - 1, 2).value())
        self.table_schedule.setCellWidget(row_position, 2, item)
        item.editingFinished.connect(self.table_schedule_changed)

        item: QCheckBox = QCheckBox()
        parent_widget = QWidget()
        parent_widget.setStyleSheet("background-color: rgba(0,0,0,0)")
        parent_widget_layout = QHBoxLayout()
        parent_widget_layout.addWidget(item)
        parent_widget_layout.setAlignment(Qt.AlignCenter)
        parent_widget_layout.setContentsMargins(0, 0, 0, 0)
        parent_widget.setLayout(parent_widget_layout)
        self.table_schedule.setItem(row_position, 0, QTableWidgetItem())
        self.table_schedule.setCellWidget(row_position, 0, parent_widget)
        self.table_schedule.setColumnWidth(0, self.table_schedule.rowHeight(row_position))
        if values and (isinstance(values, tuple) or isinstance(values, list)) and len(values) > 0:
            item.setCheckState(Qt.Checked if values[0] else Qt.Unchecked)
        else:
            item.setCheckState(Qt.Checked)
        item.stateChanged.connect(self.table_schedule_row_enabled)

        self.button_go.setEnabled(bool(self.table_schedule.rowCount() > 0 and self.button_power.isChecked()))

        # why doesn't it work by itself??!
        if values and not values[0]:
            for c in range(1, self.table_schedule.columnCount()):
                w1 = self.table_schedule.cellWidget(row_position, c)
                if w1 is not None:
                    w1.setEnabled(values[0])

        self.table_schedule.selectRow(row_position)

        if self._current_row is not None:
            if row_position <= self._current_row:
                self._current_row += 1
            self.highlight_current_row()
        return

    def button_schedule_action_remove_clicked(self) -> None:
        rows_to_be_removed = []
        for r in self.table_schedule.selectedRanges():
            for i in range(r.topRow(), r.bottomRow() + 1):
                if i not in rows_to_be_removed:
                    rows_to_be_removed += [i]
        rows_to_be_removed.sort()
        for i in rows_to_be_removed[::-1]:
            self.table_schedule.removeRow(i)
        self.button_go.setEnabled(bool(self.table_schedule.rowCount() > 0 and self.button_power.isChecked()))
        if self._current_row is not None:
            self._current_row -= np.count_nonzero(np.array(rows_to_be_removed) < self._current_row)
        self.highlight_current_row()
        return

    def table_schedule_row_enabled(self, new_state: Qt.CheckState) -> None:
        self.table_schedule_changed()
        for r in range(self.table_schedule.rowCount()):
            w: Optional[QWidget] = self.table_schedule.cellWidget(r, 0)
            if w is None:
                continue
            w2: Optional[QWidget] = w.childAt(w.childrenRect().center())
            if w2 is None:
                continue
            w2ch: Qt.CheckState = w2.checkState()
            if w2ch == new_state:
                for c in range(1, self.table_schedule.columnCount()):
                    w1: Optional[QWidget] = self.table_schedule.cellWidget(r, c)
                    if w1 is not None:
                        w1.setEnabled(w2ch != Qt.Unchecked)
        something_enabled: bool = bool(self.enabled_rows())
        self.button_go.setEnabled(something_enabled and self.button_power.isChecked())
        if not something_enabled:
            self.button_go.setChecked(False)
        return

    def table_schedule_changed(self) -> None:
        if self._loading:
            return

        # validate angles
        step: float = self.motor.step
        for r in range(self.table_schedule.rowCount()):
            w: Optional[QWidget] = self.table_schedule.cellWidget(r, 1)
            if w is None:  # in case of emergency
                continue
            angle: float = w.value()
            w.blockSignals(True)
            w.setValue(round(angle / step) * step)
            w.blockSignals(False)

        st, sl = self.stringify_table()
        self.set_config_value('schedule', 'table', st)
        self.set_config_value('schedule', 'skip lines', sl)

    @staticmethod
    def move_row_down(table, row) -> int:
        if row < table.rowCount() - 1:
            table.setRowHidden(row, True)
            table.insertRow(row + 2)
            for c in range(table.columnCount()):
                table.setItem(row + 2, c, table.takeItem(row, c))
                table.setCellWidget(row + 2, c, table.cellWidget(row, c))
            table.removeRow(row)
            return row + 1
        return row

    @staticmethod
    def move_row_up(table, row) -> int:
        if row > 0:
            table.setRowHidden(row, True)
            table.insertRow(row - 1)
            for c in range(table.columnCount()):
                table.setItem(row - 1, c, table.takeItem(row + 1, c))
                table.setCellWidget(row - 1, c, table.cellWidget(row + 1, c))
            table.removeRow(row + 1)
            return row - 1
        return row

    def button_schedule_action_up_clicked(self) -> None:
        rows_to_be_raised = []
        for r in self.table_schedule.selectedRanges():
            for i in range(r.topRow(), r.bottomRow() + 1):
                if i > 0 and i not in rows_to_be_raised:
                    rows_to_be_raised.append(i)
        rows_to_be_raised.sort()
        current_row_shift: int = 0
        for r in rows_to_be_raised:
            new_r: int = self.move_row_up(self.table_schedule, r)
            if r >= self._current_row > new_r:
                current_row_shift += 1
            self.table_schedule.setRangeSelected(QTableWidgetSelectionRange(r - 1, 0, r - 1,
                                                                            self.table_schedule.columnCount() - 1),
                                                 True)
        if self._current_row is not None:
            self._current_row -= current_row_shift
        self.highlight_current_row()
        return

    def button_schedule_action_down_clicked(self) -> None:
        rows_to_be_sunken = []
        for r in self.table_schedule.selectedRanges():
            for i in range(r.topRow(), r.bottomRow() + 1):
                if i < self.table_schedule.rowCount() - 1 and i not in rows_to_be_sunken:
                    rows_to_be_sunken.append(i)
        rows_to_be_sunken.sort()
        current_row_shift: int = 0
        for r in rows_to_be_sunken[::-1]:
            new_r = self.move_row_down(self.table_schedule, r)
            if r <= self._current_row < new_r:
                current_row_shift += 1
            self.table_schedule.setRangeSelected(QTableWidgetSelectionRange(r + 1, 0, r + 1,
                                                                            self.table_schedule.columnCount() - 1),
                                                 True)
        if self._current_row is not None:
            self._current_row += current_row_shift
        self.highlight_current_row()
        return

    def highlight_current_row(self, enabled: bool = True) -> None:
        for row in range(0, self.table_schedule.rowCount()):
            if enabled and row != self._current_row:
                cw = self.table_schedule.cellWidget(row, 0)
                if cw:
                    cw.setStyleSheet("background-color: rgba(0,0,0,0)")
        if enabled and self._current_row is not None:
            cw = self.table_schedule.cellWidget(self._current_row, 0)
            if cw:
                cw.setStyleSheet("background-color: green")
            # scroll to the next row
            self.table_schedule.scrollToItem(self.table_schedule.item(self._current_row, 0))
        return

    def enabled_rows(self) -> List[int]:
        rows: List[int] = []
        for r in range(self.table_schedule.rowCount()):
            w: Optional[QWidget] = self.table_schedule.cellWidget(r, 0)
            duration: float = self.table_schedule.cellWidget(r, 2).value()
            if duration > 0.0 and w is not None:
                # noinspection PyTypeChecker
                w2: Optional[QCheckBox] = w.findChild(QCheckBox, '', Qt.FindDirectChildrenOnly)
                if w2 is not None and w2.checkState():
                    rows += [r]
        return rows

    def next_enabled_row(self, row: Optional[int]) -> Optional[int]:
        if row is None:
            return None
        rows = self.enabled_rows()
        rows.sort()  # just in case
        if not rows:
            return None
        else:
            for r in rows:
                if r > row:
                    return r
            return rows[0]

    def fill_weather(self, weather: Optional[dict]) -> None:
        if weather is not None:
            self.label_weather_temperature_value.setNum(np.round(weather['OutsideTemp'], decimals=1))
            self.label_weather_humidity_value.setNum(weather['OutsideHum'])
            self.label_weather_wind_speed_value.setNum(weather['WindSpeed'])
            self.label_weather_wind_direction_value.setNum(weather['WindDir'])
            self.label_weather_rain_rate_value.setNum(weather['RainRate'])
            self.label_weather_solar_radiation_value.setNum(weather['SolarRad'])

    def calculate_bb_τ(self, *, callback: Callable[[int, float], Any],
                       min_angle: float, max_angle: float, bb_angle: float,
                       precision: float = 5.) -> None:
        distance_to_max_angle: Union[None, float] = None
        distance_to_min_angle: Union[None, float] = None
        distance_to_bb_angle: Union[None, float] = None
        closest_to_bb_angle: Union[None, float] = None
        closest_to_max_angle: Union[None, float] = None
        closest_to_min_angle: Union[None, float] = None
        for angle in self.last_loop_data:
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
            for ch in range(len(self.last_loop_data[closest_to_bb_angle])):
                d0 = self.last_loop_data[closest_to_bb_angle][ch]
                d1 = self.last_loop_data[closest_to_max_angle][ch]
                d2 = self.last_loop_data[closest_to_min_angle][ch]
                np.seterr(invalid='raise', divide='raise')
                try:
                    if (d0 > d1 and d0 > d2) or (d0 < d1 and d0 < d2):
                        τ = np.log((d0 - d1) / (d0 - d2)) / \
                            (1.0 / np.sin(np.radians(closest_to_min_angle))
                             - 1.0 / np.sin(np.radians(closest_to_max_angle)))
                    else:
                        τ = np.nan
                except FloatingPointError:
                    print('τ = ln(({d0} - {d1})/({d0} - {d2})) / (1/cos({θ2}°) - 1/cos({θ1}°))'.format(
                        d0=d0,
                        d1=d1,
                        d2=d2,
                        θ1=90 - closest_to_min_angle,
                        θ2=90 - closest_to_max_angle))
                else:
                    if not np.isnan(τ):
                        callback(ch, τ)
                np.seterr(invalid='warn', divide='warn')

    def calculate_leastsq_τ(self, ch: int) -> Tuple[float, float]:
        h: np.ndarray = np.array(list(self.last_loop_data))
        d: np.ndarray = np.array([self.last_loop_data[a][ch] if ch < len(self.last_loop_data[a]) else np.nan
                                  for a in self.last_loop_data])
        d0: np.float64 = d[np.argmin(np.abs(h))]
        good: np.ndarray = (h >= 15) & (d0 > d)
        if not np.any(good):
            return np.nan, np.nan
        h = h[good]
        d = d[good]
        x = -1. / np.sin(np.deg2rad(h))
        y = np.log(d0 - d)
        p, residuals, *_ = np.polyfit(x, y, deg=1, full=True)
        return p[0], residuals[0] if residuals.size else np.nan

    def calculate_magic_angles_τ(self, ch: int, lower_angle: float, higher_angle: float) -> float:
        h: np.ndarray = np.array(list(self.last_loop_data))
        d: np.ndarray = np.array([self.last_loop_data[a][ch] if ch < len(self.last_loop_data[a]) else np.nan
                                  for a in self.last_loop_data])
        good: np.ndarray = (h >= 10)
        h = h[good]
        d = d[good]
        if not np.any(good):
            return np.nan
        min_diff: float = 1.
        j: int = -1
        k: int = int(np.argmin(np.abs(h - higher_angle)))
        i: int = int(np.argmin(np.abs(h - lower_angle)))
        if i == k:
            return np.nan
        z_a: float = float(np.deg2rad(h[k]))
        h_a: float = float(np.deg2rad(h[i]))
        for _j in range(h.size):
            if _j in (i, k):
                continue
            diff = np.abs(1. / np.sin(z_a) - 2. / np.sin(np.deg2rad(h[_j])) + 1. / np.sin(h_a))
            if min_diff > diff:
                j = _j
                min_diff = diff
        if min_diff > 0.02:
            return np.nan
        np.seterr(invalid='raise', divide='raise')
        τ = np.nan
        if d[i] < d[j] < d[k] or d[i] > d[j] > d[k]:
            try:
                τ = np.log((d[j] - d[k]) / (d[i] - d[j])) / \
                    (1. / np.sin(h_a) - 1. / np.sin(np.deg2rad(h[j])))
            finally:
                pass
            np.seterr(invalid='warn', divide='warn')
        if np.isnan(τ):
            print('τ = ln(({d1} - {d0})/({d2} - {d1})) / (1/cos({θ2}°) - 1/cos({θ1}°))'.format(
                d0=d[k],
                d1=d[j],
                d2=d[i],
                θ1=90 - h[j],
                θ2=90 - h[i]))
        return τ

    def measure_next(self, ignore_home: bool = False) -> None:
        self.fill_weather(self.last_weather())
        self.update_temperature_values()
        if self._measured or ignore_home:
            self.canvas.draw_idle()
            current_angle = self.table_schedule.cellWidget(self._current_row, 1).value()
            self.last_loop_data[current_angle] = self.last_data()
            next_row = self.next_enabled_row(self._current_row)
            if next_row is None:
                return

            if self._current_row >= next_row and not ignore_home:
                # calculate τ in different manners
                max_angle = self.spin_max_angle.value()
                for min_angle, bb_angle, callback in [
                    (self.spin_min_angle.value(), self.spin_bb_angle.value(), self.add_τ),
                    (self.spin_min_angle_alt.value(), self.spin_bb_angle.value(), self.add_τ_alt),
                    (self.spin_min_angle_alt.value(), self.spin_bb_angle_alt.value(), self.add_τ_bb_alt),
                ]:
                    self.calculate_bb_τ(callback=callback,
                                        min_angle=min_angle, max_angle=max_angle, bb_angle=bb_angle)
                for ch in range(len(self.last_loop_data[current_angle])):
                    _τ, _error = self.calculate_leastsq_τ(ch)
                    if not np.isnan(_error):
                        self.add_τ_leastsq(ch, _τ, _error)
                    _τ = self.calculate_magic_angles_τ(ch, self.spin_min_angle.value(), self.spin_max_angle.value())
                    if not np.isnan(_τ):
                        self.add_τ_magic_angles(ch, _τ)
                    # _τ = self.calculate_magic_angles_τ(ch, self.spin_min_angle_alt.value(),
                    #                                    self.spin_max_angle.value())
                    # if not np.isnan(_τ):
                    #     self.adc_thread.add_τ_magic_angles_alt(ch, _τ)

                self.last_loop_data = {}
                self.canvas.draw_idle()

                self.pd.setMaximum(round(1000 * self.time_to_move_home()))
                self.pd.setLabelText('Wait till the motor comes home')
                self.pd.reset()
                self.move_home()
                if self.timer.receivers(self.timer.timeout):
                    self.timer.timeout.disconnect()
                self.timer.timeout.connect(
                    lambda: self.next_pd_tick(
                        fallback=lambda: self.measure_next(ignore_home=True),
                        abort=self.adc_thread.done
                    )
                )
                self.timer.setSingleShot(True)
                self.timer.start(100)  # don't use QTimer.singleShot here to be able to stop the timer later!!

                self.pack_data()
                # self.adc_thread.purge_obsolete_data(purge_all=True)

            elif self.button_go.isChecked():
                angle = self.table_schedule.cellWidget(next_row, 1).value()
                duration = self.table_schedule.cellWidget(next_row, 2).value()
                self._current_row = next_row
                self.highlight_current_row()

                self.motor.move(angle - self._current_angle)
                self.adc_thread.measure(self.motor.time_to_turn(angle - self._current_angle) + self._measurement_delay,
                                        duration)
                self._measured = False
                self._current_angle = angle
                self.set_config_value('common', 'last angle', angle)

                if self.timer.receivers(self.timer.timeout):
                    self.timer.timeout.disconnect()
                self.timer.timeout.connect(self.measure_next)
                self.timer.setSingleShot(True)
                # don't use QTimer.singleShot here to be able to stop the timer later!!
                self.timer.start(round(1000 * self.measurement_time(angle, duration)))
        else:
            if self.timer.receivers(self.timer.timeout):
                self.timer.timeout.disconnect()
            self.timer.timeout.connect(self.measure_next)
            self.timer.setSingleShot(True)
            self.timer.start(100)  # don't use QTimer.singleShot here to be able to stop the timer later!!

    def button_go_toggled(self, new_value: bool) -> None:
        if new_value and self.table_schedule.rowCount() > 0:
            if self._current_row is None:
                self._current_row = self.next_enabled_row(-1)
            self.highlight_current_row()
            angle = self.table_schedule.cellWidget(self._current_row, 1).value()
            duration = self.table_schedule.cellWidget(self._current_row, 2).value()
            self.purge_obsolete_data(purge_all=True)

            self.motor.move(angle - self._current_angle)
            self.adc_thread.measure(self.motor.time_to_turn(angle - self._current_angle) + self._measurement_delay,
                                    duration)
            self._measured = False
            self._current_angle = angle
            self.set_config_value('common', 'last angle', angle)

            if self.timer.receivers(self.timer.timeout):
                self.timer.timeout.disconnect()
            self.timer.timeout.connect(self.measure_next)
            self.timer.setSingleShot(True)
            # don't use QTimer.singleShot here to be able to stop the timer later!!
            self.timer.start(round(self.measurement_time(angle, duration)) * 1000)
        else:
            self.timer.stop()
            self.adc_thread.set_running(False)
            self.highlight_current_row(False)
        self.set_config_value('common', 'running', new_value)
        self.resuming = False

    def next_pd_tick(self, fallback: Optional[Callable[[], Any]] = None,
                     abort: Optional[Callable[[], Any]] = None) -> None:
        next_value: int = self.pd.value() + self.timer.interval()
        if not abort() if callable(abort) else (next_value < self.pd.maximum()):
            if next_value < self.pd.maximum():
                self.pd.setValue(next_value)
            if self.timer.receivers(self.timer.timeout):
                self.timer.timeout.disconnect()
            self.timer.timeout.connect(lambda: self.next_pd_tick(fallback=fallback, abort=abort))
            self.timer.setSingleShot(True)
            self.timer.start(100)  # don't use QTimer.singleShot here to be able to stop the timer later!!
        else:
            self.pd.reset()
            if callable(fallback):
                fallback()

    def enable_motor(self, enable: bool) -> None:
        self.adc_thread.targets.append((self._enable_motor, (enable,)))

    def move_home(self) -> None:
        self.adc_thread.targets.append((self._move_home, ()))

    def button_power_toggled(self, new_state: bool) -> None:
        if not new_state:
            self.button_go.setChecked(False)
            self.button_go.setEnabled(False)
        self.button_power.setDisabled(True)
        self.enable_motor(new_state)
        if new_state:
            self.pd.setMaximum(round(1000 * self.time_to_move_home()))
            self.pd.setLabelText('Wait till the motor comes home')
            self.pd.reset()
            if self.timer.receivers(self.timer.timeout):
                self.timer.timeout.disconnect()
            self.timer.timeout.connect(
                lambda: self.next_pd_tick(
                    fallback=lambda: (
                            self.button_go.setEnabled(new_state)
                            or self.button_go.setChecked(new_state and self.resuming)
                            or self.button_power.setEnabled(new_state)
                    ),
                    abort=self.adc_thread.done
                )
            )
            self.timer.setSingleShot(True)
            self.timer.start(100)  # don't use QTimer.singleShot here to be able to stop the timer later!!
        else:
            self.button_power.setEnabled(True)
        self.set_config_value('common', 'power', new_state)

    def step_fraction_changed(self, new_value: int) -> None:
        self.set_config_value('motor', 'step fraction', new_value)
        self.motor.microstepping_mode = MicrosteppingMode(index=new_value)
        step: float = self.motor.step
        for r in range(self.table_schedule.rowCount()):
            angle: float = self.table_schedule.cellWidget(r, 1).value()
            angle = round(angle / step) * step
            self.table_schedule.cellWidget(r, 1).setValue(angle)
            self.table_schedule.cellWidget(r, 1).setSingleStep(step)

    def spin_settings_speed_changed(self, new_value) -> None:
        self.set_config_value('motor', 'speed', new_value)
        self.motor.speed(new_value)

    def spin_settings_gear_1_changed(self, new_value) -> None:
        self.set_config_value('motor', 'gear 1 size', new_value)
        self.motor.gear_ratio(new_value / self.spin_settings_gear_2.value())

    def spin_settings_gear_2_changed(self, new_value) -> None:
        self.set_config_value('motor', 'gear 2 size', new_value)
        self.motor.gear_ratio(self.spin_settings_gear_1.value() / new_value)

    def button_move_home_clicked(self) -> None:
        self.pd.setMaximum(round(1000 * self.time_to_move_home()))
        self.pd.setLabelText('Wait till the motor comes home')
        self.pd.reset()
        if self.timer.receivers(self.timer.timeout):
            self.timer.timeout.disconnect()
        self.timer.timeout.connect(lambda: self.next_pd_tick(abort=self.adc_thread.done))
        self.timer.setSingleShot(True)
        self.timer.start(100)  # don't use QTimer.singleShot here to be able to stop the timer later!!
        self.move_home()

    def button_move_90degrees_clicked(self) -> None:
        self.pd.setMaximum(round(1000 * self.move_90degrees()))
        self.pd.setLabelText('Wait till the motor turns 90 degrees')
        self.pd.reset()
        if self.timer.receivers(self.timer.timeout):
            self.timer.timeout.disconnect()
        self.timer.timeout.connect(self.next_pd_tick)
        self.timer.setSingleShot(True)
        self.timer.start(100)  # don't use QTimer.singleShot here to be able to stop the timer later!!

    def button_move_1step_right_clicked(self) -> None:
        self.pd.setMaximum(round(1000 * self.move_1step_right()))
        self.pd.setLabelText('Wait till the motor turns 1 step')
        self.pd.reset()
        if self.timer.receivers(self.timer.timeout):
            self.timer.timeout.disconnect()
        self.timer.timeout.connect(self.next_pd_tick)
        self.timer.setSingleShot(True)
        self.timer.start(100)  # don't use QTimer.singleShot here to be able to stop the timer later!!

    def button_move_1step_left_clicked(self) -> None:
        self.pd.setMaximum(round(1000 * self.move_1step_left()))
        self.pd.setLabelText('Wait till the motor turns 1 step')
        self.pd.reset()
        if self.timer.receivers(self.timer.timeout):
            self.timer.timeout.disconnect()
        self.timer.timeout.connect(self.next_pd_tick)
        self.timer.setSingleShot(True)
        self.timer.start(100)  # don't use QTimer.singleShot here to be able to stop the timer later!!

    def button_move_360degrees_right_clicked(self) -> None:
        self.pd.setMaximum(round(1000 * self.move_360degrees_right()))
        self.pd.setLabelText('Wait till the motor turns 360 degrees')
        self.pd.reset()
        if self.timer.receivers(self.timer.timeout):
            self.timer.timeout.disconnect()
        self.timer.timeout.connect(self.next_pd_tick)
        self.timer.setSingleShot(True)
        self.timer.start(100)  # don't use QTimer.singleShot here to be able to stop the timer later!!

    def button_move_360degrees_left_clicked(self) -> None:
        self.pd.setMaximum(round(1000 * self.move_360degrees_left()))
        self.pd.setLabelText('Wait till the motor turns 360 degrees')
        self.pd.reset()
        if self.timer.receivers(self.timer.timeout):
            self.timer.timeout.disconnect()
        self.timer.timeout.connect(self.next_pd_tick)
        self.timer.setSingleShot(True)
        self.timer.start(100)  # don't use QTimer.singleShot here to be able to stop the timer later!!

    def spin_channels_changed(self, new_value: int) -> None:
        self.set_config_value('settings', 'number of channels', new_value)
        self.settings.sync()
        # self.figure.clf()

        self.adc_channels = list(range(self.spin_channels.value()))
        for _ in range(len(self._plot_lines), self.spin_channels.value()):
            self._plot_lines.append(self.plot.plot_date(np.empty(0), np.empty(0))[0])
            self._τ_plot_lines.append(self.τ_plot.plot_date(np.empty(0), np.empty(0),
                                                            color=self._plot_lines[-1].get_color(),
                                                            ls='-')[0])
            self._τ_plot_alt_lines.append(self.τ_plot.plot_date(np.empty(0), np.empty(0),
                                                                color=self._plot_lines[-1].get_color(),
                                                                ls='--')[0])
            self._τ_plot_alt_bb_lines.append(self.τ_plot.plot_date(np.empty(0), np.empty(0),
                                                                   color=self._plot_lines[-1].get_color(),
                                                                   ls='--')[0])
            self._τ_plot_leastsq_lines.append(self.τ_plot.plot_date(np.empty(0), np.empty(0),
                                                                    color=self._plot_lines[-1].get_color(),
                                                                    ls=':')[0])
            self._τ_plot_magic_lines.append(self.τ_plot.plot_date(np.empty(0), np.empty(0),
                                                                  color=self._plot_lines[-1].get_color(),
                                                                  ls='-.')[0])
            # self._τ_plot_magic_alt_lines.append(self.τ_plot.plot_date(np.empty(0), np.empty(0),
            #                                                           color=self._plot_lines[-1].get_color(),
            #                                                           ls='-.')[0])

        self.x = np.empty(0)
        self.y = [np.empty(0)] * len(self.adc_channels)
        self.τx = [np.empty(0)] * len(self.adc_channels)
        self.τy = [np.empty(0)] * len(self.adc_channels)
        self.τx_alt = [np.empty(0)] * len(self.adc_channels)
        self.τy_alt = [np.empty(0)] * len(self.adc_channels)
        self.τx_bb_alt = [np.empty(0)] * len(self.adc_channels)
        self.τy_bb_alt = [np.empty(0)] * len(self.adc_channels)
        self.τx_leastsq = [np.empty(0)] * len(self.adc_channels)
        self.τy_leastsq = [np.empty(0)] * len(self.adc_channels)
        # self.τy_error_leastsq = [np.empty(0)] * len(self.adc_channels)
        self.τx_magic = [np.empty(0)] * len(self.adc_channels)
        self.τy_magic = [np.empty(0)] * len(self.adc_channels)
        # self.τx_magic_alt = [np.empty(0)] * len(self.adc_channels)
        # self.τy_magic_alt = [np.empty(0)] * len(self.adc_channels)
        self.wind_x = np.empty(0)
        self.wind_y = np.empty(0)

        self.adc_channels_names = self.adc_channels_names  # update the values

        self.adc_thread.set_channels(self.adc_channels)

    def spin_measurement_delay_changed(self, new_value) -> None:
        self.set_config_value('settings', 'delay before measuring', new_value)
        self.set_measurement_delay(new_value)

    def spin_bb_angle_changed(self, new_value) -> None:
        self.set_config_value('settings', 'black body position', new_value)
        self.settings.sync()

    def spin_bb_angle_alt_changed(self, new_value) -> None:
        self.set_config_value('settings', 'black body position alt', new_value)
        self.settings.sync()

    def spin_max_angle_changed(self, new_value) -> None:
        self.set_config_value('settings', 'zenith position', new_value)
        self.settings.sync()

    def spin_min_angle_changed(self, new_value) -> None:
        self.set_config_value('settings', 'horizon position', new_value)
        self.settings.sync()

    def spin_min_angle_alt_changed(self, new_value) -> None:
        self.set_config_value('settings', 'horizon position alt', new_value)
        self.settings.sync()

    @staticmethod
    def on_xlim_changed(axes: Axes) -> None:
        x_lim = axes.get_xlim()
        axis_min, axis_max = min(x_lim), max(x_lim)
        if axis_min < 1.:
            axes.set_xlim(left=1., right=axis_max if axis_max > 1. else 1.001, emit=False, auto=True)
            axes.set_autoscalex_on(True)
            return
        auto_scale = axes.get_autoscalex_on()
        data_min, data_max = None, None
        for line in axes.lines:
            data = line.get_xdata()
            if not data.size:
                continue
            if data_min is not None:
                data_min = min(data_min, np.min(data))
            else:
                data_min = np.min(data)
            if data_max is not None:
                data_max = max(data_max, np.max(data))
            else:
                data_max = np.max(data)
        if data_min is not None and data_max is not None:
            if axis_min > data_min or axis_max < data_max:
                auto_scale = False
            else:
                x_margin, y_margin = axes.margins()
                if data_max == data_min:
                    span = 1
                else:
                    span = abs(data_max - data_min)
                axis_min = data_min - x_margin * span
                axis_max = data_max + x_margin * span
                axes.set_xlim(left=axis_min, right=axis_max, emit=False, auto=True)
                auto_scale = True
        axes.set_autoscalex_on(auto_scale)

    # @staticmethod
    # def on_xlim_changed(axes: Axes) -> None:
    #     xlim = axes.get_xlim()
    #     autoscale = True
    #     _min, _max = min(xlim), max(xlim)
    #     if _min < 1.:
    #         axes.set_xlim(left=1., right=_max if _max > 1. else 1.001)
    #         axes.set_autoscalex_on(True)
    #     for line in axes.lines:
    #         data = line.get_xdata()[:-1]
    #         if len(data) > 0 and (_min > min(data) or _max < max(data)):
    #             autoscale = False
    #         if len(data) > 0:
    #             print(line, _min, min(data), _max, max(data))
    #     axes.set_autoscalex_on(autoscale)
    #     print(autoscale)
    #
    @staticmethod
    def on_ylim_changed(axes: Axes) -> None:
        y_lim = axes.get_ylim()
        auto_scale = True
        for line in axes.lines:
            data = line.get_ydata()[:-1]
            if data.size > 0 and (min(y_lim) > min(data) and max(y_lim) < max(data)):
                auto_scale = False
        axes.set_autoscaley_on(auto_scale)

    @staticmethod
    def on_click(event) -> None:
        if event.dblclick and event.inaxes is not None:
            event.inaxes.set_autoscale_on(True)
            event.inaxes.relim(visible_only=True)
            # event.inaxes.autoscale_view(None, True, True)
            event.inaxes.autoscale(enable=True, axis='both')

    def _enable_motor(self, enable: bool) -> None:
        if enable:
            self.motor.enable()
            self.motor.forward()
            self.move_home()
        else:
            self.motor.disable()

    def move_90degrees(self) -> Optional[float]:
        self.motor.move(90)
        self._current_angle += 90
        return self.motor.time_to_turn(90)

    def move_1step_right(self) -> Optional[float]:
        self.motor.move(self.motor.step)
        self._current_angle += self.motor.step
        return self.motor.time_to_turn(self.motor.step)

    def move_1step_left(self) -> Optional[float]:
        self.motor.move(-self.motor.step)
        self._current_angle -= self.motor.step
        return self.motor.time_to_turn(self.motor.step)

    def move_360degrees_right(self) -> Optional[float]:
        self.motor.move(360)
        self._current_angle += 360
        return self.motor.time_to_turn(360)

    def move_360degrees_left(self) -> Optional[float]:
        self.motor.move(-360)
        self._current_angle -= 360
        return self.motor.time_to_turn(360)

    def time_to_move_home(self) -> Optional[float]:
        return (self.motor.time_to_turn(self._current_angle)
                + self.motor.time_to_turn(360)
                + 4. * self.motor.microstepping_mode * self.motor.time_to_turn(self.motor.step)
                + 4. * self.motor.microstepping_mode
                + 2. * self.motor.time_to_turn(25.2))

    def _move_home(self) -> None:
        _threshold: int = 768
        self.motor.move(-self._current_angle)
        time.sleep(self.motor.time_to_turn(self._current_angle))
        v: Optional[int] = self.arduino.voltage('A0')
        print('A0 voltage is', v)
        if v is None:
            print('no “0” position data')
            print('making whole turn')
            self.motor.forward()
            self.motor.move_home()
            time.sleep(self.motor.time_to_turn(360))
        else:
            _i: int = 0
            if v is not None and v > _threshold:
                print('making steps back to ensure the motor is not behind “0”')
            while v is not None and v > _threshold and _i < self.motor.microstepping_mode:
                print(f'attempt #{_i + 1} out of {self.motor.microstepping_mode} to find “0”')
                self.motor.move(-self.motor.step)
                time.sleep(self.motor.time_to_turn(self.motor.step))
                v = self.arduino.voltage('A0')
                if v is None or v > _threshold:
                    print('it failed: A0 voltage still is', v)
                else:
                    print('success: A0 voltage is', v)
                _i += 1
            if v is not None and v < _threshold:
                print('making steps forward to get back to “0”')
                self.motor.move(self.motor.step)
                time.sleep(self.motor.time_to_turn(self.motor.step))
                v = self.arduino.voltage('A0')
                print('A0 voltage is', v)
                _i = 0
            while v is not None and v < _threshold and _i < self.motor.microstepping_mode:
                print(f'attempt #{_i + 1} out of {self.motor.microstepping_mode} to find “0”')
                self.motor.move(self.motor.step)
                time.sleep(self.motor.time_to_turn(self.motor.step))
                v = self.arduino.voltage('A0')
                if v is None or v < _threshold:
                    print('it failed: A0 voltage is', v)
                else:
                    print('success: A0 voltage is', v)
                _i += 1
            if v is None or v < _threshold:
                print('making whole turn')
                self.motor.forward()
                self.motor.move_home()
                time.sleep(self.motor.time_to_turn(360.0))
        print('moving back and forth')
        self.motor.move(-25.2)
        time.sleep(self.motor.time_to_turn(25.2))
        self.motor.forward()
        self.motor.move_home()
        time.sleep(self.motor.time_to_turn(25.2))
        v = self.arduino.voltage('A0')
        print('A0 voltage is', v)
        if v is None:
            print('no “0” position data')
        else:
            _i: int = 0
            if v is not None and v > _threshold:
                print('making steps back to ensure the motor is not behind “0”')
            while v is not None and v > _threshold and _i < self.motor.microstepping_mode:
                print(f'attempt #{_i + 1} out of {self.motor.microstepping_mode} to find “0”')
                self.motor.move(-self.motor.step)
                time.sleep(self.motor.time_to_turn(self.motor.step))
                v = self.arduino.voltage('A0')
                if v is None or v > _threshold:
                    print('it failed: A0 voltage still is', v)
                else:
                    print('success: A0 voltage is', v)
                _i += 1
            if v is not None and v < _threshold:
                print('making steps forward to get back to “0”')
                self.motor.move(self.motor.step)
                time.sleep(self.motor.time_to_turn(self.motor.step))
                v = self.arduino.voltage('A0')
                print('A0 voltage is', v)
                _i = 0
            while v is not None and v < _threshold and _i < self.motor.microstepping_mode:
                print(f'attempt #{_i + 1} out of {self.motor.microstepping_mode} to find “0”')
                self.motor.move(self.motor.step)
                time.sleep(self.motor.time_to_turn(self.motor.step))
                v = self.arduino.voltage('A0')
                if v is None or v < _threshold:
                    print('it failed: A0 voltage is', v)
                else:
                    print('success: A0 voltage is', v)
                _i += 1
        with open('A0_voltage.csv', 'a') as f_out:
            f_out.write(f'{v}\n')
        self._current_angle = 0.0
        print('got home')

    def set_measurement_delay(self, delay) -> None:
        _delay: float = float(delay)
        if _delay < 0.0:
            raise ValueError('Measurement delay can not be negative')
        self._measurement_delay = _delay

    def measurement_time(self, angle, duration) -> float:
        """ convenience function """
        if self.motor.speed():
            return self.motor.time_to_turn(angle - self._current_angle) + self._measurement_delay + duration
        else:
            return np.nan

    def set_point(self) -> None:
        self.purge_obsolete_data()
        data_item: Dict[str, Union[Dict[str, Union[None, str, float]],
                                   List[float], List[bool], List[List[float]],
                                   None, bool, float, str]] = {}
        weather_data: Dict[str, Union[None, int, float, str, List[None, int, float]]] = \
            self.weather_station.get_realtime_data()
        if weather_data:
            data_item['weather'] = weather_data
            self.wind_x = np.concatenate((self.wind_x, np.array([date2num(datetime.now())])))
            self.wind_y = np.concatenate((self.wind_y,
                                          np.array([weather_data['AvgWindSpeed']
                                                    * np.cos(np.radians(weather_data['WindDir']))])))
            self._wind_plot_line.set_data(self.wind_x, self.wind_y)
            self._wind_plot.relim(visible_only=True)
            # follow the autoscale settings of self.τ_plot
            self._wind_plot.autoscale_view(None, self.τ_plot.get_autoscalex_on(), True)
        data_item['temperatures'] = self.arduino.temperatures
        data_item['setpoints'] = self.arduino.setpoints
        data_item['states'] = self.arduino.states
        data_item['enabled'] = self.arduino.enabled
        data_item['timestamp'] = self.adc_thread.current_x.timestamp()
        data_item['time'] = self.adc_thread.current_x.isoformat()
        data_item['angle'] = self._current_angle
        # noinspection PyTypeChecker
        data_item['voltage'] = [ys.tolist() for ys in self.adc_thread.current_y]
        self.data.append(data_item)
        self.x = np.concatenate((self.x, np.array([date2num(self.adc_thread.current_x)])))
        for ch, ys in enumerate(self.adc_thread.current_y):
            if ys.size:
                if len(self.y) > ch:
                    self.y[ch] = np.concatenate((self.y[ch], np.array([np.mean(ys)])))
                else:
                    self.y.append(np.full(self.y[-1].shape, np.nan))
                if self.x.shape != self.y[ch].shape:
                    print('data shapes don\'t match:')
                    print('channel', ch)
                    print(self.x)
                    print(self.y[ch])
                else:
                    self._plot_lines[ch].set_data(self.x, self.y[ch])
            else:
                print('empty y for channel', ch + 1)
                self.y[ch] = np.concatenate((self.y[ch], np.array([np.nan])))
            self.adc_thread.current_y[ch] = np.array([])
        for ch in range(len(self.adc_thread.current_y), len(self.y)):  # deactivated channels after the count changed
            self.y[ch] = np.concatenate((self.y[ch], np.array([np.nan])))
        self.plot.relim(visible_only=True)
        self.plot.autoscale_view(None, self.plot.get_autoscalex_on(), self.plot.get_autoscaley_on())
        self.τ_plot.relim(visible_only=True)
        self.τ_plot.autoscale_view(None, False, self.τ_plot.get_autoscaley_on())
        # rotate and align the tick labels so they look better
        self.figure.autofmt_xdate(bottom=self.subplotpars['bottom'])
        self.figure.canvas.draw_idle()
        self.adc_thread.set_running(False)
        self._measured = True

    def purge_obsolete_data(self, purge_all: bool = False) -> None:
        current_time: float = date2num(datetime.now())
        time_span: float = 1.0
        not_obsolete: np.ndarray = (current_time - self.x <= time_span)
        self.x = self.x[not_obsolete]
        self.y = [self.y[ch][not_obsolete] for ch in range(len(self.y))]
        if self.x.size > 0 and self.x[0] > np.mean(self.plot.get_xlim()):
            self.plot.set_autoscalex_on(True)
        for ch in range(len(self.τx)):
            not_obsolete: np.ndarray = (current_time - self.τx[ch] <= time_span)
            self.τx[ch] = self.τx[ch][not_obsolete]
            self.τy[ch] = self.τy[ch][not_obsolete]
            if self.τx[ch].size > 0 and self.τx[ch][0] > np.mean(self.τ_plot.get_xlim()):
                self.τ_plot.set_autoscalex_on(True)
        for ch in range(len(self.τx_alt)):
            not_obsolete: np.ndarray = (current_time - self.τx_alt[ch] <= time_span)
            self.τx_alt[ch] = self.τx_alt[ch][not_obsolete]
            self.τy_alt[ch] = self.τy_alt[ch][not_obsolete]
            if self.τx_alt[ch].size > 0 and self.τx_alt[ch][0] > np.mean(self.τ_plot.get_xlim()):
                self.τ_plot.set_autoscalex_on(True)
        for ch in range(len(self.τx_bb_alt)):
            not_obsolete: np.ndarray = (current_time - self.τx_bb_alt[ch] <= time_span)
            self.τx_bb_alt[ch] = self.τx_bb_alt[ch][not_obsolete]
            self.τy_bb_alt[ch] = self.τy_bb_alt[ch][not_obsolete]
            if self.τx_bb_alt[ch].size > 0 and self.τx_bb_alt[ch][0] > np.mean(self.τ_plot.get_xlim()):
                self.τ_plot.set_autoscalex_on(True)
        for ch in range(len(self.τx_leastsq)):
            not_obsolete: np.ndarray = (current_time - self.τx_leastsq[ch] <= time_span)
            self.τx_leastsq[ch] = self.τx_leastsq[ch][not_obsolete]
            self.τy_leastsq[ch] = self.τy_leastsq[ch][not_obsolete]
            # self._τy_error_leastsq[ch] = self._τy_error_leastsq[ch][not_obsolete]
            if self.τx_leastsq[ch].size > 0 and self.τx_leastsq[ch][0] > np.mean(self.τ_plot.get_xlim()):
                self.τ_plot.set_autoscalex_on(True)
        for ch in range(len(self.τx_magic)):
            not_obsolete: np.ndarray = (current_time - self.τx_magic[ch] <= time_span)
            self.τx_magic[ch] = self.τx_magic[ch][not_obsolete]
            self.τy_magic[ch] = self.τy_magic[ch][not_obsolete]
            if self.τx_magic[ch].size > 0 and self.τx_magic[ch][0] > np.mean(self.τ_plot.get_xlim()):
                self.τ_plot.set_autoscalex_on(True)
        # for ch in range(len(self._τx_magic_alt)):
        #     not_obsolete: np.ndarray = (current_time - self._τx_magic_alt[ch] <= time_span)
        #     self._τx_magic_alt[ch] = self._τx_magic_alt[ch][not_obsolete]
        #     self._τy_magic_alt[ch] = self._τy_magic_alt[ch][not_obsolete]
        #     if self._τx_magic_alt[ch].size > 0 and self._τx_magic_alt[ch][0] > np.mean(self.τ_plot.get_xlim()):
        #         self.τ_plot.set_autoscalex_on(True)
        not_obsolete: np.ndarray = (current_time - self.wind_x <= time_span)
        self.wind_x = self.wind_x[not_obsolete]
        self.wind_y = self.wind_y[not_obsolete]
        if self.wind_x.size > 0 and self.wind_x[0] > np.mean(self._wind_plot.get_xlim()):
            self._wind_plot.set_autoscalex_on(True)
        if purge_all:
            self.data = []

    def last_data(self) -> List[float]:
        return [self.y[ch][-1] if self.y[ch].size else np.nan for ch in range(len(self.y))]

    def last_weather(self) -> Optional[Dict[str, Any]]:
        return self.data[-1]['weather'] if len(self.data) > 0 and 'weather' in self.data[-1] else None

    def add_τ(self, channel: int, τ: float) -> None:
        current_time: float = date2num(datetime.now())
        self.τx[channel] = np.concatenate((self.τx[channel], np.array([current_time])))
        self.τy[channel] = np.concatenate((self.τy[channel], np.array([τ])))
        for ch in range(len(self.τy)):
            self._τ_plot_lines[ch].set_data(self.τx[ch], self.τy[ch])

    def add_τ_alt(self, channel: int, τ: float) -> None:
        current_time: float = date2num(datetime.now())
        self.τx_alt[channel] = np.concatenate((self.τx_alt[channel], np.array([current_time])))
        self.τy_alt[channel] = np.concatenate((self.τy_alt[channel], np.array([τ])))
        for ch in range(len(self.τy_alt)):
            self._τ_plot_alt_lines[ch].set_data(self.τx_alt[ch], self.τy_alt[ch])

    def add_τ_bb_alt(self, channel: int, τ: float) -> None:
        current_time: float = date2num(datetime.now())
        self.τx_bb_alt[channel] = np.concatenate((self.τx_bb_alt[channel], np.array([current_time])))
        self.τy_bb_alt[channel] = np.concatenate((self.τy_bb_alt[channel], np.array([τ])))
        for ch in range(len(self.τy_bb_alt)):
            self._τ_plot_alt_bb_lines[ch].set_data(self.τx_bb_alt[ch], self.τy_bb_alt[ch])

    def add_τ_leastsq(self, channel: int, τ: float, _error: float = np.nan) -> None:
        current_time: float = date2num(datetime.now())
        self.τx_leastsq[channel] = np.concatenate((self.τx_leastsq[channel], np.array([current_time])))
        self.τy_leastsq[channel] = np.concatenate((self.τy_leastsq[channel], np.array([τ])))
        # self._τy_error_leastsq[channel] = np.concatenate((self._τy_error_leastsq[channel], np.array([error])))
        for ch in range(len(self.τy_leastsq)):
            self._τ_plot_leastsq_lines[ch].set_data(self.τx_leastsq[ch], self.τy_leastsq[ch])

    def add_τ_magic_angles(self, channel: int, τ: float) -> None:
        current_time: float = date2num(datetime.now())
        self.τx_magic[channel] = np.concatenate((self.τx_magic[channel], np.array([current_time])))
        self.τy_magic[channel] = np.concatenate((self.τy_magic[channel], np.array([τ])))
        for ch in range(len(self.τy_magic)):
            self._τ_plot_magic_lines[ch].set_data(self.τx_magic[ch], self.τy_magic[ch])

    # def add_τ_magic_angles_alt(self, channel: int, τ: float) -> None:
    #     current_time: float = date2num(datetime.now())
    #     self._τx_magic_alt[channel] = np.concatenate((self._τx_magic_alt[channel], np.array([current_time])))
    #     self._τy_magic_alt[channel] = np.concatenate((self._τy_magic_alt[channel], np.array([τ])))
    #     for ch in range(len(self._τy_magic_alt)):
    #         self._τ_plot_magic_alt_lines[ch].set_data(self._τx_magic_alt[ch], self._τy_magic_alt[ch])

    def pack_data(self) -> None:
        self.purge_obsolete_data()
        if not self.data:
            return
        if not os.path.exists(self.output_folder):
            os.mkdir(self.output_folder)
        elif not os.path.isdir(self.output_folder):
            os.remove(self.output_folder)
            os.mkdir(self.output_folder)
        with gzip.open(
                os.path.join(
                    self.output_folder,
                    f'{datetime.fromtimestamp(self.data[0]["timestamp"]).strftime("%Y%m%d%H%M%S%f")}.json.gz'
                ), 'wb') as f:
            f.write(json.dumps(
                {'raw_data': self.data},
                indent=4).encode())
        if self.summary_file_prefix is not None:
            fields: List[str] = [
                'time',
                'timestamp',
                'wind direction',
                'wind speed',
                'humidity',
                'temperature',
            ]
            for ch in range(len(self.τy)):
                path: str = f'{self.summary_file_prefix}.{ch + 1}.csv'
                is_new_file: bool = not os.path.exists(path)
                if not is_new_file and (os.path.isdir(path) or not os.access(path, os.W_OK)):
                    print('ERROR: can not append to', path)
                    continue
                with open(path, 'a') as csv_file:
                    angles_data: Dict[float, float] = {}
                    for a in self.data:
                        angles_data[a['angle']] = float(np.mean(a['voltage'][ch])) if ch < len(a['voltage']) else np.nan
                    angles_fields: List[str] = [f'angle {a}' for a in sorted(angles_data)]
                    angles_data: Dict[str, float] = dict((f'angle {i}', angles_data[i]) for i in sorted(angles_data))
                    csv_writer = csv.DictWriter(csv_file, fieldnames=fields + angles_fields, dialect='excel-tab')
                    if is_new_file:
                        csv_writer.writeheader()
                    weather: Dict[str, Union[None, int, float]] = \
                        {'WindDir': -1, 'AvgWindSpeed': -1, 'OutsideHum': -1, 'OutsideTemp': -1,
                         'RainRate': -1, 'UVLevel': -1, 'SolarRad': -1}
                    for _d in self.data:
                        if 'weather' in _d:
                            weather = _d['weather']
                            break
                    csv_writer.writerow({**dict(zip(fields, [
                        self.data[0]['time'],
                        self.data[0]['timestamp'],
                        weather['WindDir'],
                        weather['AvgWindSpeed'],
                        weather['OutsideHum'],
                        weather['OutsideTemp'],
                        weather['RainRate'],
                        weather['UVLevel'],
                        weather['SolarRad'],
                    ])), **angles_data})
            self.data = []

    def update_plot_legend(self, bbox_to_anchor: Optional[Tuple[float, float]] = None) -> None:
        if bbox_to_anchor is None:
            bbox_to_anchor = self.bbox_to_anchor
        else:
            self.bbox_to_anchor = bbox_to_anchor
        self._plot_legend = self.plot.legend(loc='upper left', bbox_to_anchor=bbox_to_anchor)
        for _legend_line in self._plot_legend.get_lines():
            _legend_line.set_picker(True)
            _legend_line.set_pickradius(5)
        self.plot.figure.canvas.draw()

    def update_τ_plot_legend(self, bbox_to_anchor: Optional[Tuple[float, float]] = None) -> None:
        if bbox_to_anchor is None:
            bbox_to_anchor = self.bbox_to_anchor
        else:
            self.bbox_to_anchor = bbox_to_anchor
        self._τ_plot_legend: Legend = self.τ_plot.legend(loc='upper left', bbox_to_anchor=bbox_to_anchor)
        for _legend_line in self._τ_plot_legend.get_lines():
            _legend_line.set_picker(True)
            _legend_line.set_pickradius(5)
        self.τ_plot.figure.canvas.draw()

    def update_legends(self, bbox_to_anchor: Optional[Tuple[float, float]] = None) -> None:
        self.update_plot_legend(bbox_to_anchor)
        self.update_τ_plot_legend(bbox_to_anchor)

    def move_legends(self, bbox_to_anchor: Optional[Tuple[float, float]] = None) -> None:
        if bbox_to_anchor is None:
            bbox_to_anchor = self.bbox_to_anchor
        else:
            self.bbox_to_anchor = bbox_to_anchor
        self._plot_legend.set_bbox_to_anchor(bbox_to_anchor)
        self._τ_plot_legend.set_bbox_to_anchor(bbox_to_anchor)

    @property
    def legends(self) -> List[Legend]:
        return [self._plot_legend, self._τ_plot_legend]

    @property
    def plot_lines_styles(self) -> List[Dict[str, Union[str, float, None]]]:
        return [dict(map(lambda p: (p, getattr(line, 'get_' + p)()), LINE_PROPERTIES)) for line in self._plot_lines]

    @plot_lines_styles.setter
    def plot_lines_styles(self, props: List[Dict[str, Union[str, float, None]]]) -> None:
        for index, line in enumerate(self._plot_lines):
            for key, value in props[index].items():
                attr: str = 'set_' + key
                if hasattr(line, attr):
                    getattr(line, attr)(value)
        self.update_plot_legend()

    @property
    def τ_plot_lines(self) -> List[Line2D]:
        return (self._τ_plot_lines + self._τ_plot_alt_lines + self._τ_plot_alt_bb_lines
                + self._τ_plot_leastsq_lines
                + self._τ_plot_magic_lines
                # + self._τ_plot_magic_alt_lines
                )

    @property
    def τ_plot_lines_styles(self) -> List[Dict[str, Union[str, float, None]]]:
        return [dict(map(lambda p: (p, getattr(line, 'get_' + p)()), LINE_PROPERTIES))
                for line in self.τ_plot_lines]

    @τ_plot_lines_styles.setter
    def τ_plot_lines_styles(self, props: List[Dict[str, Union[str, float, None]]]) -> None:
        for index, line in enumerate(self.τ_plot_lines):
            if index >= len(props):
                break
            for key, value in props[index].items():
                attr: str = 'set_' + key
                if hasattr(line, attr):
                    getattr(line, attr)(value)
        self.update_τ_plot_legend()

    @property
    def plot_lines_visibility(self) -> List[bool]:
        return [line.get_visible() for line in self._plot_lines]

    @plot_lines_visibility.setter
    def plot_lines_visibility(self, states: List[bool]) -> None:
        for line, vis in zip(self._plot_lines, states):
            line.set_visible(True)
            line.set_alpha(1.0 if vis else 0.2)
        self.update_plot_legend()
        for line, vis in zip(self._plot_lines, states):
            line.set_visible(vis)
        self.plot.figure.canvas.draw()

    @property
    def τ_plot_lines_visibility(self) -> List[bool]:
        return [line.get_visible() for line in self.τ_plot_lines]

    @τ_plot_lines_visibility.setter
    def τ_plot_lines_visibility(self, states: List[bool]) -> None:
        # FIXME: when setting line visibility to False, lines disappear from the legend, too
        for line, vis in zip(self.τ_plot_lines, states):
            line.set_visible(True)
            line.set_alpha(1.0 if vis else 0.2)
        self.update_τ_plot_legend()
        for line, vis in zip(self.τ_plot_lines, states):
            line.set_visible(vis)
        self.τ_plot.figure.canvas.draw()

    @property
    def subplotpars(self) -> Dict[str, float]:
        _attrs: List[str] = ["top", "bottom", "left", "right", "hspace", "wspace"]
        return {attr: float(vars(self.figure.subplotpars)[attr]) for attr in _attrs}

    @subplotpars.setter
    def subplotpars(self, pars: Dict[str, float]) -> None:
        self.figure.subplots_adjust(**pars)
        self.figure.canvas.draw_idle()

    @property
    def adc_channels_names(self) -> List[str]:
        return self._adc_channels_names

    @adc_channels_names.setter
    def adc_channels_names(self, new_names: Iterable[str]) -> None:
        self._adc_channels_names = list(new_names)
        if len(self._adc_channels_names) < len(self.adc_channels):
            self._adc_channels_names += list(f'ch {ch + 1}'
                                             for ch in self.adc_channels[len(self._adc_channels_names):])
        for index, (current_label, ch) in enumerate(zip(self._adc_channels_names, self.adc_channels)):
            if not current_label:
                self._adc_channels_names[index] = f'ch {ch + 1}'
        label_lines(self._plot_lines, self._adc_channels_names)
        label_lines(self._τ_plot_lines, self._adc_channels_names)
        label_lines(self._τ_plot_alt_lines, self._adc_channels_names, suffix='alt')
        label_lines(self._τ_plot_alt_bb_lines, self._adc_channels_names, suffix='alt, bb alt')
        label_lines(self._τ_plot_leastsq_lines, self._adc_channels_names, suffix='leastsq')
        label_lines(self._τ_plot_magic_lines, self._adc_channels_names, suffix='3 angles')
        # label_lines(self._τ_plot_magic_alt_lines, self._adc_channels_names, suffix='3 angles alt')
        self.update_legends()

    def set_adc_channels_names(self, new_names: List[str]) -> None:
        self.adc_channels_names = new_names


if __name__ == '__main__':
    def main() -> None:
        ap = argparse.ArgumentParser(description='Radiometer controller')
        ap.add_argument('--no-gui', help='run without graphical interface', action='store_true', default=False)
        with open('/tmp/log', 'at') as f_out:
            f_out.write(f'{time.asctime()}\tparsing args\n')
        args, unknown_keys = ap.parse_known_args()
        if unknown_keys:
            with open('/tmp/log', 'at') as f_out:
                f_out.write(f'{time.asctime()}\tgot unknown keys: {unknown_keys}\n')

        # https://stackoverflow.com/a/7758075/8554611
        # Without holding a reference to our socket somewhere it gets garbage
        # collected when the function exits
        _lock_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        with open('/tmp/log', 'at') as f_out:
            f_out.write(f'{time.asctime()}\tchecking lock\n')
        for check_number in range(2):
            try:
                _lock_socket.bind('\0' + __file__)
            except socket.error as ex:
                print(f'{__file__} is already running')

                import traceback

                with open('/tmp/log', 'at') as f_out:
                    f_out.write(f'{time.asctime()}\tsocket occupied\n')
                    f_out.write(f'{time.asctime()}\t{ex}\n')
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    traceback.print_tb(exc_traceback, file=f_out)
                    traceback.print_exception(exc_type, exc_value, exc_traceback, file=f_out)
                    traceback.print_exc(file=f_out)
                    f_out.write(traceback.format_exc())
            else:
                if not args.no_gui:
                    make_desktop_launcher(os.path.abspath(__file__))
                    app = QApplication(sys.argv)
                    with open('/tmp/log', 'at') as f_out:
                        f_out.write(f'{time.asctime()}\tcreating window\n')
                    try:
                        window = App()
                    except Exception as ex:
                        import traceback

                        with open('/tmp/log', 'at') as f_out:
                            f_out.write(f'{time.asctime()}\t{ex}\n')
                            f_out.write(f'{time.asctime()}\twindow not created\n')
                            exc_type, exc_value, exc_traceback = sys.exc_info()
                            traceback.print_tb(exc_traceback, file=f_out)
                            traceback.print_exception(exc_type, exc_value, exc_traceback, file=f_out)
                            traceback.print_exc(file=f_out)
                            f_out.write(traceback.format_exc())
                            sys.exit(0)
                    with open('/tmp/log', 'at') as f_out:
                        f_out.write(f'{time.asctime()}\tshowing window\n')
                    window.show()
                    with open('/tmp/log', 'at') as f_out:
                        f_out.write(f'{time.asctime()}\tstarting app\n')
                    app.exec_()
                break


    main()
