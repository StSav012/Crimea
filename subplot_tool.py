# -*- coding: utf-8 -*-

from typing import Dict, List, Optional

from PyQt5.QtWidgets import QDialog, QDoubleSpinBox, QFormLayout, QGroupBox, QHBoxLayout, QPushButton, \
    QVBoxLayout
from matplotlib.figure import Figure
from matplotlib.legend import Legend


class UiSubplotTool(QDialog):
    def __init__(self, *args, **kwargs):
        title: Optional[str] = kwargs.pop('title', None)
        super().__init__(*args, **kwargs)
        self.setObjectName('SubplotTool')
        if title is not None:
            self.setWindowTitle(title)
        self._widgets = {}

        layout = QHBoxLayout()
        self.setLayout(layout)

        left = QVBoxLayout()
        layout.addLayout(left)
        right = QVBoxLayout()
        layout.addLayout(right)

        box = QGroupBox('Borders')
        left.addWidget(box)
        inner = QFormLayout(box)
        for side, label in zip(['top', 'bottom', 'left', 'right'],
                               ['Top:', 'Bottom:', 'Left:', 'Right:']):
            self._widgets[side] = widget = QDoubleSpinBox()
            widget.setMinimum(0)
            widget.setMaximum(1)
            widget.setDecimals(3)
            widget.setSingleStep(.005)
            widget.setKeyboardTracking(False)
            inner.addRow(label, widget)
        left.addStretch(1)

        box = QGroupBox('Spacings')
        left.addWidget(box)
        inner = QFormLayout(box)
        for side, label in zip(['hspace', 'wspace'],
                               ['Vertical:', 'Horizontal:']):
            self._widgets[side] = widget = QDoubleSpinBox()
            widget.setMinimum(0)
            widget.setMaximum(1)
            widget.setDecimals(3)
            widget.setSingleStep(.005)
            widget.setKeyboardTracking(False)
            inner.addRow(label, widget)

        box = QGroupBox('Legend')
        left.addWidget(box)
        inner = QFormLayout(box)
        for side, label in zip(['legend top', 'legend left'],
                               ['Top:', 'Left:']):
            self._widgets[side] = widget = QDoubleSpinBox()
            widget.setMinimum(0)
            widget.setMaximum(9)
            widget.setDecimals(3)
            widget.setSingleStep(.005)
            widget.setKeyboardTracking(False)
            inner.addRow(label, widget)

        for action in ['Tight layout', 'Reset', 'Close']:
            self._widgets[action] = widget = QPushButton(action)
            widget.setAutoDefault(False)
            right.addWidget(widget)
        right.addStretch(1)

        self._widgets['Close'].setFocus()


class SubplotToolQt(UiSubplotTool):
    def __init__(self, target_figure: Figure,
                 legends: List[Legend],
                 *args, **kwargs):
        UiSubplotTool.__init__(self, *args, **kwargs)

        self._figure: Figure = target_figure
        self._legends: List[Legend] = legends

        for lower, higher in [('bottom', 'top'), ('left', 'right')]:
            self._widgets[lower].valueChanged.connect(
                lambda val: self._widgets[higher].setMinimum(val + .001))
            self._widgets[higher].valueChanged.connect(
                lambda val: self._widgets[lower].setMaximum(val - .001))

        self._attrs: List[str] = ['top', 'bottom', 'left', 'right', 'hspace', 'wspace']
        self._defaults: Dict[str, float] = {attr: vars(self._figure.subplotpars)[attr]
                                            for attr in self._attrs}
        self._legends_attrs: List[str] = ['legend left', 'legend top']
        if legends:
            self._legends_defaults: Dict[str, float] = \
                dict(zip(self._legends_attrs,
                         [getattr(legends[0].get_bbox_to_anchor(), '_bbox').xmin,
                          getattr(legends[0].get_bbox_to_anchor(), '_bbox').ymax]))
        else:
            self._legends_defaults: Dict[str, float] = dict()

        # Set values after setting the range callbacks, but before setting up
        # the redraw callbacks.
        self._reset()

        for attr in self._attrs:
            self._widgets[attr].valueChanged.connect(self._on_value_changed)
        for attr in self._legends_attrs:
            self._widgets[attr].valueChanged.connect(self._on_legend_value_changed)
        for action, method in [('Tight layout', self._tight_layout),
                               ('Reset', self._reset),
                               ('Close', self.close)]:
            self._widgets[action].clicked.connect(method)

    def _on_value_changed(self):
        self._figure.subplots_adjust(**{attr: self._widgets[attr].value()
                                        for attr in self._attrs})
        self._figure.canvas.draw_idle()

    def _on_legend_value_changed(self):
        for legend in self._legends:
            legend.set_bbox_to_anchor(tuple(self._widgets[attr].value()
                                            for attr in self._legends_attrs))
        self._figure.canvas.draw_idle()

    def _tight_layout(self):
        self._figure.tight_layout()
        for attr in self._attrs:
            widget = self._widgets[attr]
            widget.blockSignals(True)
            widget.setValue(vars(self._figure.subplotpars)[attr])
            widget.blockSignals(False)
        self._figure.canvas.draw_idle()

    def _reset(self):
        for attr, value in self._defaults.items():
            self._widgets[attr].setValue(value)
        for attr, value in self._legends_defaults.items():
            self._widgets[attr].setValue(value)
