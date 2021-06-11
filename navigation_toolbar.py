# -*- coding: utf-8 -*-

from typing import List

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QInputDialog, QMessageBox
from matplotlib.backends.backend_qt5 import NavigationToolbar2QT

import figureoptions
import utils
from subplot_tool import SubplotToolQt


class NavigationToolbar(NavigationToolbar2QT):
    def __init__(self, canvas, parent, coordinates: bool = True) -> None:
        super().__init__(canvas, parent, coordinates)
        self.toolbar_parent_hot_fix = parent

    def _init_toolbar(self) -> None:
        pass

    def edit_parameters(self) -> None:
        axes = self.canvas.figure.get_axes()
        if not axes:
            QMessageBox.warning(self.canvas.parent(), "Error", "There are no axes to edit.")
            return
        elif len(axes) == 1:
            ax, = axes
        else:
            titles: List[str] = [
                ax.get_label() or
                ax.get_title() or
                ' — '.join(filter(None, [ax.get_xlabel(), ax.get_ylabel()])) or
                f'<anonymous {type(ax).__name__}>'
                for ax in axes]
            duplicate_titles: List[str] = [title for title in titles if titles.count(title) > 1]
            for i, ax in enumerate(axes):
                if titles[i] in duplicate_titles:
                    titles[i] += f' (id: {id(ax):#x})'  # Deduplicate titles.
            item, ok = QInputDialog.getItem(
                self.canvas.parent(), 'Customize', 'Select axes:', titles, 0, False)
            if not ok:
                return
            ax = axes[titles.index(item)]
        figureoptions.figure_edit(ax, self.toolbar_parent_hot_fix)

    def configure_subplots(self):
        image = utils.get_icon('subplots.svg')
        dia = SubplotToolQt(self.toolbar_parent_hot_fix,
                            title='Subplots options',
                            labels=self.toolbar_parent_hot_fix.adc_channels_names,
                            labels_changed_callback=self.toolbar_parent_hot_fix.set_adc_channels_names)
        dia.setWindowIcon(QIcon(image))
        dia.exec_()
        self.toolbar_parent_hot_fix.bbox_to_anchor = \
            (getattr(self.toolbar_parent_hot_fix.legends[0].get_bbox_to_anchor(), '_bbox').xmin,
             getattr(self.toolbar_parent_hot_fix.legends[0].get_bbox_to_anchor(), '_bbox').ymax)
