# -*- coding: utf-8 -*-

import os
from typing import List

from PyQt5.QtCore import QCoreApplication, QSettings, QTimer, Qt
from PyQt5.QtGui import QIcon, QKeySequence, QPixmap
from PyQt5.QtWidgets import QAbstractItemView, QCheckBox, QDoubleSpinBox, \
    QFrame, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QMainWindow, QProgressDialog, QPushButton, QShortcut, \
    QSizePolicy, QSpacerItem, QSpinBox, QTabWidget, QTableWidget, \
    QTableWidgetItem, QVBoxLayout, QWidget
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from navigation_toolbar import NavigationToolbar
from spin_list_box import SpinListBox


class GUI(QMainWindow):
    def __init__(self):
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
        self.label_bb_angle: QLabel = QLabel(self.group_settings_angles)
        self.spin_bb_angle_alt: QDoubleSpinBox = QDoubleSpinBox(self.group_settings_angles)
        self.label_bb_angle_alt: QLabel = QLabel(self.group_settings_angles)
        self.spin_max_angle: QDoubleSpinBox = QDoubleSpinBox(self.group_settings_angles)
        self.label_max_angle: QLabel = QLabel(self.group_settings_angles)
        self.spin_min_angle: QDoubleSpinBox = QDoubleSpinBox(self.group_settings_angles)
        self.label_min_angle: QLabel = QLabel(self.group_settings_angles)
        self.spin_min_angle_alt: QDoubleSpinBox = QDoubleSpinBox(self.group_settings_angles)
        self.label_min_angle_alt: QLabel = QLabel(self.group_settings_angles)
        self.grid_layout_settings_angles: QGridLayout = QGridLayout(self.group_settings_angles)

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
        self.button_schedule_action_down: QPushButton = QPushButton(self.group_schedule)
        self.button_schedule_action_up: QPushButton = QPushButton(self.group_schedule)
        self.button_schedule_action_remove: QPushButton = QPushButton(self.group_schedule)
        self.button_schedule_action_add: QPushButton = QPushButton(self.group_schedule)
        self.table_schedule: QTableWidget = QTableWidget(self.group_schedule)
        self.grid_layout_schedule: QGridLayout = QGridLayout(self.group_schedule)

        self.group_weather_state: QGroupBox = QGroupBox(self.tab_main)
        self.label_weather_solar_radiation_value: QLabel = QLabel(self.group_weather_state)
        self.label_weather_solar_radiation: QLabel = QLabel(self.group_weather_state)
        self.label_weather_rain_rate_value: QLabel = QLabel(self.group_weather_state)
        self.label_weather_rain_rate: QLabel = QLabel(self.group_weather_state)
        self.label_weather_wind_direction_value: QLabel = QLabel(self.group_weather_state)
        self.label_weather_wind_direction: QLabel = QLabel(self.group_weather_state)
        self.label_weather_wind_speed_value: QLabel = QLabel(self.group_weather_state)
        self.label_weather_wind_speed: QLabel = QLabel(self.group_weather_state)
        self.label_weather_humidity_value: QLabel = QLabel(self.group_weather_state)
        self.label_weather_humidity: QLabel = QLabel(self.group_weather_state)
        self.label_weather_temperature_value: QLabel = QLabel(self.group_weather_state)
        self.label_weather_temperature: QLabel = QLabel(self.group_weather_state)
        self.grid_layout_weather_state: QGridLayout = QGridLayout(self.group_weather_state)
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

    def setup_ui(self):
        # whatever is written in the design file, “Go” button should be disabled initially
        self.button_go.setDisabled(True)

        icon = QIcon()
        icon.addPixmap(QPixmap(os.path.join(os.path.split(__file__)[0], 'crimea-eng-circle.svg')),
                       QIcon.Normal, QIcon.Off)
        self.setWindowIcon(icon)

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

        line = 0
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
        self.table_schedule.setProperty("showDropIndicator", False)
        self.table_schedule.setDragDropOverwriteMode(False)
        self.table_schedule.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_schedule.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.table_schedule.setColumnCount(3)
        self.table_schedule.setRowCount(0)
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
        self.grid_layout_tab_main.addWidget(self.group_schedule, 2, 0)

        self.grid_layout_tab_main.setRowStretch(2, 1)

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

        line = 0
        self.grid_layout_settings_angles.addWidget(self.label_bb_angle, line, 0)
        self.spin_bb_angle.setRange(-180, 180)
        self.spin_bb_angle.setDecimals(1)
        self.spin_bb_angle.setSuffix('°')
        self.spin_bb_angle.setSingleStep(1)
        self.grid_layout_settings_angles.addWidget(self.spin_bb_angle, line, 1)
        line += 1
        self.grid_layout_settings_angles.addWidget(self.label_bb_angle_alt, line, 0)
        self.spin_bb_angle_alt.setRange(-180, 180)
        self.spin_bb_angle_alt.setDecimals(1)
        self.spin_bb_angle_alt.setSuffix('°')
        self.spin_bb_angle_alt.setSingleStep(1)
        self.grid_layout_settings_angles.addWidget(self.spin_bb_angle_alt, line, 1)
        line += 1
        self.grid_layout_settings_angles.addWidget(self.label_max_angle, line, 0)
        self.spin_max_angle.setRange(-180, 180)
        self.spin_max_angle.setDecimals(1)
        self.spin_max_angle.setSuffix('°')
        self.spin_max_angle.setSingleStep(1)
        self.grid_layout_settings_angles.addWidget(self.spin_max_angle, line, 1)
        line += 1
        self.grid_layout_settings_angles.addWidget(self.label_min_angle, line, 0)
        self.spin_min_angle.setRange(-180, 180)
        self.spin_min_angle.setDecimals(1)
        self.spin_min_angle.setSuffix('°')
        self.spin_min_angle.setSingleStep(1)
        self.grid_layout_settings_angles.addWidget(self.spin_min_angle, line, 1)
        line += 1
        self.grid_layout_settings_angles.addWidget(self.label_min_angle_alt, line, 0)
        self.spin_min_angle_alt.setRange(-180, 180)
        self.spin_min_angle_alt.setDecimals(1)
        self.spin_min_angle_alt.setSuffix('°')
        self.spin_min_angle_alt.setSingleStep(1)
        self.grid_layout_settings_angles.addWidget(self.spin_min_angle_alt, line, 1)

        self.grid_layout_settings_angles.setColumnStretch(0, 1)
        self.vertical_layout_settings.addWidget(self.group_settings_angles)

        self.tab_widget.addTab(self.tab_settings, "")

        self.gridLayout.addWidget(self.tab_widget, 0, 1)

        self.figure.tight_layout()
        self.vertical_layout_plot.addWidget(self.toolbar)
        self.vertical_layout_plot.addWidget(self.canvas)
        self.gridLayout.addWidget(self.plot_frame, 0, 0)
        self.gridLayout.setColumnStretch(0, 1)

        self.setCentralWidget(self.central_widget)

        self.translate_ui()
        self.tab_widget.setCurrentIndex(0)
        self.adjustSize()

    def translate_ui(self):
        _translate = QCoreApplication.translate
        self.setWindowTitle(_translate("MainWindow", "Crimea"))
        self.group_weather_state.setTitle(_translate("MainWindow", "Current Weather"))
        self.label_weather_temperature.setText(_translate("MainWindow", "Temperature [°C]") + ':')
        self.label_weather_humidity.setText(_translate("MainWindow", "Humidity [%]") + ':')
        self.label_weather_wind_speed.setText(_translate("MainWindow", "Wind Speed") + ':')
        self.label_weather_wind_direction.setText(_translate("MainWindow", "Wind Direction [°]") + ':')
        self.label_weather_rain_rate.setText(_translate("MainWindow", "Rain Rate") + ':')
        self.label_weather_solar_radiation.setText(_translate("MainWindow", "Solar Radiation") + ':')
        self.group_temperature.setTitle(_translate("MainWindow", "Temperature"))
        self.label_temperature_label.setText(_translate('main_window', 'T [°C]'))
        self.label_state_label.setText(_translate('main_window', 'State'))
        self.label_setpoint_label.setText(_translate('main_window', 'SP [°C]'))
        for i in range(len(self.labels_sensor)):
            self.labels_sensor[i].setText(_translate('main_window', 'Sensor') + f' {i + 1}:')
        self.check_auto_temperature_mode.setText(_translate('main_window', 'Automatic'))
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
        self.button_move_home.setText(_translate("MainWindow", "Move home"))
        self.button_move_90degrees.setText(_translate("MainWindow", "Move 90° counter-clockwise"))
        self.button_move_360degrees_right.setText(_translate("MainWindow", "Move 360° counter-clockwise"))
        self.button_move_360degrees_left.setText(_translate("MainWindow", "Move 360° clockwise"))
        self.button_move_1step_right.setText(_translate("MainWindow", "Move 1 step counter-clockwise"))
        self.button_move_1step_left.setText(_translate("MainWindow", "Move 1 step clockwise"))
        self.group_settings_measurement.setTitle(_translate("MainWindow", "Measurement"))
        self.label_channels.setText(_translate("MainWindow", "Number of ADC Channels") + ':')
        self.label_measurement_delay.setText(_translate("MainWindow", "Delay Before Measuring") + ':')
        self.spin_measurement_delay.setSuffix(_translate("MainWindow", ' s'))
        self.group_settings_angles.setTitle(_translate("MainWindow", "Angles"))
        self.label_bb_angle.setText(_translate("MainWindow", "Black Body Position") + ':')
        self.label_bb_angle_alt.setText(_translate("MainWindow", "Black Body Position (alt)") + ':')
        self.label_max_angle.setText(_translate("MainWindow", "Zenith Position") + ':')
        self.label_min_angle.setText(_translate("MainWindow", "Horizon Position") + ':')
        self.label_min_angle_alt.setText(_translate("MainWindow", "Horizon Position (alt)") + ':')

        self.tab_widget.setTabText(self.tab_widget.indexOf(self.tab_settings), _translate("MainWindow", "Settings"))
