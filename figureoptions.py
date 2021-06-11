# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# see the mpl licenses directory for a copy of the license


"""Module that provides a GUI-based editor for matplotlib's figure options."""
from typing import Dict, List, Tuple, Union

import matplotlib.backends.qt_editor as qt_editor
from matplotlib import colors as mcolors, markers
from matplotlib.axes import Axes
from matplotlib.lines import Line2D

import utils

LINE_STYLES = {'-': 'Solid',
               '--': 'Dashed',
               '-.': 'DashDot',
               ':': 'Dotted',
               'None': 'None',
               }

DRAW_STYLES = {
    'default': 'Default',
    'steps-pre': 'Steps (Pre)', 'steps': 'Steps (Pre)',
    'steps-mid': 'Steps (Mid)',
    'steps-post': 'Steps (Post)'}

MARKERS = markers.MarkerStyle.markers


def figure_edit(axes: Axes, parent=None):
    """Edit matplotlib figure options"""
    sep: Tuple[None, None] = (None, None)  # separator

    # Get / General
    # Cast to builtin floats as they have nicer reprs.
    x_min, x_max = map(float, axes.get_xlim())
    y_min, y_max = map(float, axes.get_ylim())
    general: List[Tuple[Union[None, str], Union[str, float]]] = [
        (None, '<b>X-Axis</b>'),
        ('Left', x_min), ('Right', x_max),
        ('Label', axes.get_xlabel()),
        sep,
        (None, '<b>Y-Axis</b>'),
        ('Bottom', y_min), ('Top', y_max),
        ('Label', axes.get_ylabel()),
    ]

    # Save the unit data
    x_converter = axes.xaxis.converter
    y_converter = axes.yaxis.converter
    x_units = axes.xaxis.get_units()
    y_units = axes.yaxis.get_units()

    # Get / Curves
    line_dict: Dict[str, Line2D] = {}
    for line in axes.get_lines():
        label: str = line.get_label()
        if label.startswith('_'):
            continue
        line_dict[label] = line
    curves = []

    def prepare_data(d, init):
        """Prepare entry for FormLayout.

        `d` is a mapping of shorthands to style names (a single style may
        have multiple shorthands, in particular the shorthands `None`,
        `"None"`, `"none"` and `""` are synonyms); `init` is one shorthand
        of the initial style.

        This function returns an list suitable for initializing a
        FormLayout combobox, namely `[initial_name, (shorthand,
        style_name), (shorthand, style_name), ...]`.
        """
        if init not in d:
            d = {**d, init: str(init)}
        # Drop duplicate shorthands from dict (by overwriting them during
        # the dict comprehension).
        name2short = {name: short for short, name in d.items()}
        # Convert back to {shorthand: name}.
        short2name = {short: name for name, short in name2short.items()}
        # Find the kept shorthand for the style specified by init.
        canonical_init = name2short[d[init]]
        # Sort by representation and prepend the initial value.
        return ([canonical_init] +
                sorted(short2name.items(),
                       key=lambda short_and_name: short_and_name[1]))

    curve_labels = list(line_dict.keys())
    for label in curve_labels:
        line = line_dict[label]
        try:
            color = mcolors.to_hex(
                mcolors.to_rgba(line.get_color(), line.get_alpha()),
                keep_alpha=True)
        except ValueError:
            color = '#000000ff'
        try:
            ec = mcolors.to_hex(
                mcolors.to_rgba(line.get_markeredgecolor(), line.get_alpha()),
                keep_alpha=True)
        except ValueError:
            ec = '#000000ff'
        try:
            fc = mcolors.to_hex(
                mcolors.to_rgba(line.get_markerfacecolor(), line.get_alpha()),
                keep_alpha=True)
        except ValueError:
            fc = '#000000ff'
        curve_data = [
            (None, '<b>Line</b>'),
            ('Line style', prepare_data(LINE_STYLES, line.get_linestyle())),
            ('Draw style', prepare_data(DRAW_STYLES, line.get_drawstyle())),
            ('Width', line.get_linewidth()),
            ('Color (RGBA)', color),
            sep,
            (None, '<b>Marker</b>'),
            ('Style', prepare_data(MARKERS, line.get_marker())),
            ('Size', line.get_markersize()),
            ('Face color (RGBA)', fc),
            ('Edge color (RGBA)', ec)]
        curves.append([curve_data, label, ""])
    # Is there a curve displayed?
    has_curve: bool = bool(curves)

    data_list = [(general, "Axes", "")]
    if curves:
        data_list.append((curves, "Curves", ""))

    def apply_callback(_data):
        """This function will be called to apply changes"""
        orig_x_lim: Tuple[float, float] = axes.get_xlim()
        orig_y_lim: Tuple[float, float] = axes.get_ylim()

        _general = _data.pop(0)
        _curves = _data.pop(0) if has_curve else []
        if _data:
            raise ValueError("Unexpected field")

        # Set / General
        (_x_min, _x_max, x_label, _y_min, _y_max, y_label) = _general

        axes.set_xlim(_x_min, _x_max)
        axes.set_xlabel(x_label)
        axes.set_ylim(_y_min, _y_max)
        axes.set_ylabel(y_label)

        # Restore the unit data
        axes.xaxis.converter = x_converter
        axes.yaxis.converter = y_converter
        axes.xaxis.set_units(x_units)
        axes.yaxis.set_units(y_units)
        getattr(axes.xaxis, '_update_axisinfo')()
        getattr(axes.yaxis, '_update_axisinfo')()

        # Set / Curves
        for index, curve in enumerate(_curves):
            _line = line_dict[curve_labels[index]]
            (line_style, draw_style, line_width, _color, marker, marker_size,
             marker_face_color, marker_edge_color) = curve
            _line.set_linestyle(line_style)
            _line.set_drawstyle(draw_style)
            _line.set_linewidth(line_width)
            rgba = mcolors.to_rgba(_color)
            # _line.set_alpha(None)
            _line.set_color(rgba)
            _line.set_marker(marker)
            _line.set_markersize(marker_size)
            _line.set_markerfacecolor(marker_face_color)
            _line.set_markeredgecolor(marker_edge_color)

        # Redraw
        figure = axes.get_figure()
        figure.canvas.draw()
        if not (axes.get_xlim() == orig_x_lim and axes.get_ylim() == orig_y_lim):
            figure.canvas.toolbar.push_current()
        if (parent is not None
                and hasattr(parent, 'adc_thread')
                and hasattr(parent.adc_thread, 'update_legends')
                and callable(parent.adc_thread.update_legends)):
            parent.adc_thread.update_legends()

    if hasattr(qt_editor, '_formlayout'):
        form_layout = getattr(qt_editor, '_formlayout')
    elif hasattr(qt_editor, 'formlayout'):
        form_layout = getattr(qt_editor, 'formlayout')
    else:
        return
    data = form_layout.fedit(data_list, title="Figure options", parent=parent,
                             icon=utils.get_icon('qt4_editor_options.svg'),
                             apply=apply_callback)
    if data is not None:
        apply_callback(data)
