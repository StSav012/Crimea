# -*- coding: utf-8 -*-

import csv
import gzip
import json
import os
import time
from datetime import datetime
from threading import Thread
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QInputDialog, QMessageBox
from matplotlib.axes import Axes
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT
from matplotlib.dates import date2num
from matplotlib.figure import Figure
from matplotlib.legend import Legend
from matplotlib.lines import Line2D

import figureoptions
import utils
from subplot_tool import SubplotToolQt

try:
    import smsd_dummy as smsd
except ImportError:
    import smsd
try:
    import radiometer_dummy as radiometer
except ImportError:
    import radiometer
import dallas
import temperature_backend

LINE_PROPERTIES: List[str] = ['color', 'dash_capstyle', 'dash_joinstyle', 'drawstyle', 'fillstyle', 'linestyle',
                              'linewidth', 'marker', 'markeredgecolor', 'markeredgewidth', 'markerfacecolor',
                              'markerfacecoloralt', 'markersize', 'markevery', 'solid_capstyle', 'solid_joinstyle']


class NavigationToolbar(NavigationToolbar2QT):
    def __init__(self, canvas, parent, coordinates: bool = True):
        super().__init__(canvas, parent, coordinates)
        self.toolbar_parent_hot_fix = parent

    def _init_toolbar(self):
        pass

    def edit_parameters(self):
        axes = self.canvas.figure.get_axes()
        if not axes:
            QMessageBox.warning(self.parent, "Error", "There are no axes to edit.")
            return
        elif len(axes) == 1:
            ax, = axes
        else:
            titles = [
                ax.get_label() or
                ax.get_title() or
                " — ".join(filter(None, [ax.get_xlabel(), ax.get_ylabel()])) or
                f"<anonymous {type(ax).__name__}>"
                for ax in axes]
            duplicate_titles = [
                title for title in titles if titles.count(title) > 1]
            for i, ax in enumerate(axes):
                if titles[i] in duplicate_titles:
                    titles[i] += f" (id: {id(ax):#x})"  # Deduplicate titles.
            item, ok = QInputDialog.getItem(
                self.canvas.parent(), 'Customize', 'Select axes:', titles, 0, False)
            if not ok:
                return
            ax = axes[titles.index(item)]
        figureoptions.figure_edit(ax, self.toolbar_parent_hot_fix)

    def configure_subplots(self):
        image = utils.get_icon('subplots.svg')
        dia = SubplotToolQt(self.canvas.figure,
                            self.toolbar_parent_hot_fix.plot.legends,
                            title='Subplots options',
                            labels=self.toolbar_parent_hot_fix.plot.adc_channels_names,
                            labels_changed_callback=self.toolbar_parent_hot_fix.plot.set_adc_channels_names)
        dia.setWindowIcon(QIcon(image))
        dia.exec_()
        self.toolbar_parent_hot_fix.plot.bbox_to_anchor = \
            (getattr(self.toolbar_parent_hot_fix.plot.legends[0].get_bbox_to_anchor(), '_bbox').xmin,
             getattr(self.toolbar_parent_hot_fix.plot.legends[0].get_bbox_to_anchor(), '_bbox').ymax)


def label_lines(lines: List[Line2D], labels: List[str], suffix: str = ''):
    for line, label in zip(lines, labels):
        line.set_label(f'{label} ({suffix})' if suffix else label)


class Plot(Thread):
    def __init__(self, *, serial_device, microstepping_mode, speed,
                 adc_channels: List[int],
                 figure: Figure,
                 adc_channels_names: Optional[List[str]] = None,
                 measurement_delay: float = 0, init_angle: float = 0,
                 output_folder: str = os.path.curdir,
                 results_file_prefix: str = '', ratio: float = 1.0):
        Thread.__init__(self)
        self.daemon = True

        self.bbox_to_anchor: Tuple[float, float] = (1.10, 1)

        self._figure: Figure = figure

        self._plot: Axes = figure.add_subplot(2, 1, 1)
        self._plot.autoscale()
        box = self._plot.get_position()
        self._plot.set_position([box.x0, box.y0, box.width * 0.8, box.height])
        self._plot.set_xlabel('Time')
        self._plot.set_ylabel('Voltage [V]')
        self._plot.set_label('Voltage')
        self._plot.set_autoscale_on(True)
        self._plot.format_coord = lambda x, y: f'voltage = {y:.3f} V'
        self._plot.callbacks.connect('xlim_changed', self.on_xlim_changed)
        self._plot.callbacks.connect('ylim_changed', self.on_ylim_changed)
        self._plot_lines: List[Line2D] = [self._plot.plot_date(np.empty(0), np.empty(0))[0]
                                          for _ in adc_channels]

        self._τ_plot: Axes = figure.add_subplot(2, 1, 2, sharex=self._plot)
        self._τ_plot.autoscale()
        box = self._τ_plot.get_position()
        self._τ_plot.set_position([box.x0, box.y0, box.width * 0.8, box.height])
        self._τ_plot.set_xlabel('Time')
        self._τ_plot.set_ylabel('τ')
        self._τ_plot.set_label('Absorption')
        # self._τ_plot.callbacks.connect('xlim_changed', self.on_xlim_changed)
        self._τ_plot.callbacks.connect('ylim_changed', self.on_ylim_changed)
        self._τ_plot_lines: List[Line2D] = [self._τ_plot.plot_date(np.empty(0), np.empty(0),
                                                                   color=self._plot_lines[ch].get_color(),
                                                                   ls='-')[0]
                                            for ch in range(len(self._plot_lines))]
        self._τ_plot_alt_lines: List[Line2D] = [self._τ_plot.plot_date(np.empty(0), np.empty(0),
                                                                       color=self._plot_lines[ch].get_color(),
                                                                       ls='--')[0]
                                                for ch in range(len(self._plot_lines))]
        self._τ_plot_alt_bb_lines: List[Line2D] = [self._τ_plot.plot_date(np.empty(0), np.empty(0),
                                                                          color=self._plot_lines[ch].get_color(),
                                                                          ls='--')[0]
                                                   for ch in range(len(self._plot_lines))]
        self._τ_plot_leastsq_lines: List[Line2D] = [self._τ_plot.plot_date(np.empty(0), np.empty(0),
                                                                           color=self._plot_lines[ch].get_color(),
                                                                           ls=':')[0]
                                                    for ch in range(len(self._plot_lines))]
        self._τ_plot_magic_lines: List[Line2D] = [self._τ_plot.plot_date(np.empty(0), np.empty(0),
                                                                         color=self._plot_lines[ch].get_color(),
                                                                         ls='-.')[0]
                                                  for ch in range(len(self._plot_lines))]
        # self._τ_plot_magic_alt_lines: List[Line2D] = [self._τ_plot.plot_date(np.empty(0), np.empty(0),
        #                                                                      color=self._plot_lines[ch].get_color(),
        #                                                                      ls='-.')[0]
        #                                               for ch in range(len(self._plot_lines))]

        if adc_channels_names is None:
            self._adc_channels_names: List[str] = list(f'ch {ch + 1}' for ch in adc_channels)
        else:
            self._adc_channels_names: List[str] = adc_channels_names[:len(adc_channels)]
            if len(self._adc_channels_names) < len(adc_channels):
                self._adc_channels_names += list(f'ch {ch + 1}' for ch in adc_channels[len(self._adc_channels_names):])
            for index, (current_label, ch) in enumerate(zip(self._adc_channels_names, adc_channels)):
                if not current_label:
                    self._adc_channels_names[index] = f'ch {ch + 1}'

        label_lines(self._plot_lines, self._adc_channels_names)
        label_lines(self._τ_plot_lines, self._adc_channels_names)
        label_lines(self._τ_plot_alt_lines, self._adc_channels_names, suffix='alt')
        label_lines(self._τ_plot_alt_bb_lines, self._adc_channels_names, suffix='alt, bb alt')
        label_lines(self._τ_plot_leastsq_lines, self._adc_channels_names, suffix='leastsq')
        label_lines(self._τ_plot_magic_lines, self._adc_channels_names, suffix='3 angles')
        # label_lines(self._τ_plot_magic_alt_lines, self._adc_channels_names, suffix='3 angles alt')

        self._plot_legend: Legend = self._plot.legend(loc='upper left', bbox_to_anchor=self.bbox_to_anchor)
        for legend_line in self._plot_legend.get_lines():
            legend_line.set_picker(True)
            legend_line.set_pickradius(5)
        self._τ_plot_legend: Legend = self._τ_plot.legend(loc='upper left', bbox_to_anchor=self.bbox_to_anchor)
        for legend_line in self._τ_plot_legend.get_lines():
            legend_line.set_picker(True)
            legend_line.set_pickradius(5)

        self._wind_plot: Axes = self._τ_plot.twinx()
        self._wind_plot.set_position([box.x0, box.y0, box.width * 0.8, box.height])
        self._wind_plot.set_navigate(False)
        self._τ_plot.set_zorder(self._wind_plot.get_zorder() + 1)
        self._τ_plot.patch.set_visible(False)
        self._wind_plot.patch.set_visible(True)
        self._wind_plot.set_ylabel('Wind')
        self._wind_plot.set_label('Wind')
        self._τ_plot.format_coord = lambda x, y: 'τ = {:.3f}\nwind speed = {:.3f}'.format(
            y, self._wind_plot.transData.inverted().transform(self._τ_plot.transData.transform((x, y)))[-1])
        self._wind_plot_line, = self._wind_plot.plot_date(np.empty(0), np.empty(0), 'k:')

        def on_pick(event):
            # on the pick event, find the orig line corresponding to the
            # legend proxy line, and toggle the visibility
            _legend_line = event.artist
            if _legend_line in self._plot_legend.get_lines():
                _legend = '_plot_legend'
                _lines = self._plot_lines
                _axes = self._plot
            elif _legend_line in self._τ_plot_legend.get_lines():
                _legend = '_τ_plot_legend'
                _lines = self.τ_plot_lines
                _axes = self._τ_plot
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

        figure.canvas.mpl_connect('pick_event', on_pick)

        self._is_running: bool = False
        self._measured: bool = False
        self._closing: bool = False
        self._adc_channels: List[int] = adc_channels[:]
        self._x: np.ndarray = np.empty(0)
        self._y: List[np.ndarray] = [np.empty(0)] * len(adc_channels)
        self._τx: List[np.ndarray] = [np.empty(0)] * len(adc_channels)
        self._τy: List[np.ndarray] = [np.empty(0)] * len(adc_channels)
        self._τx_alt: List[np.ndarray] = [np.empty(0)] * len(adc_channels)
        self._τy_alt: List[np.ndarray] = [np.empty(0)] * len(adc_channels)
        self._τx_bb_alt: List[np.ndarray] = [np.empty(0)] * len(adc_channels)
        self._τy_bb_alt: List[np.ndarray] = [np.empty(0)] * len(adc_channels)
        self._τx_leastsq: List[np.ndarray] = [np.empty(0)] * len(adc_channels)
        self._τy_leastsq: List[np.ndarray] = [np.empty(0)] * len(adc_channels)
        # self._τy_error_leastsq: List[np.ndarray] = [np.empty(0)] * len(adc_channels)
        self._τx_magic: List[np.ndarray] = [np.empty(0)] * len(adc_channels)
        self._τy_magic: List[np.ndarray] = [np.empty(0)] * len(adc_channels)
        # self._τx_magic_alt: List[np.ndarray] = [np.empty(0)] * len(adc_channels)
        # self._τy_magic_alt: List[np.ndarray] = [np.empty(0)] * len(adc_channels)
        self._wind_x: np.ndarray = np.empty(0)
        self._wind_y: np.ndarray = np.empty(0)
        self._current_x: datetime = datetime.now()
        self._current_y: List[np.ndarray] = [np.empty(0)] * len(adc_channels)

        self._adc = radiometer.ADC(channels=adc_channels, timeout=0.1)
        self._adc.start()

        self._motor = smsd.Motor(device=serial_device, microstepping_mode=microstepping_mode, speed=speed, ratio=ratio)
        self._motor.start()
        self._motor.open()

        self._measurement_delay: float = measurement_delay
        self._start_time: Optional[float] = None
        self._stop_time: Optional[float] = None
        self._current_angle: float = init_angle

        self._meteo = dallas.Dallas()

        self.arduino = temperature_backend.Dallas18B20()
        self.arduino.start()

        self.output_folder: str = output_folder
        self.summary_file_prefix: str = results_file_prefix
        if results_file_prefix:
            print('summary is stored into', ', '.join(f'{self.summary_file_prefix}.{ch + 1}.csv'
                                                      for ch in range(len(adc_channels))))
        self.data: List[dict] = []

    def close(self):
        self._adc.stop()
        self._adc.join()
        self._motor.disable()
        self._motor.join()
        self.arduino.stop()
        # FIXME: the following line causes double channel count changes
        # self.arduino.join(timeout=1)
        self._closing = True

    @staticmethod
    def on_xlim_changed(axes: Axes):
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
    # def on_xlim_changed(axes: Axes):
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
    def on_ylim_changed(axes: Axes):
        y_lim = axes.get_ylim()
        auto_scale = True
        for line in axes.lines:
            data = line.get_ydata()[:-1]
            if data.size > 0 and (min(y_lim) > min(data) and max(y_lim) < max(data)):
                auto_scale = False
        axes.set_autoscaley_on(auto_scale)

    @staticmethod
    def on_click(event):
        if event.dblclick and event.inaxes is not None:
            event.inaxes.set_autoscale_on(True)
            event.inaxes.relim(visible_only=True)
            # event.inaxes.autoscale_view(None, True, True)
            event.inaxes.autoscale(enable=True, axis='both')

    def enable_motor(self, enable, new_thread: bool = False):
        if enable:
            self._motor.enable()
            self._motor.forward()
            if new_thread:
                Thread(target=self.move_home).start()
            else:
                self.move_home()
        else:
            self._motor.disable()

    def move_90degrees(self):
        self._motor.move(90)
        self._current_angle += 90
        return self._motor.time_to_turn(90)

    def move_360degrees_right(self):
        self._motor.move(360)
        self._current_angle += 360
        return self._motor.time_to_turn(360)

    def move_360degrees_left(self):
        self._motor.move(-360)
        self._current_angle -= 360
        return self._motor.time_to_turn(360)

    def time_to_move_home(self):
        return (self._motor.time_to_turn(self._current_angle)
                + self._motor.time_to_turn(360)
                + 2. * self._motor.time_to_turn(25))

    def move_home(self):
        self._motor.move(-self._current_angle)
        time.sleep(self._motor.time_to_turn(self._current_angle))
        v = self.arduino.voltage('A0')
        if v is None or v > 512:
            print('making whole turn')
            self._motor.forward()
            self._motor.move_home()
            time.sleep(self._motor.time_to_turn(360))
        self._motor.move(-25)
        time.sleep(self._motor.time_to_turn(25))
        self._motor.forward()
        self._motor.move_home()
        time.sleep(self._motor.time_to_turn(25))
        self._current_angle = 0

    def set_microstepping_mode(self, mode):
        self._motor.set_microstepping_mode(mode)

    def set_motor_speed(self, speed):
        self._motor.speed(speed)

    def set_gear_ratio(self, ratio):
        self._motor.gear_ratio(ratio)

    def set_measurement_delay(self, delay):
        _delay = float(delay)
        if _delay < 0.0:
            raise ValueError('Measurement delay can not be negative')
        self._measurement_delay = _delay

    def set_running(self, is_running):
        self._is_running = bool(is_running)

    def measurement_time(self, angle, duration):
        """ convenience function """
        return self._motor.time_to_turn(angle - self._current_angle) + self._measurement_delay + duration

    def measure(self, angle, duration):
        self._motor.move(angle - self._current_angle)
        self._start_time = \
            time.perf_counter() + self._motor.time_to_turn(angle - self._current_angle) + self._measurement_delay
        self._stop_time = self._start_time + duration
        self._current_x = datetime.now()
        self._is_running = True
        self._current_angle = angle
        self._measured = False

    def has_measured(self):
        return self._measured

    def set_point(self):
        self.purge_obsolete_data()
        data_item: Dict[str, Union[Dict[str, Union[None, str, float]],
                                   List[float], List[bool], List[List[float]],
                                   None, bool, float, str]] = {}
        weather_data: Dict[str, Union[None, int, float, str, List[None, int, float]]] = self._meteo.get_realtime_data()
        if weather_data:
            data_item['weather'] = weather_data
            self._wind_x = np.concatenate((self._wind_x, np.array([date2num(datetime.now())])))
            self._wind_y = np.concatenate((self._wind_y,
                                           np.array([weather_data['AvgWindSpeed']
                                                     * np.cos(np.radians(weather_data['WindDir']))])))
            self._wind_plot_line.set_data(self._wind_x, self._wind_y)
            self._wind_plot.relim(visible_only=True)
            # follow the autoscale settings of self._τ_plot
            self._wind_plot.autoscale_view(None, self._τ_plot.get_autoscalex_on(), True)
        data_item['temperatures'] = self.arduino.temperatures
        data_item['setpoints'] = self.arduino.setpoints
        data_item['states'] = self.arduino.states
        data_item['enabled'] = self.arduino.enabled
        data_item['timestamp'] = self._current_x.timestamp()
        data_item['time'] = self._current_x.isoformat()
        data_item['angle'] = self._current_angle
        # noinspection PyTypeChecker
        data_item['voltage'] = [ys.tolist() for ys in self._current_y]
        self.data.append(data_item)
        self._x = np.concatenate((self._x, np.array([date2num(self._current_x)])))
        for ch, ys in enumerate(self._current_y):
            if ys.size:
                self._y[ch] = np.concatenate((self._y[ch], np.array([np.mean(ys)])))
                if self._x.shape != self._y[ch].shape:
                    print('data shapes don\'t match:')
                    print('channel', ch)
                    print(self._x)
                    print(self._y[ch])
                else:
                    self._plot_lines[ch].set_data(self._x, self._y[ch])
            else:
                print('empty y for channel', ch + 1)
                self._y[ch] = np.concatenate((self._y[ch], np.array([np.nan])))
            self._current_y[ch] = np.array([])
        self._plot.relim(visible_only=True)
        self._plot.autoscale_view(None, self._plot.get_autoscalex_on(), self._plot.get_autoscaley_on())
        self._τ_plot.relim(visible_only=True)
        self._τ_plot.autoscale_view(None, False, self._τ_plot.get_autoscaley_on())
        # rotate and align the tick labels so they look better
        self._figure.autofmt_xdate(bottom=self.subplotpars['bottom'])
        self._figure.canvas.draw_idle()
        self._is_running = False
        self._measured = True

    def purge_obsolete_data(self, purge_all: bool = False):
        current_time: float = date2num(datetime.now())
        time_span: float = 1.0
        not_obsolete: np.ndarray = (current_time - self._x <= time_span)
        self._x = self._x[not_obsolete]
        self._y = [self._y[ch][not_obsolete] for ch in range(len(self._y))]
        if self._x.size > 0 and self._x[0] > np.mean(self._plot.get_xlim()):
            self._plot.set_autoscalex_on(True)
        for ch in range(len(self._τx)):
            not_obsolete: np.ndarray = (current_time - self._τx[ch] <= time_span)
            self._τx[ch] = self._τx[ch][not_obsolete]
            self._τy[ch] = self._τy[ch][not_obsolete]
            if self._τx[ch].size > 0 and self._τx[ch][0] > np.mean(self._τ_plot.get_xlim()):
                self._τ_plot.set_autoscalex_on(True)
        for ch in range(len(self._τx_alt)):
            not_obsolete: np.ndarray = (current_time - self._τx_alt[ch] <= time_span)
            self._τx_alt[ch] = self._τx_alt[ch][not_obsolete]
            self._τy_alt[ch] = self._τy_alt[ch][not_obsolete]
            if self._τx_alt[ch].size > 0 and self._τx_alt[ch][0] > np.mean(self._τ_plot.get_xlim()):
                self._τ_plot.set_autoscalex_on(True)
        for ch in range(len(self._τx_bb_alt)):
            not_obsolete: np.ndarray = (current_time - self._τx_bb_alt[ch] <= time_span)
            self._τx_bb_alt[ch] = self._τx_bb_alt[ch][not_obsolete]
            self._τy_bb_alt[ch] = self._τy_bb_alt[ch][not_obsolete]
            if self._τx_bb_alt[ch].size > 0 and self._τx_bb_alt[ch][0] > np.mean(self._τ_plot.get_xlim()):
                self._τ_plot.set_autoscalex_on(True)
        for ch in range(len(self._τx_leastsq)):
            not_obsolete: np.ndarray = (current_time - self._τx_leastsq[ch] <= time_span)
            self._τx_leastsq[ch] = self._τx_leastsq[ch][not_obsolete]
            self._τy_leastsq[ch] = self._τy_leastsq[ch][not_obsolete]
            # self._τy_error_leastsq[ch] = self._τy_error_leastsq[ch][not_obsolete]
            if self._τx_leastsq[ch].size > 0 and self._τx_leastsq[ch][0] > np.mean(self._τ_plot.get_xlim()):
                self._τ_plot.set_autoscalex_on(True)
        for ch in range(len(self._τx_magic)):
            not_obsolete: np.ndarray = (current_time - self._τx_magic[ch] <= time_span)
            self._τx_magic[ch] = self._τx_magic[ch][not_obsolete]
            self._τy_magic[ch] = self._τy_magic[ch][not_obsolete]
            if self._τx_magic[ch].size > 0 and self._τx_magic[ch][0] > np.mean(self._τ_plot.get_xlim()):
                self._τ_plot.set_autoscalex_on(True)
        # for ch in range(len(self._τx_magic_alt)):
        #     not_obsolete: np.ndarray = (current_time - self._τx_magic_alt[ch] <= time_span)
        #     self._τx_magic_alt[ch] = self._τx_magic_alt[ch][not_obsolete]
        #     self._τy_magic_alt[ch] = self._τy_magic_alt[ch][not_obsolete]
        #     if self._τx_magic_alt[ch].size > 0 and self._τx_magic_alt[ch][0] > np.mean(self._τ_plot.get_xlim()):
        #         self._τ_plot.set_autoscalex_on(True)
        not_obsolete: np.ndarray = (current_time - self._wind_x <= time_span)
        self._wind_x = self._wind_x[not_obsolete]
        self._wind_y = self._wind_y[not_obsolete]
        if self._wind_x.size > 0 and self._wind_x[0] > np.mean(self._wind_plot.get_xlim()):
            self._wind_plot.set_autoscalex_on(True)
        if purge_all:
            self.data = []

    def last_data(self):
        return [self._y[ch][-1] if self._y[ch].size else None for ch in range(len(self._y))]

    def last_weather(self):
        return self.data[-1]['weather'] if len(self.data) > 0 and 'weather' in self.data[-1] else None

    def add_τ(self, channel: int, τ: float):
        current_time: float = date2num(datetime.now())
        self._τx[channel] = np.concatenate((self._τx[channel], np.array([current_time])))
        self._τy[channel] = np.concatenate((self._τy[channel], np.array([τ])))
        for ch in range(len(self._τy)):
            self._τ_plot_lines[ch].set_data(self._τx[ch], self._τy[ch])

    def add_τ_alt(self, channel: int, τ: float):
        current_time: float = date2num(datetime.now())
        self._τx_alt[channel] = np.concatenate((self._τx_alt[channel], np.array([current_time])))
        self._τy_alt[channel] = np.concatenate((self._τy_alt[channel], np.array([τ])))
        for ch in range(len(self._τy_alt)):
            self._τ_plot_alt_lines[ch].set_data(self._τx_alt[ch], self._τy_alt[ch])

    def add_τ_bb_alt(self, channel: int, τ: float):
        current_time: float = date2num(datetime.now())
        self._τx_bb_alt[channel] = np.concatenate((self._τx_bb_alt[channel], np.array([current_time])))
        self._τy_bb_alt[channel] = np.concatenate((self._τy_bb_alt[channel], np.array([τ])))
        for ch in range(len(self._τy_bb_alt)):
            self._τ_plot_alt_bb_lines[ch].set_data(self._τx_bb_alt[ch], self._τy_bb_alt[ch])

    def add_τ_leastsq(self, channel: int, τ: float, error: float = np.nan):
        current_time: float = date2num(datetime.now())
        self._τx_leastsq[channel] = np.concatenate((self._τx_leastsq[channel], np.array([current_time])))
        self._τy_leastsq[channel] = np.concatenate((self._τy_leastsq[channel], np.array([τ])))
        # self._τy_error_leastsq[channel] = np.concatenate((self._τy_error_leastsq[channel], np.array([error])))
        del error
        for ch in range(len(self._τy_leastsq)):
            self._τ_plot_leastsq_lines[ch].set_data(self._τx_leastsq[ch], self._τy_leastsq[ch])

    def add_τ_magic_angles(self, channel: int, τ: float):
        current_time: float = date2num(datetime.now())
        self._τx_magic[channel] = np.concatenate((self._τx_magic[channel], np.array([current_time])))
        self._τy_magic[channel] = np.concatenate((self._τy_magic[channel], np.array([τ])))
        for ch in range(len(self._τy_magic)):
            self._τ_plot_magic_lines[ch].set_data(self._τx_magic[ch], self._τy_magic[ch])

    # def add_τ_magic_angles_alt(self, channel: int, τ: float):
    #     current_time: float = date2num(datetime.now())
    #     self._τx_magic_alt[channel] = np.concatenate((self._τx_magic_alt[channel], np.array([current_time])))
    #     self._τy_magic_alt[channel] = np.concatenate((self._τy_magic_alt[channel], np.array([τ])))
    #     for ch in range(len(self._τy_magic_alt)):
    #         self._τ_plot_magic_alt_lines[ch].set_data(self._τx_magic_alt[ch], self._τy_magic_alt[ch])

    def pack_data(self):
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
            for ch in range(len(self._τy)):
                path: str = f'{self.summary_file_prefix}.{ch + 1}.csv'
                is_new_file: bool = not os.path.exists(path)
                if not is_new_file and (os.path.isdir(path) or not os.access(path, os.W_OK)):
                    print('ERROR: can not append to', path)
                    continue
                with open(path, 'a') as csv_file:
                    angles_data: Dict[float, float] = {}
                    for a in self.data:
                        angles_data[a['angle']] = float(np.mean(a['voltage'][ch]))
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

    def update_plot_legend(self, bbox_to_anchor: Optional[Tuple[float, float]] = None):
        if bbox_to_anchor is None:
            bbox_to_anchor = self.bbox_to_anchor
        else:
            self.bbox_to_anchor = bbox_to_anchor
        self._plot_legend = self._plot.legend(loc='upper left', bbox_to_anchor=bbox_to_anchor)
        for _legend_line in self._plot_legend.get_lines():
            _legend_line.set_picker(True)
            _legend_line.set_pickradius(5)
        self._plot.figure.canvas.draw()

    def update_τ_plot_legend(self, bbox_to_anchor: Optional[Tuple[float, float]] = None):
        if bbox_to_anchor is None:
            bbox_to_anchor = self.bbox_to_anchor
        else:
            self.bbox_to_anchor = bbox_to_anchor
        self._τ_plot_legend: Legend = self._τ_plot.legend(loc='upper left', bbox_to_anchor=bbox_to_anchor)
        for _legend_line in self._τ_plot_legend.get_lines():
            _legend_line.set_picker(True)
            _legend_line.set_pickradius(5)
        self._τ_plot.figure.canvas.draw()

    def update_legends(self, bbox_to_anchor: Optional[Tuple[float, float]] = None):
        self.update_plot_legend(bbox_to_anchor)
        self.update_τ_plot_legend(bbox_to_anchor)

    def move_legends(self, bbox_to_anchor: Optional[Tuple[float, float]] = None):
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
    def plot_lines_styles(self, props: List[Dict[str, Union[str, float, None]]]):
        for index, line in enumerate(self._plot_lines):
            for key, value in props[index].items():
                attr: str = 'set_' + key
                if hasattr(line, attr):
                    getattr(line, attr)(value)
        self.update_plot_legend()

    @property
    def τ_plot_lines(self):
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
    def τ_plot_lines_styles(self, props: List[Dict[str, Union[str, float, None]]]):
        for index, line in enumerate(self.τ_plot_lines):
            if index >= len(props):
                break
            for key, value in props[index].items():
                attr: str = 'set_' + key
                if hasattr(line, attr):
                    getattr(line, attr)(value)
        self.update_τ_plot_legend()

    @property
    def plot_lines_visibility(self):
        return [line.get_visible() for line in self._plot_lines]

    @plot_lines_visibility.setter
    def plot_lines_visibility(self, states: List[bool]):
        for line, vis in zip(self._plot_lines, states):
            line.set_visible(True)
            line.set_alpha(1.0 if vis else 0.2)
        self.update_plot_legend()
        for line, vis in zip(self._plot_lines, states):
            line.set_visible(vis)
        self._plot.figure.canvas.draw()

    @property
    def τ_plot_lines_visibility(self):
        return [line.get_visible() for line in self.τ_plot_lines]

    @τ_plot_lines_visibility.setter
    def τ_plot_lines_visibility(self, states: List[bool]):
        # FIXME: when setting line visibility to False, lines disappear from the legend, too
        for line, vis in zip(self.τ_plot_lines, states):
            line.set_visible(True)
            line.set_alpha(1.0 if vis else 0.2)
        self.update_τ_plot_legend()
        for line, vis in zip(self.τ_plot_lines, states):
            line.set_visible(vis)
        self._τ_plot.figure.canvas.draw()

    @property
    def subplotpars(self) -> Dict[str, float]:
        _attrs: List[str] = ["top", "bottom", "left", "right", "hspace", "wspace"]
        return {attr: float(vars(self._figure.subplotpars)[attr]) for attr in _attrs}

    @subplotpars.setter
    def subplotpars(self, pars: Dict[str, float]):
        self._figure.subplots_adjust(**pars)
        self._figure.canvas.draw_idle()

    @property
    def adc_channels_names(self) -> List[str]:
        return self._adc_channels_names

    @adc_channels_names.setter
    def adc_channels_names(self, new_names: List[str]):
        self._adc_channels_names = new_names[:]
        if len(self._adc_channels_names) < len(self._adc_channels):
            self._adc_channels_names += list(f'ch {ch + 1}'
                                             for ch in self._adc_channels[len(self._adc_channels_names):])
        for index, (current_label, ch) in enumerate(zip(self._adc_channels_names, self._adc_channels)):
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

    def set_adc_channels_names(self, new_names: List[str]):
        self.adc_channels_names = new_names

    def run(self):
        try:
            while not self._closing:
                if self._is_running and self._stop_time:
                    while self._is_running and time.perf_counter() <= self._stop_time and not self._closing:
                        if time.perf_counter() >= self._start_time:
                            for ch in self._adc_channels:
                                v = self._adc.voltages[ch]
                                if v is not None:
                                    self._current_y[ch] = np.concatenate((self._current_y[ch], np.array([v])))
                        if self._is_running and time.perf_counter() <= self._stop_time and not self._closing:
                            time.sleep(0.1)
                        elif self._is_running and time.perf_counter() <= self._start_time and not self._closing:
                            time.sleep(0.01)
                    if self._is_running and not self._closing:
                        self.set_point()
                elif not self._closing:
                    time.sleep(0.1)
        except (KeyboardInterrupt, SystemExit):
            return
