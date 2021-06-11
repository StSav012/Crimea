# -*- coding: utf-8 -*-

from PyQt5.QtGui import QValidator
from PyQt5.QtWidgets import QSpinBox


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
