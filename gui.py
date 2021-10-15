# -*- coding: utf-8 -*-

import os
from typing import List

from PyQt5.QtCore import QCoreApplication, QSettings, QTimer, Qt
from PyQt5.QtGui import QIcon, QKeySequence, QPixmap
from PyQt5.QtWidgets import QAbstractItemView, QCheckBox, QDoubleSpinBox, QFormLayout, QFrame, QGridLayout, QGroupBox, \
    QHBoxLayout, QLabel, QMainWindow, QProgressDialog, QPushButton, QShortcut, QSizePolicy, QSpacerItem, QSpinBox, \
    QTabWidget, QTableWidget, QTableWidgetItem, QToolButton, QVBoxLayout, QWidget
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from navigation_toolbar import NavigationToolbar
from spin_list_box import SpinListBox


class GUI(QMainWindow):
    def __init__(self) -> None:
        super().__init__(flags=Qt.WindowFlags())
        self.settings: QSettings = QSettings("SavSoft", "Crimea Radiometer")

        self.central_widget: QWidget = QWidget(self, flags=Qt.WindowFlags())
        self.figure: Figure = Figure()
        self.canvas: FigureCanvas = FigureCanvas(self.figure)
        self.toolbar: NavigationToolbar = NavigationToolbar(self.canvas, self)
        self.plot_frame: QFrame = QFrame(self.central_widget)
        self.vertical_layout_plot: QVBoxLayout = QVBoxLayout(self.plot_frame)

        self.tab_settings: QWidget = QWidget()

        self.group_settings_angles: QGroupBox = QGroupBox(self.tab_settings)
        self.spin_bb_angle: QDoubleSpinBox = QDoubleSpinBox(self.group_settings_angles)
        self.spin_bb_angle_alt: QDoubleSpinBox = QDoubleSpinBox(self.group_settings_angles)
        self.spin_max_angle: QDoubleSpinBox = QDoubleSpinBox(self.group_settings_angles)
        self.spin_min_angle: QDoubleSpinBox = QDoubleSpinBox(self.group_settings_angles)
        self.spin_min_angle_alt: QDoubleSpinBox = QDoubleSpinBox(self.group_settings_angles)
        self.form_layout_settings_angles: QFormLayout = QFormLayout(self.group_settings_angles)

        self.group_settings_measurement: QGroupBox = QGroupBox(self.tab_settings)
        self.spin_measurement_delay: QDoubleSpinBox = QDoubleSpinBox(self.group_settings_measurement)
        self.label_measurement_delay: QLabel = QLabel(self.group_settings_measurement)
        self.spin_channels: QSpinBox = QSpinBox(self.group_settings_measurement)
        self.label_channels: QLabel = QLabel(self.group_settings_measurement)
        self.grid_layout_settings_measurement: QGridLayout = QGridLayout(self.group_settings_measurement)

        self.group_settings_motor: QGroupBox = QGroupBox(self.tab_settings)
        self.button_move_1step_left: QPushButton = QPushButton(self.group_settings_motor)
        self.button_move_1step_right: QPushButton = QPushButton(self.group_settings_motor)
        self.button_move_360degrees_left: QPushButton = QPushButton(self.group_settings_motor)
        self.button_move_360degrees_right: QPushButton = QPushButton(self.group_settings_motor)
        self.button_move_90degrees: QPushButton = QPushButton(self.group_settings_motor)
        self.button_move_home: QPushButton = QPushButton(self.group_settings_motor)
        self.spin_settings_gear_2: QSpinBox = QSpinBox(self.group_settings_motor)
        self.label_settings_gear_2: QLabel = QLabel(self.group_settings_motor)
        self.spin_settings_gear_1: QSpinBox = QSpinBox(self.group_settings_motor)
        self.label_settings_gear_1: QLabel = QLabel(self.group_settings_motor)
        self.label_settings_speed_unit: QLabel = QLabel(self.group_settings_motor)
        self.spin_settings_speed: QSpinBox = QSpinBox(self.group_settings_motor)
        self.label_settings_speed: QLabel = QLabel(self.group_settings_motor)
        self.spin_step_fraction: SpinListBox = SpinListBox(self.group_settings_motor, ['1', '½', '¼', '⅟₁₆'])
        self.label_step_fraction: QLabel = QLabel(self.group_settings_motor)
        self.grid_layout_settings_motor: QGridLayout = QGridLayout(self.group_settings_motor)

        self.vertical_layout_settings: QVBoxLayout = QVBoxLayout(self.tab_settings)

        self.tab_main: QWidget = QWidget()
        self.button_go: QPushButton = QPushButton(self.tab_main)
        self.button_power: QPushButton = QPushButton(self.tab_main)
        self.horizontal_layout_main: QHBoxLayout = QHBoxLayout()

        self.group_temperature: QGroupBox = QGroupBox(self.central_widget)
        self.grid_layout_temperature: QGridLayout = QGridLayout(self.group_temperature)
        self.labels_sensor: List[QLabel] = []
        self.label_temperature_label: QLabel = QLabel(self.group_temperature)
        self.labels_temperature_value: List[QLabel] = []
        self.label_state_label: QLabel = QLabel(self.group_temperature)
        self.checks_state_value: List[QCheckBox] = []
        self.label_setpoint_label: QLabel = QLabel(self.group_temperature)
        self.spins_setpoint_value: List[QSpinBox] = []

        self.check_auto_temperature_mode: QCheckBox = QCheckBox(self.group_temperature)

        self.group_schedule: QGroupBox = QGroupBox(self.tab_main)
        self.button_schedule_action_down: QToolButton = QToolButton(self.group_schedule)
        self.button_schedule_action_up: QToolButton = QToolButton(self.group_schedule)
        self.button_schedule_action_remove: QToolButton = QToolButton(self.group_schedule)
        self.button_schedule_action_add: QToolButton = QToolButton(self.group_schedule)
        self.table_schedule: QTableWidget = QTableWidget(self.group_schedule)
        self.grid_layout_schedule: QGridLayout = QGridLayout(self.group_schedule)

        self.group_weather_state: QGroupBox = QGroupBox(self.tab_main)
        self.label_weather_solar_radiation: QLabel = QLabel(self.group_weather_state)
        self.label_weather_rain_rate: QLabel = QLabel(self.group_weather_state)
        self.label_weather_wind_direction: QLabel = QLabel(self.group_weather_state)
        self.label_weather_wind_speed: QLabel = QLabel(self.group_weather_state)
        self.label_weather_humidity: QLabel = QLabel(self.group_weather_state)
        self.label_weather_temperature: QLabel = QLabel(self.group_weather_state)
        self.form_layout_weather_state: QFormLayout = QFormLayout(self.group_weather_state)
        self.grid_layout_tab_main: QGridLayout = QGridLayout(self.tab_main)

        self.tab_widget: QTabWidget = QTabWidget(self.central_widget)
        self.gridLayout: QGridLayout = QGridLayout(self.central_widget)

        self.button_power_shortcut: QShortcut = QShortcut(QKeySequence("Shift+Space"), self)
        self.button_go_shortcut: QShortcut = QShortcut(QKeySequence("Space"), self)

        self.setup_ui()

        self.timer: QTimer = QTimer()
        self.pd: QProgressDialog = QProgressDialog()
        self.pd.setCancelButton(None)
        self.pd.setWindowTitle(self.windowTitle())
        self.pd.setWindowModality(Qt.WindowModal)
        self.pd.setWindowIcon(self.windowIcon())
        self.pd.closeEvent = lambda e: e.ignore()
        self.pd.keyPressEvent = lambda e: e.ignore()
        self.pd.reset()

    def setup_ui(self) -> None:
        _translate = QCoreApplication.translate

        # “Go” button should be disabled initially
        self.button_go.setDisabled(True)

        icon: QIcon = QIcon()
        icon.addPixmap(QPixmap(os.path.join(os.path.split(__file__)[0], 'qaradag.svg')), QIcon.Normal, QIcon.Off)
        self.setWindowIcon(icon)

        self.group_weather_state.setFlat(True)
        _value_label_interaction_flags = (Qt.LinksAccessibleByKeyboard
                                          | Qt.LinksAccessibleByMouse
                                          | Qt.TextBrowserInteraction
                                          | Qt.TextSelectableByKeyboard
                                          | Qt.TextSelectableByMouse)
        self.label_weather_temperature.setTextInteractionFlags(_value_label_interaction_flags)
        self.label_weather_humidity.setTextInteractionFlags(_value_label_interaction_flags)
        self.label_weather_wind_speed.setTextInteractionFlags(_value_label_interaction_flags)
        self.label_weather_wind_direction.setTextInteractionFlags(_value_label_interaction_flags)
        self.label_weather_rain_rate.setTextInteractionFlags(_value_label_interaction_flags)
        self.label_weather_solar_radiation.setTextInteractionFlags(_value_label_interaction_flags)
        self.form_layout_weather_state.addRow(self.tr("Temperature [°C]") + ':', self.label_weather_temperature)
        self.form_layout_weather_state.addRow(self.tr("Humidity [%]") + ':', self.label_weather_humidity)
        self.form_layout_weather_state.addRow(self.tr("Wind Speed") + ':', self.label_weather_wind_speed)
        self.form_layout_weather_state.addRow(self.tr("Wind Direction [°]") + ':', self.label_weather_wind_direction)
        self.form_layout_weather_state.addRow(self.tr("Rain Rate") + ':', self.label_weather_rain_rate)
        self.form_layout_weather_state.addRow(self.tr("Solar Radiation") + ':', self.label_weather_solar_radiation)

        self.grid_layout_tab_main.addWidget(self.group_weather_state, 0, 0)

        line: int
        line = 0
        i: int
        for i in range(5):
            line = i + 1
            self.labels_sensor.append(QLabel(self.group_temperature))
            self.grid_layout_temperature.addWidget(self.labels_sensor[-1], line, 0, 1, 1)
            self.labels_temperature_value.append(QLabel(self.group_temperature))
            self.labels_temperature_value[-1].setTextInteractionFlags(_value_label_interaction_flags)
            self.grid_layout_temperature.addWidget(self.labels_temperature_value[-1], line, 1, 1, 1)
            self.checks_state_value.append(QCheckBox(self.group_temperature))
            self.checks_state_value[-1].toggled.connect(self.check_state_value_toggled)
            self.checks_state_value[-1].setEnabled(False)
            self.grid_layout_temperature.addWidget(self.checks_state_value[-1], line, 2, 1, 1, Qt.AlignHCenter)
            self.spins_setpoint_value.append(QSpinBox(self.group_temperature))
            self.spins_setpoint_value[-1].setMaximum(42)
            self.spins_setpoint_value[-1].blockSignals(True)
            self.spins_setpoint_value[-1].valueChanged.connect(self.spin_setpoint_value_changed)
            self.spins_setpoint_value[-1].blockSignals(False)
            self.grid_layout_temperature.addWidget(self.spins_setpoint_value[-1], line, 3, 1, 1, Qt.AlignHCenter)

        self.grid_layout_temperature.addWidget(self.label_temperature_label, 0, 1, 1, 1)
        self.grid_layout_temperature.addWidget(self.label_state_label, 0, 2, 1, 1, Qt.AlignHCenter)
        self.grid_layout_temperature.addWidget(self.label_setpoint_label, 0, 3, 1, 1, Qt.AlignHCenter)

        line += 1
        self.grid_layout_temperature.addWidget(self.check_auto_temperature_mode, line, 0, 1, 4)

        self.grid_layout_tab_main.addWidget(self.group_temperature, 1, 0)

        self.group_schedule.setFlat(True)
        self.table_schedule.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_schedule.setProperty('showDropIndicator', False)
        self.table_schedule.setDragDropOverwriteMode(False)
        self.table_schedule.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_schedule.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.table_schedule.setColumnCount(3)
        self.table_schedule.setRowCount(0)
        col: int
        for col in range(self.table_schedule.columnCount()):
            item: QTableWidgetItem = QTableWidgetItem()
            item.setTextAlignment(Qt.AlignCenter)
            self.table_schedule.setHorizontalHeaderItem(col, item)
        self.grid_layout_schedule.addWidget(self.table_schedule, 0, 0, 5, 1)
        self.grid_layout_schedule.addWidget(self.button_schedule_action_add, 0, 1)
        self.grid_layout_schedule.addWidget(self.button_schedule_action_remove, 1, 1)
        self.grid_layout_schedule.addWidget(self.button_schedule_action_up, 2, 1)
        self.grid_layout_schedule.addWidget(self.button_schedule_action_down, 3, 1)
        self.grid_layout_schedule.setColumnStretch(0, 1)
        self.grid_layout_tab_main.addWidget(self.group_schedule, 2, 0)

        self.grid_layout_tab_main.setRowStretch(2, 1)

        spacer_item: QSpacerItem = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.horizontal_layout_main.addItem(spacer_item)
        self.button_power.setCheckable(True)
        self.horizontal_layout_main.addWidget(self.button_power)
        spacer_item1: QSpacerItem = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.horizontal_layout_main.addItem(spacer_item1)
        self.button_go.setCheckable(True)
        self.horizontal_layout_main.addWidget(self.button_go)
        spacer_item2: QSpacerItem = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.horizontal_layout_main.addItem(spacer_item2)
        self.grid_layout_tab_main.addLayout(self.horizontal_layout_main, 3, 0)

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
        self.grid_layout_settings_motor.addWidget(self.button_move_home, line, 0, 1, 3)
        line += 1
        self.grid_layout_settings_motor.addWidget(self.button_move_90degrees, line, 0, 1, 3)
        line += 1
        self.grid_layout_settings_motor.addWidget(self.button_move_1step_right, line, 0, 1, 3)
        line += 1
        self.grid_layout_settings_motor.addWidget(self.button_move_1step_left, line, 0, 1, 3)
        line += 1
        self.grid_layout_settings_motor.addWidget(self.button_move_360degrees_right, line, 0, 1, 3)
        line += 1
        self.grid_layout_settings_motor.addWidget(self.button_move_360degrees_left, line, 0, 1, 3)
        self.grid_layout_settings_motor.setColumnStretch(0, 1)
        self.vertical_layout_settings.addWidget(self.group_settings_motor)

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
        self.vertical_layout_settings.addWidget(self.group_settings_measurement)

        self.spin_bb_angle.setRange(-180, 180)
        self.spin_bb_angle.setDecimals(1)
        self.spin_bb_angle.setSuffix('°')
        self.spin_bb_angle.setSingleStep(1)
        self.form_layout_settings_angles.addRow(self.tr('Black Body Position') + ':', self.spin_bb_angle)
        self.spin_bb_angle_alt.setRange(-180, 180)
        self.spin_bb_angle_alt.setDecimals(1)
        self.spin_bb_angle_alt.setSuffix('°')
        self.spin_bb_angle_alt.setSingleStep(1)
        self.form_layout_settings_angles.addRow(self.tr('Black Body Position (alt)') + ':', self.spin_bb_angle_alt)
        self.spin_max_angle.setRange(-180, 180)
        self.spin_max_angle.setDecimals(1)
        self.spin_max_angle.setSuffix('°')
        self.spin_max_angle.setSingleStep(1)
        self.form_layout_settings_angles.addRow(self.tr('Zenith Position') + ':', self.spin_max_angle)
        self.spin_min_angle.setRange(-180, 180)
        self.spin_min_angle.setDecimals(1)
        self.spin_min_angle.setSuffix('°')
        self.spin_min_angle.setSingleStep(1)
        self.form_layout_settings_angles.addRow(self.tr('Horizon Position') + ':', self.spin_min_angle)
        self.spin_min_angle_alt.setRange(-180, 180)
        self.spin_min_angle_alt.setDecimals(1)
        self.spin_min_angle_alt.setSuffix('°')
        self.spin_min_angle_alt.setSingleStep(1)
        self.form_layout_settings_angles.addRow(self.tr('Horizon Position (alt)') + ':', self.spin_min_angle_alt)

        self.vertical_layout_settings.addWidget(self.group_settings_angles)

        self.tab_widget.addTab(self.tab_settings, self.tr('Settings'))

        self.gridLayout.addWidget(self.tab_widget, 0, 1)

        self.figure.tight_layout()
        self.vertical_layout_plot.addWidget(self.toolbar)
        self.vertical_layout_plot.addWidget(self.canvas)
        self.gridLayout.addWidget(self.plot_frame, 0, 0)
        self.gridLayout.setColumnStretch(0, 1)

        self.setCentralWidget(self.central_widget)

        self.setWindowTitle(self.tr('Crimea Radiometer'))
        self.group_weather_state.setTitle(self.tr('Current Weather'))
        self.group_temperature.setTitle(self.tr('Temperature'))
        self.label_temperature_label.setText(self.tr('T [°C]'))
        self.label_state_label.setText(self.tr('State'))
        self.label_setpoint_label.setText(self.tr('SP [°C]'))
        i: int
        for i in range(len(self.labels_sensor)):
            self.labels_sensor[i].setText(self.tr('Sensor') + f' {i + 1}:')
        self.check_auto_temperature_mode.setText(self.tr('Automatic'))
        self.group_schedule.setTitle(self.tr('Schedule'))
        item: QTableWidgetItem
        item = self.table_schedule.horizontalHeaderItem(0)
        item.setText(self.tr('On'))
        item = self.table_schedule.horizontalHeaderItem(1)
        item.setText(self.tr('Angle h'))
        item = self.table_schedule.horizontalHeaderItem(2)
        item.setText(self.tr('Delay'))
        self.button_schedule_action_add.setText(self.tr('+'))
        self.button_schedule_action_remove.setText(self.tr('−'))
        self.button_schedule_action_up.setText(self.tr('↑'))
        self.button_schedule_action_down.setText(self.tr('↓'))
        self.button_power.setText(self.tr('Power ON'))
        self.button_go.setText(self.tr('Go'))
        self.tab_widget.setTabText(self.tab_widget.indexOf(self.tab_main), self.tr('Main'))
        self.group_settings_motor.setTitle(self.tr('Motor'))
        self.label_step_fraction.setText(self.tr('Step Fraction') + ':')
        self.label_settings_speed.setText(self.tr('Motor Speed') + ':')
        self.label_settings_speed_unit.setText(self.tr('°/s'))
        self.label_settings_gear_1.setText(self.tr('Gear 1 Size') + ':')
        self.label_settings_gear_2.setText(self.tr('Gear 2 Size') + ':')
        self.button_move_home.setText(self.tr('Move home'))
        self.button_move_90degrees.setText(self.tr('Move 90° counter-clockwise'))
        self.button_move_360degrees_right.setText(self.tr('Move 360° counter-clockwise'))
        self.button_move_360degrees_left.setText(self.tr('Move 360° clockwise'))
        self.button_move_1step_right.setText(self.tr('Move 1 step counter-clockwise'))
        self.button_move_1step_left.setText(self.tr('Move 1 step clockwise'))
        self.group_settings_measurement.setTitle(self.tr('Measurement'))
        self.label_channels.setText(self.tr('Number of ADC Channels') + ':')
        self.label_measurement_delay.setText(self.tr('Delay Before Measuring') + ':')
        self.spin_measurement_delay.setSuffix(self.tr(' s'))
        self.group_settings_angles.setTitle(self.tr('Angles'))

        self.tab_widget.setCurrentIndex(0)
        self.adjustSize()
