#!/usr/bin/python3
# -*- coding: utf-8 -*-

# TODO: emulate “ldevio” app with a Python script to check the re-connection when the number of the channels changes
# TODO: translate most of the stuff into Russian

import argparse
import os
import socket
import sys
import time
from typing import List, Any, Dict, Union, Tuple

import matplotlib.style as mplstyle
import numpy as np
from PyQt5.QtCore import QCoreApplication, QMetaObject, QSettings, QTimer, Qt
from PyQt5.QtGui import QIcon, QKeySequence, QPixmap, QValidator
from PyQt5.QtWidgets import QAbstractItemView, QApplication, QCheckBox, QDesktopWidget, QDoubleSpinBox, \
    QFrame, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QMainWindow, QMessageBox, \
    QProgressDialog, QPushButton, QShortcut, QSizePolicy, QSpacerItem, QSpinBox, QTabWidget, QTableWidget, \
    QTableWidgetItem, QTableWidgetSelectionRange, QVBoxLayout, QWidget
from matplotlib import rcParams as PlotParams
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

import backend

try:
    from smsd_dummy import MicrosteppingMode
except ImportError:
    from smsd import MicrosteppingMode

mplstyle.use('fast')

try:
    import cycler

    PlotParams['axes.prop_cycle'] = cycler.cycler(color='brgcmyk')
except (ImportError, KeyError):
    pass


class SpinListBox(QSpinBox):
    def __init__(self, parent=None, values=None):
        QSpinBox.__init__(self, parent)
        if values is None:
            values = ['']
        self.values = []
        self.setValues(values)
        self.lineEdit().setReadOnly(True)
        self.lineEdit().selectionChanged.connect(lambda: self.lineEdit().setSelection(0, 0))

    def setValues(self, values):
        self.values = values
        self.setRange(0, len(self.values) - 1)

    def validate(self, text, pos):
        return QValidator.Acceptable, text, pos

    def valueFromText(self, text):
        return self.values.index(text)

    def textFromValue(self, value):
        return self.values[value]


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


def make_launcher(entry_path: str):
    if not os.path.exists(entry_path):
        try:
            import stat
            with open(entry_path, 'w') as fout:
                fout.writelines('\n'.join([
                    '[Desktop Entry]',
                    'Version=1.1',
                    'Name=Crimea Radiometer',
                    f'Comment=Crimea Radiometer Controller, {time.localtime().tm_year}',
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
    desktop_entry_path = os.path.join(desktop_path, 'Crimea Radiometer.desktop')
    make_launcher(desktop_entry_path)


def make_autostart_launcher():
    autostart_path = os.path.join(os.path.expanduser('~'), '.config', 'autostart')
    autostart_entry_path = os.path.join(autostart_path, 'Crimea Radiometer.desktop')
    make_launcher(autostart_entry_path)


class App(QMainWindow):
    def __init__(self):
        super().__init__(flags=Qt.WindowFlags())
        self.settings = QSettings("SavSoft", "Crimea Radiometer")

        self.central_widget = QWidget(self, flags=Qt.WindowFlags())
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = backend.NavigationToolbar(self.canvas, self)
        self.plot_frame = QFrame(self.central_widget)
        self.vertical_layout_plot = QVBoxLayout(self.plot_frame)

        self.tab_settings = QWidget()

        self.group_settings_angles = QGroupBox(self.tab_settings)
        self.spin_bb_angle = QDoubleSpinBox(self.group_settings_angles)
        self.label_bb_angle = QLabel(self.group_settings_angles)
        self.spin_max_angle = QDoubleSpinBox(self.group_settings_angles)
        self.label_max_angle = QLabel(self.group_settings_angles)
        self.spin_min_angle = QDoubleSpinBox(self.group_settings_angles)
        self.label_min_angle = QLabel(self.group_settings_angles)
        self.spin_min_angle_alt = QDoubleSpinBox(self.group_settings_angles)
        self.label_min_angle_alt = QLabel(self.group_settings_angles)
        self.grid_layout_settings_angles = QGridLayout(self.group_settings_angles)

        self.group_settings_measurement = QGroupBox(self.tab_settings)
        self.spin_measurement_delay = QDoubleSpinBox(self.group_settings_measurement)
        self.label_measurement_delay = QLabel(self.group_settings_measurement)
        self.spin_channels = QSpinBox(self.group_settings_measurement)
        self.label_channels = QLabel(self.group_settings_measurement)
        self.grid_layout_settings_measurement = QGridLayout(self.group_settings_measurement)

        self.group_settings_motor = QGroupBox(self.tab_settings)
        self.button_move_360degrees_left = QPushButton(self.group_settings_motor)
        self.button_move_360degrees_right = QPushButton(self.group_settings_motor)
        self.button_move_90degrees = QPushButton(self.group_settings_motor)
        self.spin_settings_gear_2 = QSpinBox(self.group_settings_motor)
        self.label_settings_gear_2 = QLabel(self.group_settings_motor)
        self.spin_settings_gear_1 = QSpinBox(self.group_settings_motor)
        self.label_settings_gear_1 = QLabel(self.group_settings_motor)
        self.label_settings_speed_unit = QLabel(self.group_settings_motor)
        self.spin_settings_speed = QSpinBox(self.group_settings_motor)
        self.label_settings_speed = QLabel(self.group_settings_motor)
        self.spin_step_fraction = SpinListBox(self.group_settings_motor, ['1', '½', '¼', '⅟₁₆'])
        self.label_step_fraction = QLabel(self.group_settings_motor)
        self.grid_layout_settings_motor = QGridLayout(self.group_settings_motor)

        self.grid_layout_settings = QGridLayout(self.tab_settings)

        self.tab_main = QWidget()
        self.button_go = QPushButton(self.tab_main)
        self.button_power = QPushButton(self.tab_main)
        self.horizontal_layout_main = QHBoxLayout()

        self.group_schedule = QGroupBox(self.tab_main)
        self.button_schedule_action_down = QPushButton(self.group_schedule)
        self.button_schedule_action_up = QPushButton(self.group_schedule)
        self.button_schedule_action_remove = QPushButton(self.group_schedule)
        self.button_schedule_action_add = QPushButton(self.group_schedule)
        self.table_schedule = QTableWidget(self.group_schedule)
        self.grid_layout_schedule = QGridLayout(self.group_schedule)

        self.group_weather_state = QGroupBox(self.tab_main)
        self.label_weather_solar_radiation_value = QLabel(self.group_weather_state)
        self.label_weather_solar_radiation = QLabel(self.group_weather_state)
        self.label_weather_rain_rate_value = QLabel(self.group_weather_state)
        self.label_weather_rain_rate = QLabel(self.group_weather_state)
        self.label_weather_wind_direction_value = QLabel(self.group_weather_state)
        self.label_weather_wind_direction = QLabel(self.group_weather_state)
        self.label_weather_wind_speed_value = QLabel(self.group_weather_state)
        self.label_weather_wind_speed = QLabel(self.group_weather_state)
        self.label_weather_humidity_value = QLabel(self.group_weather_state)
        self.label_weather_humidity = QLabel(self.group_weather_state)
        self.label_weather_temperature_value = QLabel(self.group_weather_state)
        self.label_weather_temperature = QLabel(self.group_weather_state)
        self.grid_layout_weather_state = QGridLayout(self.group_weather_state)
        self.grid_layout_tab_main = QGridLayout(self.tab_main)

        self.tab_widget = QTabWidget(self.central_widget)
        self.gridLayout = QGridLayout(self.central_widget)

        self.resuming = self.get_config_value('common', 'power', False, bool)

        self.setup_ui(self)
        self.timer = QTimer()
        self.pd = QProgressDialog()
        self.pd.setCancelButton(None)
        self.pd.setWindowTitle(self.windowTitle())
        self.pd.setWindowModality(Qt.WindowModal)
        self.pd.setWindowIcon(self.windowIcon())
        self.pd.closeEvent = lambda e: e.ignore()
        self.pd.keyPressEvent = lambda e: e.ignore()
        self.pd.reset()
        # current schedule table row being measured
        self._current_row: Union[None, int] = None
        self._init_angle = 0
        # prevent config from being re-written while loading
        self._loading = True
        # config
        self.load_config()
        # backend
        self.plot = backend.Plot(serial_device='/dev/ttyS0',
                                 microstepping_mode=MicrosteppingMode(index=self.spin_step_fraction.value()),
                                 speed=self.spin_settings_speed.value(),
                                 ratio=self.spin_settings_gear_1.value() / self.spin_settings_gear_2.value(),
                                 measurement_delay=self.spin_measurement_delay.value(),
                                 init_angle=self._init_angle,
                                 figure=self.figure,
                                 adc_channels=list(range(self.spin_channels.value())),
                                 output_folder=self.get_config_value('settings', 'output folder',
                                                                     os.path.join(os.path.curdir, 'data'), str),
                                 results_file_prefix=time.strftime("%Y%m%d%H%M%S"))
        self.plot.start()
        self.load_plot_config()
        # common
        self.tab_widget.currentChanged.connect(self.tab_widget_changed)
        # tab 1
        self.button_schedule_action_add.clicked.connect(self.button_schedule_action_add_clicked)
        self.button_schedule_action_remove.clicked.connect(self.button_schedule_action_remove_clicked)
        self.button_schedule_action_up.clicked.connect(self.button_schedule_action_up_clicked)
        self.button_schedule_action_down.clicked.connect(self.button_schedule_action_down_clicked)
        self.button_power.toggled.connect(self.button_power_toggled)
        self.button_power_shortcut = QShortcut(QKeySequence("Shift+Space"), self)
        self.button_power_shortcut.activated.connect(self.button_power.click)
        self.button_go.toggled.connect(self.button_go_toggled)
        self.button_go_shortcut = QShortcut(QKeySequence("Space"), self)
        self.button_go_shortcut.activated.connect(self.button_go.click)
        # tab 2
        self.spin_step_fraction.valueChanged.connect(self.step_fraction_changed)
        self.spin_settings_speed.valueChanged.connect(self.spin_settings_speed_changed)
        self.spin_settings_gear_1.valueChanged.connect(self.spin_settings_gear_1_changed)
        self.spin_settings_gear_2.valueChanged.connect(self.spin_settings_gear_2_changed)
        self.button_move_90degrees.clicked.connect(self.button_move_90degrees_clicked)
        self.button_move_360degrees_right.clicked.connect(self.button_move_360degrees_right_clicked)
        self.button_move_360degrees_left.clicked.connect(self.button_move_360degrees_left_clicked)
        self.spin_channels.valueChanged.connect(self.spin_channels_changed)
        self.spin_measurement_delay.valueChanged.connect(self.spin_measurement_delay_changed)
        self.spin_bb_angle.valueChanged.connect(self.spin_bb_angle_changed)
        self.spin_max_angle.valueChanged.connect(self.spin_max_angle_changed)
        self.spin_min_angle.valueChanged.connect(self.spin_min_angle_changed)
        self.spin_min_angle_alt.valueChanged.connect(self.spin_min_angle_alt_changed)
        # dirty hack: the event doesn't work directly for subplots
        self.canvas.mpl_connect('button_press_event', self.plot.on_click)
        # whatever is written in the design file, “Go” button should be disabled initially
        self.button_go.setDisabled(True)
        #
        self.last_loop_data = {}

    def setup_ui(self, main_window):
        main_window.resize(484, 441)
        icon = QIcon()
        icon.addPixmap(QPixmap(os.path.join(os.path.split(__file__)[0], 'crimea-eng-circle.svg')),
                       QIcon.Normal, QIcon.Off)
        main_window.setWindowIcon(icon)
        self.gridLayout.setContentsMargins(9, 9, 9, 9)
        self.gridLayout.setSpacing(6)

        self.group_weather_state.setFlat(True)
        _value_label_interaction_flags = (Qt.LinksAccessibleByKeyboard
                                          | Qt.LinksAccessibleByMouse
                                          | Qt.TextBrowserInteraction
                                          | Qt.TextSelectableByKeyboard
                                          | Qt.TextSelectableByMouse)
        self.grid_layout_weather_state.addWidget(self.label_weather_temperature, 0, 0)
        self.label_weather_temperature_value.setTextInteractionFlags(_value_label_interaction_flags)
        self.grid_layout_weather_state.addWidget(self.label_weather_temperature_value, 0, 1)
        self.grid_layout_weather_state.addWidget(self.label_weather_humidity, 1, 0)
        self.label_weather_humidity_value.setTextInteractionFlags(_value_label_interaction_flags)
        self.grid_layout_weather_state.addWidget(self.label_weather_humidity_value, 1, 1)
        self.grid_layout_weather_state.addWidget(self.label_weather_wind_speed, 2, 0)
        self.label_weather_wind_speed_value.setTextInteractionFlags(_value_label_interaction_flags)
        self.grid_layout_weather_state.addWidget(self.label_weather_wind_speed_value, 2, 1)

        self.grid_layout_weather_state.addWidget(self.label_weather_wind_direction, 3, 0)
        self.label_weather_wind_direction_value.setTextInteractionFlags(_value_label_interaction_flags)
        self.grid_layout_weather_state.addWidget(self.label_weather_wind_direction_value, 3, 1)

        self.grid_layout_weather_state.addWidget(self.label_weather_rain_rate, 4, 0)
        self.label_weather_rain_rate_value.setTextInteractionFlags(_value_label_interaction_flags)
        self.grid_layout_weather_state.addWidget(self.label_weather_rain_rate_value, 4, 1)

        self.grid_layout_weather_state.addWidget(self.label_weather_solar_radiation, 5, 0)
        self.label_weather_solar_radiation_value.setTextInteractionFlags(_value_label_interaction_flags)
        self.grid_layout_weather_state.addWidget(self.label_weather_solar_radiation_value, 5, 1)

        self.grid_layout_tab_main.addWidget(self.group_weather_state, 0, 0)

        self.group_schedule.setFlat(True)
        self.table_schedule.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_schedule.setProperty("showDropIndicator", False)
        self.table_schedule.setDragDropOverwriteMode(False)
        self.table_schedule.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_schedule.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.table_schedule.setColumnCount(3)
        self.table_schedule.setRowCount(0)
        self.table_schedule.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
        for col in range(self.table_schedule.columnCount()):
            item = QTableWidgetItem()
            item.setTextAlignment(Qt.AlignCenter)
            self.table_schedule.setHorizontalHeaderItem(col, item)
        self.grid_layout_schedule.addWidget(self.table_schedule, 0, 0, 5, 1)
        self.grid_layout_schedule.addWidget(self.button_schedule_action_add, 0, 1)
        self.grid_layout_schedule.addWidget(self.button_schedule_action_remove, 1, 1)
        self.grid_layout_schedule.addWidget(self.button_schedule_action_up, 2, 1)
        self.grid_layout_schedule.addWidget(self.button_schedule_action_down, 3, 1)
        self.grid_layout_schedule.setColumnStretch(0, 1)
        self.grid_layout_tab_main.addWidget(self.group_schedule, 1, 0)

        self.grid_layout_tab_main.setRowStretch(1, 1)

        spacer_item = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.horizontal_layout_main.addItem(spacer_item)
        self.button_power.setCheckable(True)
        self.horizontal_layout_main.addWidget(self.button_power)
        spacer_item1 = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.horizontal_layout_main.addItem(spacer_item1)
        self.button_go.setCheckable(True)
        self.horizontal_layout_main.addWidget(self.button_go)
        spacer_item2 = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.horizontal_layout_main.addItem(spacer_item2)
        self.grid_layout_tab_main.addLayout(self.horizontal_layout_main, 2, 0)

        self.tab_widget.addTab(self.tab_main, "")

        line = 0
        self.grid_layout_settings_motor.addWidget(self.label_step_fraction, line, 0)
        self.spin_step_fraction.setWrapping(True)
        self.grid_layout_settings_motor.addWidget(self.spin_step_fraction, line, 1)
        line += 1
        self.grid_layout_settings_motor.addWidget(self.label_settings_speed, line, 0)
        self.spin_settings_speed.setMaximum(10000)
        self.grid_layout_settings_motor.addWidget(self.spin_settings_speed, line, 1)
        self.grid_layout_settings_motor.addWidget(self.label_settings_speed_unit, line, 2)
        line += 1
        self.grid_layout_settings_motor.addWidget(self.label_settings_gear_1, line, 0)
        self.spin_settings_gear_1.setRange(1, 200)
        self.grid_layout_settings_motor.addWidget(self.spin_settings_gear_1, line, 1)
        line += 1
        self.grid_layout_settings_motor.addWidget(self.label_settings_gear_2, line, 0)
        self.spin_settings_gear_2.setRange(1, 200)
        self.grid_layout_settings_motor.addWidget(self.spin_settings_gear_2, line, 1)
        line += 1
        self.grid_layout_settings_motor.addWidget(self.button_move_90degrees, line, 0, 1, 3)
        line += 1
        self.grid_layout_settings_motor.addWidget(self.button_move_360degrees_right, line, 0, 1, 3)
        line += 1
        self.grid_layout_settings_motor.addWidget(self.button_move_360degrees_left, line, 0, 1, 3)
        self.grid_layout_settings_motor.setColumnStretch(0, 1)
        self.grid_layout_settings.addWidget(self.group_settings_motor, 0, 0)

        self.grid_layout_settings_measurement.addWidget(self.label_channels, 2, 0)
        self.spin_channels.setMinimum(1)
        self.spin_channels.setMaximum(8)
        self.grid_layout_settings_measurement.addWidget(self.spin_channels, 2, 1)

        self.grid_layout_settings_measurement.addWidget(self.label_measurement_delay, 3, 0)
        self.spin_measurement_delay.setRange(0, 86400)
        self.spin_measurement_delay.setDecimals(1)
        self.spin_measurement_delay.setSingleStep(1)
        self.grid_layout_settings_measurement.addWidget(self.spin_measurement_delay, 3, 1)
        self.grid_layout_settings_measurement.setColumnStretch(0, 1)
        self.grid_layout_settings.addWidget(self.group_settings_measurement, 1, 0)

        self.grid_layout_settings_angles.addWidget(self.label_bb_angle, 0, 0)
        self.spin_bb_angle.setRange(-180, 180)
        self.spin_bb_angle.setDecimals(1)
        self.spin_bb_angle.setSuffix('°')
        self.spin_bb_angle.setSingleStep(1)
        self.grid_layout_settings_angles.addWidget(self.spin_bb_angle, 0, 1)

        self.grid_layout_settings_angles.addWidget(self.label_max_angle, 1, 0)
        self.spin_max_angle.setRange(-180, 180)
        self.spin_max_angle.setDecimals(1)
        self.spin_max_angle.setSuffix('°')
        self.spin_max_angle.setSingleStep(1)
        self.grid_layout_settings_angles.addWidget(self.spin_max_angle, 1, 1)

        self.grid_layout_settings_angles.addWidget(self.label_min_angle, 2, 0)
        self.spin_min_angle.setRange(-180, 180)
        self.spin_min_angle.setDecimals(1)
        self.spin_min_angle.setSuffix('°')
        self.spin_min_angle.setSingleStep(1)
        self.grid_layout_settings_angles.addWidget(self.spin_min_angle, 2, 1)

        self.grid_layout_settings_angles.addWidget(self.label_min_angle_alt, 3, 0)
        self.spin_min_angle_alt.setRange(-180, 180)
        self.spin_min_angle_alt.setDecimals(1)
        self.spin_min_angle_alt.setSuffix('°')
        self.spin_min_angle_alt.setSingleStep(1)
        self.grid_layout_settings_angles.addWidget(self.spin_min_angle_alt, 3, 1)

        self.grid_layout_settings_angles.setColumnStretch(0, 1)
        self.grid_layout_settings.addWidget(self.group_settings_angles, 2, 0)

        self.tab_widget.addTab(self.tab_settings, "")

        self.gridLayout.addWidget(self.tab_widget, 0, 1)

        self.figure.tight_layout()
        self.vertical_layout_plot.addWidget(self.toolbar)
        self.vertical_layout_plot.addWidget(self.canvas)
        self.gridLayout.addWidget(self.plot_frame, 0, 0)
        self.gridLayout.setColumnStretch(0, 1)

        main_window.setCentralWidget(self.central_widget)

        self.retranslate_ui(main_window)
        self.tab_widget.setCurrentIndex(0)
        main_window.adjustSize()
        QMetaObject.connectSlotsByName(main_window)

    def retranslate_ui(self, main_window):
        _translate = QCoreApplication.translate
        main_window.setWindowTitle(_translate("MainWindow", "Crimea"))
        self.group_weather_state.setTitle(_translate("MainWindow", "Current Weather"))
        self.label_weather_temperature.setText(_translate("MainWindow", "Temperature [°C]") + ':')
        self.label_weather_humidity.setText(_translate("MainWindow", "Humidity [%]") + ':')
        self.label_weather_wind_speed.setText(_translate("MainWindow", "Wind Speed") + ':')
        self.label_weather_wind_direction.setText(_translate("MainWindow", "Wind Direction [°]") + ':')
        self.label_weather_rain_rate.setText(_translate("MainWindow", "Rain Rate") + ':')
        self.label_weather_solar_radiation.setText(_translate("MainWindow", "Solar Radiation") + ':')
        self.group_schedule.setTitle(_translate("MainWindow", "Schedule"))
        item = self.table_schedule.horizontalHeaderItem(0)
        item.setText(_translate("MainWindow", "On"))
        item = self.table_schedule.horizontalHeaderItem(1)
        item.setText(_translate("MainWindow", "Angle h"))
        item = self.table_schedule.horizontalHeaderItem(2)
        item.setText(_translate("MainWindow", "Delay"))
        self.button_schedule_action_add.setText(_translate("MainWindow", "+"))
        self.button_schedule_action_remove.setText(_translate("MainWindow", "−"))
        self.button_schedule_action_up.setText(_translate("MainWindow", "↑"))
        self.button_schedule_action_down.setText(_translate("MainWindow", "↓"))
        self.button_power.setText(_translate("MainWindow", "Power ON"))
        self.button_go.setText(_translate("MainWindow", "Go"))
        self.tab_widget.setTabText(self.tab_widget.indexOf(self.tab_main), _translate("MainWindow", "Main"))
        self.group_settings_motor.setTitle(_translate("MainWindow", "Motor"))
        self.label_step_fraction.setText(_translate("MainWindow", "Step Fraction") + ':')
        self.label_settings_speed.setText(_translate("MainWindow", "Motor Speed") + ':')
        self.label_settings_speed_unit.setText(_translate("MainWindow", "°/s"))
        self.label_settings_gear_1.setText(_translate("MainWindow", "Gear 1 Size") + ':')
        self.label_settings_gear_2.setText(_translate("MainWindow", "Gear 2 Size") + ':')
        self.button_move_90degrees.setText(_translate("MainWindow", "Move 90° counter-clockwise"))
        self.button_move_360degrees_right.setText(_translate("MainWindow", "Move 360° counter-clockwise"))
        self.button_move_360degrees_left.setText(_translate("MainWindow", "Move 360° clockwise"))
        self.group_settings_measurement.setTitle(_translate("MainWindow", "Measurement"))
        self.label_channels.setText(_translate("MainWindow", "Number of ADC Channels") + ':')
        self.label_measurement_delay.setText(_translate("MainWindow", "Delay Before Measuring") + ':')
        self.spin_measurement_delay.setSuffix(_translate("MainWindow", ' s'))
        self.group_settings_angles.setTitle(_translate("MainWindow", "Angles"))
        self.label_bb_angle.setText(_translate("MainWindow", "Black Body Position") + ':')
        self.label_max_angle.setText(_translate("MainWindow", "Zenith Position") + ':')
        self.label_min_angle.setText(_translate("MainWindow", "Horizon Position") + ':')
        self.label_min_angle_alt.setText(_translate("MainWindow", "Horizon Position (alt)") + ':')

        self.tab_widget.setTabText(self.tab_widget.indexOf(self.tab_settings), _translate("MainWindow", "Settings"))

    def closeEvent(self, event):
        """ senseless joke in the loop """
        close = QMessageBox.No
        while close == QMessageBox.No:
            close = QMessageBox()
            close.setText("Are you sure?")
            close.setIcon(QMessageBox.Question)
            close.setWindowIcon(self.windowIcon())
            close.setWindowTitle(self.windowTitle())
            close.setStandardButtons(QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            close = close.exec()

            if close == QMessageBox.Yes:
                self.save_plot_config()
                self.set_config_value('common', 'power', False)
                self.table_schedule_changed(None)
                self.settings.setValue("windowGeometry", self.saveGeometry())
                self.settings.setValue("windowState", self.saveState())
                self.settings.sync()
                self.plot.set_running(False)
                self.plot.close()
                self.plot.join()
                event.accept()
            elif close == QMessageBox.Cancel:
                event.ignore()
        return

    def load_config(self):
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
        self.table_schedule_row_activated(0)
        # tab 2
        self.spin_step_fraction.setValue(self.get_config_value('motor', 'step fraction', 3, int))
        self.spin_settings_speed.setValue(self.get_config_value('motor', 'speed', 42, int))
        self.spin_settings_gear_1.setValue(self.get_config_value('motor', 'gear 1 size', 100, int))
        self.spin_settings_gear_2.setValue(self.get_config_value('motor', 'gear 2 size', 98, int))
        self.spin_measurement_delay.setValue(self.get_config_value('settings', 'delay before measuring', 8, float))
        self.spin_bb_angle.setValue(self.get_config_value('settings', 'black body position', 0, float))
        self.spin_max_angle.setValue(self.get_config_value('settings', 'zenith position', 90, float))
        self.spin_min_angle.setValue(self.get_config_value('settings', 'horizon position', 20, float))
        self.spin_min_angle_alt.setValue(self.get_config_value('settings', 'horizon position alt', 30, float))
        self.spin_channels.setValue(self.get_config_value('settings', 'number of channels', 1, int))
        self._loading = False
        return

    def load_plot_config(self):
        self._loading = True
        check_states = [to_bool(b) for b in self.get_config_value('settings', 'voltage channels', '', str).split()]
        self.plot.set_plot_lines_visibility(check_states)
        check_states = [to_bool(b) for b in self.get_config_value('settings', 'absorption channels', '', str).split()]
        self.plot.set_τ_plot_lines_visibility(check_states)
        props: List[Dict[str, Union[str, float, None]]] = self.plot.get_plot_lines_styles()
        for index, p in enumerate(props):
            for key, value in p.items():
                if 'color' in key:
                    p[key] = self.get_config_value('settings', f'voltage line {index} {key}', value,
                                                   Union[str, Tuple[float, ...]])
                else:
                    p[key] = self.get_config_value('settings', f'voltage line {index} {key}', value, type(value))
        self.plot.set_plot_lines_styles(props)
        props: List[Dict[str, Union[str, float, None]]] = self.plot.get_τ_plot_lines_styles()
        for index, p in enumerate(props):
            for key, value in p.items():
                if 'color' in key:
                    p[key] = self.get_config_value('settings', f'absorption line {index} {key}', value,
                                                   Union[str, Tuple[float, ...]])
                else:
                    p[key] = self.get_config_value('settings', f'absorption line {index} {key}', value, type(value))
        self.plot.set_τ_plot_lines_styles(props)

        props: Dict[str, float] = self.plot.get_subplotpars()
        for key, value in props.items():
            props[key] = self.get_config_value('subplots', key, value, float)
        self.plot.set_subplotpars(props)

        self._loading = False
        self.button_power_toggled(self.resuming)

    def save_plot_config(self):
        self.set_config_value('settings', 'voltage channels',
                              stringify_list(self.plot.get_plot_lines_visibility()))
        self.set_config_value('settings', 'absorption channels',
                              stringify_list(self.plot.get_τ_plot_lines_visibility()))
        props: List[Dict[str, Union[str, float, None]]] = self.plot.get_plot_lines_styles()
        for index, p in enumerate(props):
            for key, value in p.items():
                self.set_config_value('settings', f'voltage line {index} {key}', value)
        props: List[Dict[str, Union[str, float, None]]] = self.plot.get_τ_plot_lines_styles()
        for index, p in enumerate(props):
            for key, value in p.items():
                self.set_config_value('settings', f'absorption line {index} {key}', value)

        props: Dict[str, float] = self.plot.get_subplotpars()
        for key, value in props.items():
            self.set_config_value('subplots', key, value)

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

    def set_config_value(self, section, key, value):
        if self._loading:
            return
        self.settings.beginGroup(section)
        # print('set', section, key, value, type(value))
        if isinstance(value, tuple):
            self.settings.setValue(key, ' '.join(map(str, value)))
        else:
            self.settings.setValue(key, value)
        self.settings.endGroup()

    def stringify_table(self):
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

    def tab_widget_changed(self, index):
        self.set_config_value('common', 'current tab', index)
        return

    def button_schedule_action_add_clicked(self):
        self.add_table_row(self.table_schedule.currentRow() + 1)
        return

    def add_table_row(self, row_position=None, values=None):
        if row_position is None:
            row_position = self.table_schedule.rowCount()
        self.table_schedule.insertRow(row_position)

        item = QDoubleSpinBox()
        item.setRange(-180, 180)
        item.setDecimals(1)
        item.setSuffix('°')
        item.setSingleStep(1)
        item.valueChanged.connect(self.table_schedule_changed)
        if values and (isinstance(values, tuple) or isinstance(values, list)) and len(values) > 1:
            item.setValue(values[1])
        elif row_position > 0:
            item.setValue(self.table_schedule.cellWidget(row_position - 1, 1).value() + item.singleStep() * 10)
        self.table_schedule.setCellWidget(row_position, 1, item)

        item = QDoubleSpinBox()
        item.setRange(1, 86400)
        item.setDecimals(1)
        item.setSuffix(' s')
        item.setSingleStep(1)
        item.valueChanged.connect(self.table_schedule_changed)
        if values and (isinstance(values, tuple) or isinstance(values, list)) and len(values) > 2:
            item.setValue(values[2])
        elif row_position > 0:
            item.setValue(self.table_schedule.cellWidget(row_position - 1, 2).value())
        self.table_schedule.setCellWidget(row_position, 2, item)

        item = QCheckBox()
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
        item.stateChanged.connect(self.table_schedule_row_activated)
        if values and (isinstance(values, tuple) or isinstance(values, list)) and len(values) > 0:
            item.setCheckState(Qt.Checked if values[0] else Qt.Unchecked)
        else:
            item.setCheckState(Qt.Checked)

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

    def button_schedule_action_remove_clicked(self):
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

    def table_schedule_row_activated(self, new_state):
        self.table_schedule_changed(None)
        for r in range(self.table_schedule.rowCount()):
            w = self.table_schedule.cellWidget(r, 0)
            if w is not None:
                w2 = w.childAt(w.childrenRect().center())
                if w2 is not None:
                    w2ch = w2.checkState()
                    if w2ch == new_state:
                        for c in range(1, self.table_schedule.columnCount()):
                            w1 = self.table_schedule.cellWidget(r, c)
                            if w1 is not None:
                                w1.setEnabled(w2ch)
        something_enabled = bool(self.enabled_rows())
        self.button_go.setEnabled(something_enabled and self.button_power.isChecked())
        if not something_enabled:
            self.button_go.setChecked(False)
        return

    def table_schedule_changed(self, _new_value):
        st, sl = self.stringify_table()
        self.set_config_value('schedule', 'table', st)
        self.set_config_value('schedule', 'skip lines', sl)

    @staticmethod
    def move_row_down(table, row):
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
    def move_row_up(table, row):
        if row > 0:
            table.setRowHidden(row, True)
            table.insertRow(row - 1)
            for c in range(table.columnCount()):
                table.setItem(row - 1, c, table.takeItem(row + 1, c))
                table.setCellWidget(row - 1, c, table.cellWidget(row + 1, c))
            table.removeRow(row + 1)
            return row - 1
        return row

    def button_schedule_action_up_clicked(self):
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

    def button_schedule_action_down_clicked(self):
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

    def highlight_current_row(self, enabled=True):
        for row in range(0, self.table_schedule.rowCount()):
            if enabled and row != self._current_row:
                cw = self.table_schedule.cellWidget(row, 0)
                if cw:
                    cw.setStyleSheet("background-color: rgba(0,0,0,0)")
        if enabled and self._current_row is not None:
            cw = self.table_schedule.cellWidget(self._current_row, 0)
            if cw:
                cw.setStyleSheet("background-color: green")
        return

    def enabled_rows(self):
        rows = []
        for r in range(self.table_schedule.rowCount()):
            w = self.table_schedule.cellWidget(r, 0)
            duration = self.table_schedule.cellWidget(r, 2).value()
            if duration > 0.0 and w is not None:
                w2 = w.findChild(QCheckBox, '', Qt.FindDirectChildrenOnly)
                if w2 is not None and w2.checkState():
                    rows += [r]
        return rows

    def next_enabled_row(self, row):
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

    def fill_weather(self, weather):
        if weather is not None:
            self.label_weather_temperature_value.setNum(np.round(weather['OutsideTemp'], decimals=1))
            self.label_weather_humidity_value.setNum(weather['OutsideHum'])
            self.label_weather_wind_speed_value.setNum(weather['WindSpeed'])
            self.label_weather_wind_direction_value.setNum(weather['WindDir'])
            self.label_weather_rain_rate_value.setNum(weather['RainRate'])
            self.label_weather_solar_radiation_value.setNum(weather['SolarRad'])

    def calculate_bb_τ(self, *, callback, min_angle: float, max_angle: float, bb_angle: float, precision: float = 5.):
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
                    print('τ = ln(({d0} - {d1})/({d0} - {d2})) / (1/cos({h2}°) - 1/cos({h1}°))'.format(
                        d0=d0,
                        d1=d1,
                        d2=d2,
                        h1=90 - closest_to_min_angle,
                        h2=90 - closest_to_max_angle))
                else:
                    if not np.isnan(τ):
                        callback(ch, τ)
                finally:
                    np.seterr(invalid='warn', divide='warn')

    def calculate_leastsq_τ(self, ch: int) -> (float, float):
        h: np.ndarray = np.array(list(self.last_loop_data))
        d: np.ndarray = np.array([self.last_loop_data[a][ch] for a in self.last_loop_data])
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

    def calculate_magic_angles_τ(self, ch: int) -> float:
        h: np.ndarray = np.array(list(self.last_loop_data))
        d: np.ndarray = np.array([self.last_loop_data[a][ch] for a in self.last_loop_data])
        good: np.ndarray = (h >= 15)
        h = h[good]
        d = d[good]
        if not np.any(good):
            return np.nan
        min_diff: float = 1.
        best_angles: Tuple[int, int] = tuple()
        k = np.argmin(np.abs(h - 90.))
        z = np.deg2rad(h[k])
        for i in range(h.size):
            for j in range(h.size):
                if i == j or i == k or j == k:
                    continue
                diff = np.abs(1. / np.sin(z) - 2. / np.sin(np.deg2rad(h[j])) + 1. / np.sin(np.deg2rad(h[i])))
                if min_diff > diff:
                    best_angles = (i, j)
                    min_diff = diff
        if min_diff > 0.00399:
            return np.nan
        i, j = best_angles
        np.seterr(invalid='raise', divide='raise')
        try:
            if d[i] < d[j] < d[k] or d[i] > d[j] > d[k]:
                τ = np.log((d[j] - d[k]) / (d[i] - d[j])) / \
                    (1. / np.sin(np.deg2rad(h[i])) - 1. / np.sin(np.deg2rad(h[j])))
            else:
                τ = np.nan
        except FloatingPointError:
            print('τ = ln(({d0} - {d1})/({d2} - {d0})) / (1/cos({h2}°) - 1/cos({h1}°))'.format(
                d0=d[j],
                d1=d[k],
                d2=d[i],
                h1=90 - h[j],
                h2=90 - h[i]))
            τ = np.nan
        finally:
            np.seterr(invalid='warn', divide='warn')
        return τ

    def measure_next(self, ignore_home: bool = False):
        self.fill_weather(self.plot.last_weather())
        if self.plot.has_measured() or ignore_home:
            self.canvas.draw_idle()
            current_angle = self.table_schedule.cellWidget(self._current_row, 1).value()
            self.last_loop_data[current_angle] = self.plot.last_data()
            next_row = self.next_enabled_row(self._current_row)
            if next_row is None:
                return
            # print(ignore_home, next_row)
            if self._current_row >= next_row and not ignore_home:
                # calculate τ in different manners
                bb_angle = self.spin_bb_angle.value()
                max_angle = self.spin_max_angle.value()
                for min_angle, callback in [(self.spin_min_angle.value(), self.plot.add_τ),
                                            (self.spin_min_angle_alt.value(), self.plot.add_τ_alt)]:
                    self.calculate_bb_τ(callback=callback,
                                        min_angle=min_angle, max_angle=max_angle, bb_angle=bb_angle)
                for ch in range(len(self.last_loop_data[current_angle])):
                    _τ, _error = self.calculate_leastsq_τ(ch)
                    if not np.isnan(_error):
                        self.plot.add_τ_leastsq(ch, _τ)
                    _τ = self.calculate_magic_angles_τ(ch)
                    if not np.isnan(_τ):
                        self.plot.add_τ_magic_angles(ch, _τ)

                self.last_loop_data = {}
                self.canvas.draw_idle()

                self.pd.setMaximum(1000 * self.plot.time_to_move_home())
                self.pd.setLabelText('Wait till the motor comes home')
                self.pd.reset()
                try:
                    self.timer.timeout.disconnect()
                except TypeError:
                    pass
                self.timer.timeout.connect(lambda: self.next_pd_tick(
                    fallback=lambda: self.measure_next(ignore_home=True)))
                self.timer.setSingleShot(True)
                self.timer.start(100)  # don't use QTimer.singleShot here to be able to stop the timer later!!
                # self.plot.enable_motor(True, new_thread=True)

                self.plot.move_home()
                self.plot.pack_data()
                self.plot.purge_obsolete_data(purge_all=True)

            if self.button_go.isChecked():
                angle = self.table_schedule.cellWidget(next_row, 1).value()
                duration = self.table_schedule.cellWidget(next_row, 2).value()
                self._current_row = next_row
                self.highlight_current_row()
                self.plot.measure(angle, duration)
                self.set_config_value('common', 'last angle', angle)
                try:
                    self.timer.timeout.disconnect()
                except TypeError:
                    pass
                self.timer.timeout.connect(self.measure_next)
                self.timer.setSingleShot(True)
                # don't use QTimer.singleShot here to be able to stop the timer later!!
                self.timer.start(self.plot.measurement_time(angle, duration) * 1000)
        else:
            try:
                self.timer.timeout.disconnect()
            except TypeError:
                pass
            self.timer.timeout.connect(self.measure_next)
            self.timer.setSingleShot(True)
            self.timer.start(100)  # don't use QTimer.singleShot here to be able to stop the timer later!!

    def button_go_toggled(self, new_value):
        if new_value and self.table_schedule.rowCount() > 0:
            if self._current_row is None:
                self._current_row = self.next_enabled_row(-1)
            self.highlight_current_row()
            angle = self.table_schedule.cellWidget(self._current_row, 1).value()
            duration = self.table_schedule.cellWidget(self._current_row, 2).value()
            self.plot.purge_obsolete_data(purge_all=True)
            self.plot.measure(angle, duration)
            self.set_config_value('common', 'last angle', angle)
            try:
                self.timer.timeout.disconnect()
            except TypeError:
                pass
            self.timer.timeout.connect(self.measure_next)
            self.timer.setSingleShot(True)
            # don't use QTimer.singleShot here to be able to stop the timer later!!
            self.timer.start(self.plot.measurement_time(angle, duration) * 1000)
        else:
            self.timer.stop()
            self.plot.set_running(False)
            self.highlight_current_row(False)
        self.set_config_value('common', 'running', new_value)
        self.resuming = False
        return

    def next_pd_tick(self, fallback=None):
        next_value = self.pd.value() + self.timer.interval()
        if next_value < self.pd.maximum():
            self.pd.setValue(next_value)
            try:
                self.timer.timeout.disconnect()
            except TypeError:
                pass
            if fallback is not None:
                self.timer.timeout.connect(lambda: self.next_pd_tick(fallback=fallback))
            else:
                self.timer.timeout.connect(self.next_pd_tick)
            self.timer.setSingleShot(True)
            self.timer.start(100)  # don't use QTimer.singleShot here to be able to stop the timer later!!
        else:
            self.pd.reset()
            if fallback is not None:
                fallback()

    def button_power_toggled(self, new_state):
        if not new_state:
            self.button_go.setChecked(False)
        self.button_power.setDisabled(True)
        if new_state:
            self.pd.setMaximum(1000 * (self.plot.time_to_move_home()))
            self.pd.setLabelText('Wait till the motor comes home')
            self.pd.reset()
            try:
                self.timer.timeout.disconnect()
            except TypeError:
                pass
            self.timer.timeout.connect(lambda: self.next_pd_tick(
                fallback=lambda: self.button_go.setEnabled(new_state) or self.button_go.setChecked(
                    new_state and self.resuming)
            ))
            self.timer.setSingleShot(True)
            self.timer.start(100)  # don't use QTimer.singleShot here to be able to stop the timer later!!
        self.plot.enable_motor(new_state, new_thread=new_state)
        self.button_power.setEnabled(True)
        self.set_config_value('common', 'power', new_state)
        return

    def step_fraction_changed(self, new_value):
        self.set_config_value('motor', 'step fraction', new_value)
        if hasattr(self, 'plot'):  # if already defined
            self.plot.set_microstepping_mode(MicrosteppingMode(index=new_value))
        return

    def spin_settings_speed_changed(self, new_value):
        self.set_config_value('motor', 'speed', new_value)
        if hasattr(self, 'plot'):  # if already defined
            self.plot.set_motor_speed(new_value)
        return

    def spin_settings_gear_1_changed(self, new_value):
        self.set_config_value('motor', 'gear 1 size', new_value)
        if hasattr(self, 'plot'):  # if already defined
            self.plot.set_gear_ratio(new_value / self.spin_settings_gear_2.value())
        return

    def spin_settings_gear_2_changed(self, new_value):
        self.set_config_value('motor', 'gear 2 size', new_value)
        if hasattr(self, 'plot'):  # if already defined
            self.plot.set_gear_ratio(self.spin_settings_gear_1.value() / new_value)
        return

    def button_move_90degrees_clicked(self):
        self.pd.setMaximum(1000 * self.plot.move_90degrees())
        self.pd.setLabelText('Wait till the motor turns 90 degrees')
        self.pd.reset()
        try:
            self.timer.timeout.disconnect()
        except TypeError:
            pass
        self.timer.timeout.connect(self.next_pd_tick)
        self.timer.setSingleShot(True)
        self.timer.start(100)  # don't use QTimer.singleShot here to be able to stop the timer later!!
        return

    def button_move_360degrees_right_clicked(self):
        self.pd.setMaximum(1000 * self.plot.move_360degrees_right())
        self.pd.setLabelText('Wait till the motor turns 360 degrees')
        self.pd.reset()
        try:
            self.timer.timeout.disconnect()
        except TypeError:
            pass
        self.timer.timeout.connect(self.next_pd_tick)
        self.timer.setSingleShot(True)
        self.timer.start(100)  # don't use QTimer.singleShot here to be able to stop the timer later!!
        return

    def button_move_360degrees_left_clicked(self):
        self.pd.setMaximum(1000 * self.plot.move_360degrees_left())
        self.pd.setLabelText('Wait till the motor turns 360 degrees')
        self.pd.reset()
        try:
            self.timer.timeout.disconnect()
        except TypeError:
            pass
        self.timer.timeout.connect(self.next_pd_tick)
        self.timer.setSingleShot(True)
        self.timer.start(100)  # don't use QTimer.singleShot here to be able to stop the timer later!!
        return

    def spin_channels_changed(self, new_value):
        self.set_config_value('settings', 'number of channels', new_value)
        if hasattr(self, 'plot'):
            self.figure.clf()
            self.plot.close()
            self.plot.join()
            self.plot = backend.Plot(serial_device='/dev/ttyS0',
                                     microstepping_mode=MicrosteppingMode(index=self.spin_step_fraction.value()),
                                     speed=self.spin_settings_speed.value(),
                                     measurement_delay=self.spin_measurement_delay.value(),
                                     init_angle=self._init_angle,
                                     figure=self.figure,
                                     adc_channels=list(range(self.spin_channels.value())),
                                     output_folder=self.get_config_value('settings', 'output folder',
                                                                         os.path.join(os.path.curdir, 'data'), str),
                                     results_file_prefix=time.strftime("%Y%m%d%H%M%S"))
            self.plot.start()
        return

    def spin_measurement_delay_changed(self, new_value):
        self.set_config_value('settings', 'delay before measuring', new_value)
        self.plot.set_measurement_delay(new_value)

    def spin_bb_angle_changed(self, new_value):
        self.set_config_value('settings', 'black body position', new_value)

    def spin_max_angle_changed(self, new_value):
        self.set_config_value('settings', 'zenith position', new_value)

    def spin_min_angle_changed(self, new_value):
        self.set_config_value('settings', 'horizon position', new_value)

    def spin_min_angle_alt_changed(self, new_value):
        self.set_config_value('settings', 'horizon position alt', new_value)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='Radiometer controller')
    ap.add_argument('--no-gui', help='run without graphical interface', action='store_true', default=False)
    args = ap.parse_args()

    # https://stackoverflow.com/a/7758075/8554611
    # Without holding a reference to our socket somewhere it gets garbage
    # collected when the function exits
    _lock_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
        _lock_socket.bind('\0' + __file__)
        if not args.no_gui:
            make_desktop_launcher()
            app = QApplication(sys.argv)
            window = App()
            window.show()
            app.exec_()
    except socket.error:
        print(f'{__file__} is already running')
