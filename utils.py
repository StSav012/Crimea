# -*- coding: utf-8 -*-

import os.path

import matplotlib
from PyQt5.QtGui import QIcon


def get_icon(name):
    basedir = os.path.join(matplotlib.get_data_path(), 'images')
    return QIcon(os.path.join(basedir, name))
