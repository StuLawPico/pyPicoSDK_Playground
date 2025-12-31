"""
UI Components Module for PicoScope Streaming Application

This module contains all GUI widget creation and styling logic,
separated from the main application logic for better organization.
"""

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore


# ============================================================================
# UI STYLE CONSTANTS
# ============================================================================

# Base styling for status widgets (moved from main script)
STATUS_WIDGET_BASE_STYLE = """
    QLabel {
        padding: 2px 6px;
        font-size: 11px;
        font-weight: bold;
        border-radius: 3px;
    }
"""

# Color schemes for different status display types (moved from main script)
STATUS_COLOR_SCHEMES = {
    'adc_rate': {
        'label_color': '#90EE90',
        'bg_color': '#2d4a2d',
        'text_color': '#90EE90',
        'border_color': '#4a6b4a'
    },
    'downsampled_rate': {
        'label_color': '#FFB6C1',
        'bg_color': '#4a2d4a',
        'text_color': '#FFB6C1',
        'border_color': '#6b4a6b'
    },
    'min_poll': {
        'label_color': '#B6FFF2',
        'bg_color': '#2d4a4a',
        'text_color': '#B6FFF2',
        'border_color': '#2b6666'
    },
    'performance': {
        'label_color': '#CCCCCC',
        'bg_color': '#3a3a3a',
        'text_color': '#CCCCCC',
        'border_color': '#555555'
    },
    'memory_req': {
        'label_color': '#B6C1FF',
        'bg_color': '#2d2d4a',
        'text_color': '#B6C1FF',
        'border_color': '#4a4a6b'
    },
    'max_memory': {
        'label_color': '#FFB6C1',
        'bg_color': '#4a2d2d',
        'text_color': '#FFB6C1',
        'border_color': '#6b4a4a'
    },
    'display_window': {
        'label_color': '#87CEEB',
        'bg_color': '#2d3a4a',
        'text_color': '#87CEEB',
        'border_color': '#4a5a6b'
    },
}

# Base widget styles to reduce duplication
BASE_WIDGET_STYLE = """
    background-color: #1a1a1a;
    color: white;
    border: 1px solid #444444;
    padding: 2px 6px;
    font-size: 11px;
    min-width: 70px;
"""

BASE_WIDGET_HOVER = """
    border-color: #555555;
    background-color: #242424;
"""

BASE_BUTTON_STYLE = """
    color: white;
    border: none;
    padding: 5px 8px;
    font-size: 11px;
    font-weight: bold;
    border-radius: 3px;
    min-width: 80px;
"""

BASE_BUTTON_HOVER = """
    background-color: #6666ff;
"""

BASE_BUTTON_PRESSED = """
    background-color: #3333cc;
"""

BASE_BUTTON_DISABLED = """
    background-color: #888888;
    color: #cccccc;
"""

STYLES = {
    'dark_spinbox': f"""
        QSpinBox {{{BASE_WIDGET_STYLE}}}
        QSpinBox:hover {{{BASE_WIDGET_HOVER}}}
    """,
    
    'dark_double_spinbox': f"""
        QDoubleSpinBox {{{BASE_WIDGET_STYLE}}}
        QDoubleSpinBox:hover {{{BASE_WIDGET_HOVER}}}
    """,
    
    'dark_combobox': f"""
        QComboBox {{{BASE_WIDGET_STYLE}}}
        QComboBox:hover {{{BASE_WIDGET_HOVER}}}
        QComboBox::drop-down {{
            border: none;
        }}
        QComboBox::down-arrow {{
            image: none;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 4px solid white;
            margin-right: 4px;
        }}
        QComboBox QAbstractItemView {{
            background-color: #1a1a1a;
            border: 1px solid #444444;
            selection-background-color: #444444;
            selection-color: white;
            color: white;
            outline: none;
        }}
        QComboBox QAbstractItemView::item {{
            padding: 4px;
            color: white;
        }}
        QComboBox QAbstractItemView::item:hover {{
            background-color: #333333;
            color: white;
        }}
        QComboBox QAbstractItemView::item:selected {{
            background-color: #444444;
            color: white;
        }}
    """,
    
    'primary_button': f"""
        QPushButton {{
            background-color: #2674f0;
            {BASE_BUTTON_STYLE}
            border-radius: 4px;
            padding: 4px 10px;
            font-weight: 500;
            min-height: 26px;
        }}
        QPushButton:hover {{
            background-color: #3b84ff;
        }}
        QPushButton:pressed {{{BASE_BUTTON_PRESSED}}}
        QPushButton:disabled {{{BASE_BUTTON_DISABLED}}}
    """,
    
    'stop_button': f"""
        QPushButton {{
            background-color: #d64545;
            {BASE_BUTTON_STYLE}
            border-radius: 4px;
            padding: 4px 10px;
            font-weight: 500;
            min-height: 26px;
        }}
        QPushButton:hover {{
            background-color: #e05a5a;
        }}
        QPushButton:pressed {{
            background-color: #cc3333;
        }}
        QPushButton:disabled {{{BASE_BUTTON_DISABLED}}}
    """,
    
    'secondary_button': f"""
        QPushButton {{
            background-color: #555555;
            color: #ffffff;
            border: none;
            border-radius: 4px;
            padding: 4px 10px;
            font-weight: 500;
            min-height: 26px;
            {BASE_BUTTON_STYLE}
        }}
        QPushButton:hover {{
            background-color: #666666;
        }}
        QPushButton:disabled {{{BASE_BUTTON_DISABLED}}}
    """,
    
    'slider': """
        QSlider::groove:horizontal {
            height: 4px;
            margin: 0 4px;
            border-radius: 2px;
            background: #333333;
        }
        QSlider::handle:horizontal {
            width: 10px;
            height: 10px;
            margin: -3px 0;
            border-radius: 5px;
            background: #4b6ef5;
        }
        QSlider::handle:horizontal:hover {
            background: #6c88ff;
        }
    """,
    
    'section_label': """
        color: #cccccc;
        font-weight: 500;
        font-size: 9pt;
        background-color: transparent;
        padding: 0px;
    """,
    
    'value_display_label': """
        QLabel {
            background-color: #2a2a2a;
            color: #87CEEB;
            border: 1px solid #444444;
            padding: 3px 6px;
            font-size: 10px;
            font-weight: bold;
            border-radius: 3px;
        }
    """,
    
    'groupbox': """
        QGroupBox {
            border: none;
            margin-top: 12px;
            padding-top: 0px;
            background-color: transparent;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 0px;
            padding: 0 0 4px 0;
            font-weight: 600;
            font-size: 9pt;
            color: #ffffff;
        }
    """
}


# ============================================================================
# CONTROL PANEL BUILDER FUNCTIONS
# ============================================================================

def validate_ratio(value):
    """Ensure ratio is a multiple of 64"""
    return ((value - 64) // 64) * 64 + 64


def create_group_widget(title):
    """
    Create a standardized group widget with consistent styling.
    
    Args:
        title: Group box title
    
    Returns:
        tuple: (group_widget, layout)
    """
    group = pg.QtWidgets.QGroupBox(title)
    layout = pg.QtWidgets.QVBoxLayout()
    group.setLayout(layout)
    group.setStyleSheet(STYLES['groupbox'])
    layout.setSpacing(4)
    layout.setContentsMargins(0, 4, 0, 0)  # Minimal margins, no side padding
    return group, layout


def create_label_with_style(text, style='section_label'):
    """
    Create a standardized label with consistent styling.
    
    Args:
        text: Label text
        style: Style key from STYLES dict
    
    Returns:
        QLabel widget
    """
    label = pg.QtWidgets.QLabel(text)
    label.setStyleSheet(STYLES[style])
    return label


def make_scroll_hint_label():
    """
    Create a standardized "scroll to adjust" hint label.
    
    Returns:
        QLabel widget with scroll hint styling
    """
    hint_label = pg.QtWidgets.QLabel("scroll to adjust")
    hint_label.setStyleSheet("""
        QLabel {
            color: #888888;
            font-size: 9px;
            font-style: italic;
            padding: 0px;
            margin: 0px;
        }
    """)
    return hint_label


def create_spinbox_with_style(min_val, max_val, current_val, style='dark_spinbox', step=1, tooltip=None):
    """
    Create a standardized spinbox with consistent styling.
    
    Args:
        min_val: Minimum value
        max_val: Maximum value
        current_val: Current value
        style: Style key from STYLES dict
        step: Step size
        tooltip: Optional tooltip text
    
    Returns:
        QSpinBox widget
    """
    spinbox = pg.QtWidgets.QSpinBox()
    spinbox.setRange(min_val, max_val)
    spinbox.setSingleStep(step)
    spinbox.setValue(current_val)
    # Enable scroll wheel adjustment when focused
    spinbox.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
    # Modern styling: no buttons, no frame
    ButtonSymbols = pg.QtWidgets.QAbstractSpinBox.ButtonSymbols
    spinbox.setButtonSymbols(ButtonSymbols.NoButtons)
    spinbox.setFrame(False)
    spinbox.setStyleSheet(STYLES[style])
    
    # Enhanced tooltip with scroll wheel instructions
    scroll_hint = "Hover and scroll to adjust • Ctrl+scroll for faster"
    if tooltip:
        enhanced_tooltip = f"{tooltip}\n\n{scroll_hint}"
    else:
        enhanced_tooltip = scroll_hint
    spinbox.setToolTip(enhanced_tooltip)
    
    return spinbox


def create_slider_spinbox_combo(min_val, max_val, current_val, step=1, suffix='', tooltip=None):
    """
    Create a spinbox with scroll wheel functionality and helpful hints.
    Sliders have been removed in favor of scroll wheel adjustment.
    
    Args:
        min_val: Minimum value
        max_val: Maximum value
        current_val: Current value
        step: Step size for spinbox
        suffix: Optional suffix text for spinbox (e.g., ' ns')
        tooltip: Optional tooltip text (will be enhanced with scroll wheel instructions)
    
    Returns:
        tuple: (container_widget, slider_placeholder, spinbox)
        Note: slider_placeholder is a dummy object for backward compatibility
    """
    # Create container widget with horizontal layout
    container = pg.QtWidgets.QWidget()
    layout = pg.QtWidgets.QHBoxLayout()
    container.setLayout(layout)
    layout.setSpacing(6)
    layout.setContentsMargins(0, 0, 0, 0)
    
    # Create spinbox with modern styling
    spinbox = pg.QtWidgets.QSpinBox()
    spinbox.setRange(min_val, max_val)
    spinbox.setSingleStep(step)
    spinbox.setValue(current_val)
    # Enable scroll wheel adjustment when focused
    spinbox.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
    # Hide spinbox buttons for modern look (Qt6)
    ButtonSymbols = pg.QtWidgets.QAbstractSpinBox.ButtonSymbols
    spinbox.setButtonSymbols(ButtonSymbols.NoButtons)
    spinbox.setFrame(False)
    spinbox.setStyleSheet(STYLES['dark_spinbox'])
    if suffix:
        spinbox.setSuffix(suffix)
    
    # Enhanced tooltip with scroll wheel instructions
    scroll_hint = "Hover and scroll to adjust • Ctrl+scroll for faster"
    if tooltip:
        enhanced_tooltip = f"{tooltip}\n\n{scroll_hint}"
    else:
        enhanced_tooltip = scroll_hint
    spinbox.setToolTip(enhanced_tooltip)
    
    # Add subtle hint label
    hint_label = pg.QtWidgets.QLabel("scroll to adjust")
    hint_label.setStyleSheet("""
        QLabel {
            color: #888888;
            font-size: 9px;
            font-style: italic;
            padding: 0px;
            margin: 0px;
        }
    """)
    
    # Create a placeholder object for backward compatibility (for setEnabled calls)
    class SliderPlaceholder:
        def setEnabled(self, enabled):
            pass  # Do nothing, slider is removed
    
    slider_placeholder = SliderPlaceholder()
    
    # Add widgets to layout: spinbox first, then hint label
    layout.addWidget(spinbox)
    layout.addWidget(hint_label)
    layout.addStretch()  # Push everything to the left
    
    return container, slider_placeholder, spinbox


def create_double_spinbox_with_style(min_val, max_val, current_val, decimals=2, step=0.1, suffix='', tooltip=None):
    """
    Create a standardized double spinbox with consistent styling.
    
    Args:
        min_val: Minimum value
        max_val: Maximum value
        current_val: Current value
        decimals: Number of decimal places
        step: Step size
        suffix: Suffix text (e.g., ' FPS')
        tooltip: Optional tooltip text
    
    Returns:
        QDoubleSpinBox widget
    """
    spinbox = pg.QtWidgets.QDoubleSpinBox()
    spinbox.setRange(min_val, max_val)
    spinbox.setDecimals(decimals)
    spinbox.setSingleStep(step)
    spinbox.setValue(current_val)
    # Enable scroll wheel adjustment when focused
    spinbox.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
    # Modern styling: no buttons, no frame
    ButtonSymbols = pg.QtWidgets.QAbstractSpinBox.ButtonSymbols
    spinbox.setButtonSymbols(ButtonSymbols.NoButtons)
    spinbox.setFrame(False)
    if suffix:
        spinbox.setSuffix(suffix)
    spinbox.setStyleSheet(STYLES['dark_double_spinbox'])
    
    # Enhanced tooltip with scroll wheel instructions
    scroll_hint = "Hover and scroll to adjust • Ctrl+scroll for faster"
    if tooltip:
        enhanced_tooltip = f"{tooltip}\n\n{scroll_hint}"
    else:
        enhanced_tooltip = scroll_hint
    spinbox.setToolTip(enhanced_tooltip)
    
    return spinbox


def create_status_display_widget(label_text, display_text, color_scheme_name):
    """
    Create a standardized status display widget with consistent styling.
    
    Args:
        label_text: Text for the label
        display_text: Initial text for the display widget
        color_scheme_name: Name of the color scheme from STATUS_COLOR_SCHEMES
    
    Returns:
        tuple: (label_widget, display_widget)
    """
    color_scheme = STATUS_COLOR_SCHEMES[color_scheme_name]
    
    # Create label
    label = pg.QtWidgets.QLabel(label_text)
    label.setStyleSheet(f"color: {color_scheme['label_color']}; font-weight: bold; font-size: 11px;")
    
    # Create display widget
    display = pg.QtWidgets.QLabel(display_text)
    display.setProperty('class', 'status-pill')
    display.setStyleSheet(f"""
        QLabel.status-pill {{
            background-color: {color_scheme['bg_color']};
            color: {color_scheme['text_color']};
            border: 1px solid {color_scheme['border_color']};
            padding: 2px 6px;
            font-size: 9px;
            font-weight: bold;
            border-radius: 10px;
        }}
    """)
    
    return label, display


def create_status_bar():
    """
    Create the complete status bar with two rows of metrics.
    
    Returns:
        tuple: (status_bar_widget, status_displays_dict)
        status_displays_dict contains all the display widgets for updates
    """
    # Create status bar with two rows
    status_bar = pg.QtWidgets.QWidget()
    status_bar.setObjectName('statusBarContainer')
    status_bar_main_layout = pg.QtWidgets.QVBoxLayout()
    status_bar.setLayout(status_bar_main_layout)
    status_bar.setStyleSheet("""
        QWidget#statusBarContainer {
            background-color: #202020;
            padding: 4px 6px;
        }
    """)
    status_bar_main_layout.setContentsMargins(6, 4, 6, 4)
    status_bar_main_layout.setSpacing(2)

    # Row 1: Performance metrics (rates, polling, efficiency)
    row1_layout = pg.QtWidgets.QHBoxLayout()
    row1_layout.setSpacing(10)

    # ADC Rate display - using helper function
    adc_rate_label, adc_rate_display = create_status_display_widget('ADC:', '0.0 MSPS', 'adc_rate')
    row1_layout.addWidget(adc_rate_label)
    row1_layout.addWidget(adc_rate_display)

    row1_layout.addWidget(create_separator())

    # Downsampled Rate display - using helper function
    downsampled_rate_label, downsampled_rate_display = create_status_display_widget('Downsampled:', '0.0 kHz', 'downsampled_rate')
    row1_layout.addWidget(downsampled_rate_label)
    row1_layout.addWidget(downsampled_rate_display)

    row1_layout.addWidget(create_separator())

    # Min Poll Interval display - using helper function
    min_poll_label, min_poll_display = create_status_display_widget('Min Poll:', 'Unknown', 'min_poll')
    row1_layout.addWidget(min_poll_label)
    row1_layout.addWidget(min_poll_display)

    row1_layout.addWidget(create_separator())

    # System performance status display - using helper function
    efficiency_label, efficiency_display = create_status_display_widget('Performance:', '◌ Initializing...', 'performance')
    efficiency_label.setToolTip("Shows how well the system is keeping up with the hardware data stream")
    row1_layout.addWidget(efficiency_label)
    row1_layout.addWidget(efficiency_display)

    # Set initial tooltip for efficiency display
    initial_tooltip = """
<div style='background-color: #2b2b2b; color: #ffffff; padding: 8px; border: 1px solid #555555;'>
    <p style='margin: 2px; color: #cccccc;'><b>System Performance Monitor</b></p>
    <p style='margin: 2px; color: #ffffff;'>Collecting initial data...</p>
    <hr style='border: 0; border-top: 1px solid #555555; margin: 6px 0;'>
    <p style='margin: 2px; color: #aaaaaa;'><i>This indicator will show:</i></p>
    <p style='margin: 2px; color: #ffffff;'>• Sample acquisition efficiency</p>
    <p style='margin: 2px; color: #ffffff;'>• Data consistency (jitter)</p>
    <p style='margin: 2px; color: #ffffff;'>• Overall system health</p>
</div>
"""
    efficiency_display.setToolTip(initial_tooltip)

    # Add stretch to push row 1 items to the left
    row1_layout.addStretch()

    # Add row 1 to main layout
    status_bar_main_layout.addLayout(row1_layout)

    # Row 2: Hardware memory metrics
    row2_layout = pg.QtWidgets.QHBoxLayout()
    row2_layout.setSpacing(10)

    # Memory Required display - using helper function
    memory_label, memory_display = create_status_display_widget('HW Memory Req:', '0 samples', 'memory_req')
    row2_layout.addWidget(memory_label)
    row2_layout.addWidget(memory_display)

    row2_layout.addWidget(create_separator())

    # Max Memory display - using helper function
    max_memory_label, max_memory_display = create_status_display_widget('HW Max Memory:', '0 samples', 'max_memory')
    row2_layout.addWidget(max_memory_label)
    row2_layout.addWidget(max_memory_display)

    row2_layout.addWidget(create_separator())

    # Display Window (Time) - using helper function
    display_window_label, display_window_display = create_status_display_widget('Display Window:', '0.0 s (0 / 100,000)', 'display_window')
    row2_layout.addWidget(display_window_label)
    row2_layout.addWidget(display_window_display)

    # Add stretch to push row 2 items to the left
    row2_layout.addStretch()

    # Add row 2 to main layout
    status_bar_main_layout.addLayout(row2_layout)


    # Create dictionary of all display widgets for easy access
    status_displays = {
        'adc_rate': adc_rate_display,
        'downsampled_rate': downsampled_rate_display,
        'min_poll': min_poll_display,
        'efficiency': efficiency_display,
        'memory_req': memory_display,
        'max_memory': max_memory_display,
        'display_window': display_window_display
    }

    return status_bar, status_displays


def create_separator():
    """Create a standardized separator widget."""
    sep = pg.QtWidgets.QLabel('|')
    sep.setStyleSheet("color: #666666;")
    return sep


def create_downsampling_controls(psdk, current_ratio, current_mode):
    """
    Create the downsampling controls container.
    
    Args:
        psdk: PicoSDK module reference
        current_ratio: Current downsampling ratio value
        current_mode: Current downsampling mode
    
    Returns:
        tuple: (container_widget, mode_combo, ratio_spinbox)
    """
    # Create a simple container widget without title, matching groupbox spacing
    downsample_container = pg.QtWidgets.QWidget()
    downsample_layout = pg.QtWidgets.QVBoxLayout()
    downsample_container.setLayout(downsample_layout)
    downsample_layout.setSpacing(4)
    # Match the margin-top of groupboxes (12px) for consistent spacing in cards
    downsample_layout.setContentsMargins(0, 12, 0, 0)
    
    # Mode and Ratio on same row
    mode_ratio_row = pg.QtWidgets.QHBoxLayout()
    mode_ratio_row.setSpacing(4)
    
    # Mode selection - label outside, combo has its own border
    mode_label = pg.QtWidgets.QLabel('Mode:')
    mode_label.setStyleSheet("color: #e0e0e0; font-size: 9pt; font-weight: 500; padding: 0px; margin: 0px 4px 0px 0px; border: none; background: transparent;")
    mode_ratio_row.addWidget(mode_label)
    
    # Mode combo with border only around the combo itself
    mode_combo = pg.QtWidgets.QComboBox()
    mode_combo.addItem('Decimate', psdk.RATIO_MODE.DECIMATE)
    mode_combo.addItem('Average', psdk.RATIO_MODE.AVERAGE)
    mode_combo.setCurrentText(
        'Decimate' if current_mode == psdk.RATIO_MODE.DECIMATE else 'Average'
    )
    # Use dark_combobox style which gives border only to the combo
    mode_combo.setStyleSheet(STYLES['dark_combobox'])
    mode_ratio_row.addWidget(mode_combo)
    
    # Add spacing between mode and ratio
    mode_ratio_row.addSpacing(8)
    
    # Ratio selection with spinbox combo
    ratio_label = pg.QtWidgets.QLabel('Ratio:')
    ratio_label.setStyleSheet("color: #e0e0e0; font-size: 9pt; font-weight: 500; padding: 0px; margin: 0px; border: none; background: transparent;")
    mode_ratio_row.addWidget(ratio_label)
    ratio_container, ratio_slider, ratio_spinbox = create_slider_spinbox_combo(
        64, 640000, current_ratio, step=64
    )
    # Connect validation to keep ratio as multiple of 64
    # Validation will adjust value if needed, and sync mechanism will update slider
    ratio_spinbox.valueChanged.connect(
        lambda v: ratio_spinbox.setValue(validate_ratio(v))
    )
    mode_ratio_row.addWidget(ratio_container)
    mode_ratio_row.addStretch()
    
    downsample_layout.addLayout(mode_ratio_row)
    
    return downsample_container, mode_combo, ratio_spinbox


def create_interval_controls(psdk, current_interval, current_units):
    """
    Create the ADC sample interval controls group.
    
    Args:
        psdk: PicoSDK module reference
        current_interval: Current sample interval value
        current_units: Current time units
    
    Returns:
        tuple: (group_widget, interval_spinbox, units_combo)
    """
    interval_group, interval_layout = create_group_widget("ADC Interval")
    
    # Interval on its own row
    interval_row = pg.QtWidgets.QHBoxLayout()
    interval_row.setSpacing(4)
    interval_row.addWidget(create_label_with_style('Interval:'))
    interval_container, interval_slider, interval_spinbox = create_slider_spinbox_combo(
        1, 1000000, current_interval, step=1
    )
    interval_row.addWidget(interval_container)
    interval_row.addStretch()
    interval_layout.addLayout(interval_row)
    
    # Time units on its own row
    units_row = pg.QtWidgets.QHBoxLayout()
    units_row.setSpacing(4)
    units_row.addWidget(create_label_with_style('Units:'))
    units_combo = pg.QtWidgets.QComboBox()
    units_combo.addItem('ns', psdk.TIME_UNIT.NS)
    units_combo.addItem('μs', psdk.TIME_UNIT.US)
    units_combo.addItem('ms', psdk.TIME_UNIT.MS)
    units_combo.addItem('s', psdk.TIME_UNIT.S)
    
    # Set current value
    if current_units == psdk.TIME_UNIT.NS:
        units_combo.setCurrentText('ns')
    elif current_units == psdk.TIME_UNIT.US:
        units_combo.setCurrentText('μs')
    elif current_units == psdk.TIME_UNIT.MS:
        units_combo.setCurrentText('ms')
    else:
        units_combo.setCurrentText('s')
    
    units_combo.setStyleSheet(STYLES['dark_combobox'])
    units_row.addWidget(units_combo)
    units_row.addStretch()
    interval_layout.addLayout(units_row)
    
    return interval_group, interval_spinbox, units_combo


def create_buffer_controls(current_buffer_size):
    """
    Create the hardware buffer size controls group.
    
    Args:
        current_buffer_size: Current buffer size value
    
    Returns:
        tuple: (group_widget, hw_buffer_spinbox)
    """
    # Create a simple container widget without title, matching groupbox spacing
    hw_buffer_container = pg.QtWidgets.QWidget()
    hw_buffer_layout = pg.QtWidgets.QVBoxLayout()
    hw_buffer_container.setLayout(hw_buffer_layout)
    hw_buffer_layout.setSpacing(4)
    # Match the margin-top of groupboxes (12px) for consistent spacing in cards
    hw_buffer_layout.setContentsMargins(0, 12, 0, 0)
    
    # Buffer size row with label and info text side by side
    buffer_row = pg.QtWidgets.QHBoxLayout()
    buffer_row.setSpacing(4)
    buffer_row.addWidget(create_label_with_style('Buffer Size:'))
    
    # Info label next to Buffer Size label
    hw_buffer_info = pg.QtWidgets.QLabel('(Auto-optimized on Apply)')
    hw_buffer_info.setStyleSheet("color: #666666; font-size: 9px; font-style: italic;")
    buffer_row.addWidget(hw_buffer_info)
    buffer_row.addStretch()
    hw_buffer_layout.addLayout(buffer_row)
    
    hw_buffer_spinbox = create_spinbox_with_style(
        1000, 10_000_000, current_buffer_size, step=1000,
        tooltip='Size of hardware double buffers (downsampled samples).\n'
                'Larger = better safety margin, but uses more device memory.'
    )
    hw_buffer_layout.addWidget(hw_buffer_spinbox)
    
    return hw_buffer_container, hw_buffer_spinbox


def create_performance_controls(current_refresh_fps, current_poll_interval):
    """
    Create the performance settings controls group.
    
    Args:
        current_refresh_fps: Current display refresh rate (FPS)
        current_poll_interval: Current polling interval (seconds)
    
    Returns:
        tuple: (group_widget, refresh_spinbox, poll_spinbox)
    """
    performance_group, performance_layout = create_group_widget("Performance")
    
    # Display update rate
    performance_layout.addWidget(create_label_with_style('Display Rate:'))
    
    refresh_spinbox = create_spinbox_with_style(
        1, 120, current_refresh_fps,
        tooltip='How often the plot updates (higher = smoother but more CPU)'
    )
    refresh_spinbox.setSuffix(' FPS')
    performance_layout.addWidget(refresh_spinbox)
    
    # Polling interval
    performance_layout.addWidget(create_label_with_style('Poll Interval:'))
    
    poll_spinbox = create_double_spinbox_with_style(
        0.01, 100.0, current_poll_interval * 1000,  # Convert seconds to ms
        decimals=2, step=0.1, suffix=' ms',
        tooltip='How often to check hardware for new data (lower = less latency)'
    )
    performance_layout.addWidget(poll_spinbox)
    
    return performance_group, refresh_spinbox, poll_spinbox


def create_time_window_spinbox(current_time_window):
    """
    Create a time window spinbox widget with hint label.
    
    Args:
        current_time_window: Current time window value (seconds)
    
    Returns:
        tuple: (time_window_spinbox, hint_label)
    """
    time_window_spinbox = pg.QtWidgets.QDoubleSpinBox()
    time_window_spinbox.setRange(0.01, 1.0)  # 10ms to 1 second
    time_window_spinbox.setDecimals(3)  # Allow 3 decimal places (for ms precision)
    time_window_spinbox.setSingleStep(0.01)  # 10ms steps
    time_window_spinbox.setValue(current_time_window)
    time_window_spinbox.setSuffix(' s')
    # Enable scroll wheel adjustment when focused
    time_window_spinbox.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
    # Modern styling: no buttons, no frame
    ButtonSymbols = pg.QtWidgets.QAbstractSpinBox.ButtonSymbols
    time_window_spinbox.setButtonSymbols(ButtonSymbols.NoButtons)
    time_window_spinbox.setFrame(False)
    time_window_spinbox.setStyleSheet(STYLES['dark_double_spinbox'])
    
    # Enhanced tooltip with scroll wheel instructions
    scroll_hint = "Hover and scroll to adjust • Ctrl+scroll for faster"
    tooltip = (
        'Adjust the time span of data visible in the plot (10ms to 1s).\n'
        'Changes apply when you click "Apply Changes".\n\n'
        f'{scroll_hint}'
    )
    time_window_spinbox.setToolTip(tooltip)
    
    hint_label = make_scroll_hint_label()
    return time_window_spinbox, hint_label


def create_time_window_controls(current_time_window):
    """
    Create the display time window controls group.
    
    Args:
        current_time_window: Current time window value (seconds)
    
    Returns:
        tuple: (group_widget, time_window_slider_placeholder, time_window_spinbox)
        Note: slider_placeholder is a dummy object for backward compatibility
    """
    time_window_group = pg.QtWidgets.QGroupBox("Display Window")
    time_window_layout = pg.QtWidgets.QVBoxLayout()
    time_window_group.setLayout(time_window_layout)
    time_window_group.setStyleSheet(STYLES['groupbox'])
    time_window_layout.setSpacing(2)
    time_window_layout.setContentsMargins(6, 6, 6, 4)
    
    # Title row
    title_row = pg.QtWidgets.QHBoxLayout()
    title_row.setSpacing(4)
    
    time_window_label = pg.QtWidgets.QLabel('Time Span:')
    time_window_label.setStyleSheet(STYLES['section_label'])
    title_row.addWidget(time_window_label)
    title_row.addStretch()
    time_window_layout.addLayout(title_row)
    
    # Container for spinbox and hint
    spinbox_container = pg.QtWidgets.QWidget()
    spinbox_layout = pg.QtWidgets.QHBoxLayout()
    spinbox_container.setLayout(spinbox_layout)
    spinbox_layout.setSpacing(6)
    spinbox_layout.setContentsMargins(0, 0, 0, 0)
    
    # Create double spinbox for time window using helper
    time_window_spinbox, hint_label = create_time_window_spinbox(current_time_window)
    
    # Add widgets to container
    spinbox_layout.addWidget(time_window_spinbox)
    spinbox_layout.addWidget(hint_label)
    spinbox_layout.addStretch()
    
    time_window_layout.addWidget(spinbox_container)
    
    # Create a placeholder object for backward compatibility
    class SliderPlaceholder:
        def setEnabled(self, enabled):
            pass  # Do nothing, slider is removed
        def value(self):
            return int(time_window_spinbox.value())  # Return integer for compatibility
    
    slider_placeholder = SliderPlaceholder()
    
    return time_window_group, slider_placeholder, time_window_spinbox


def create_raw_data_display_controls(enabled=False, mode='mean', factor=1, max_points=500_000):
    """
    Create the raw data display controls group for PyQtGraph downsampling.
    
    Args:
        enabled: Whether PyQtGraph downsampling is enabled by default
        mode: Default downsampling mode ('subsample', 'mean', or 'peak')
        factor: Default downsampling factor (1 = no downsampling)
        max_points: Maximum number of downsampled points to display (default: 500K)
    
    Returns:
        tuple: (group_widget, enable_checkbox, mode_combo, factor_spinbox, max_points_spinbox, gated_raw_downsample_checkbox, region_markers_checkbox)
    """
    raw_display_group, raw_display_layout = create_group_widget("Raw Data Display")
    
    # Enable/Disable checkbox
    enable_checkbox = pg.QtWidgets.QCheckBox("Enable PyQtGraph Downsampling")
    enable_checkbox.setChecked(enabled)
    enable_checkbox.setStyleSheet("""
        QCheckBox {
            color: white;
            font-size: 11px;
            padding: 2px;
        }
        QCheckBox::indicator {
            width: 14px;
            height: 14px;
            border: 1px solid #555555;
            background-color: #2a2a2a;
            border-radius: 3px;
        }
        QCheckBox::indicator:checked {
            background-color: #4444ff;
            border-color: #5555ff;
        }
    """)
    enable_checkbox.setToolTip(
        'Enable PyQtGraph built-in downsampling for raw data visualization.\n'
        'Useful for displaying large raw datasets without performance issues.'
    )
    raw_display_layout.addWidget(enable_checkbox)
    
    # Mode selection
    raw_display_layout.addWidget(create_label_with_style('Mode:'))
    
    mode_combo = pg.QtWidgets.QComboBox()
    mode_combo.addItem('Subsample', 'subsample')
    mode_combo.addItem('Mean', 'mean')
    mode_combo.addItem('Peak', 'peak')
    
    # Set current mode
    mode_index = mode_combo.findData(mode)
    if mode_index >= 0:
        mode_combo.setCurrentIndex(mode_index)
    
    mode_combo.setStyleSheet(STYLES['dark_combobox'])
    mode_combo.setToolTip(
        'Downsampling mode:\n'
        '• Subsample: Fastest, selects every N-th sample\n'
        '• Mean: Computes mean of N samples (balanced)\n'
        '• Peak: Shows min/max envelope (best visual quality)'
    )
    raw_display_layout.addWidget(mode_combo)
    
    # Downsampling factor with slider + spinbox combo
    raw_display_layout.addWidget(create_label_with_style('Factor:'))
    
    factor_container, factor_slider, factor_spinbox = create_slider_spinbox_combo(
        1, 10000, factor, step=1,
        tooltip='Downsampling factor (1 = no downsampling, 2 = show every 2nd sample, etc.)\n'
                'Higher values improve performance but reduce detail.\n'
                'Note: Factor may be automatically increased to meet Max Points constraint.'
    )
    raw_display_layout.addWidget(factor_container)
    
    # Max points constraint
    raw_display_layout.addWidget(create_label_with_style('Max Points:'))
    
    max_points_spinbox = create_spinbox_with_style(
        1000, 100_000_000, max_points, step=1000,
        tooltip='Maximum number of downsampled points to display.\n'
                'Factor will be automatically adjusted if needed to meet this constraint.\n'
                'Helps maintain performance with large raw datasets.'
    )
    raw_display_layout.addWidget(max_points_spinbox)

    # Option: apply PyQtGraph downsampling to gated raw pulls as well
    gated_raw_downsample_checkbox = pg.QtWidgets.QCheckBox("Downsample Gated Raw")
    gated_raw_downsample_checkbox.setChecked(False)
    gated_raw_downsample_checkbox.setStyleSheet("""
        QCheckBox {
            color: white;
            font-size: 10px;
            padding: 1px;
        }
        QCheckBox::indicator {
            width: 14px;
            height: 14px;
        }
        QCheckBox::indicator:unchecked {
            background-color: #333333;
            border: 1px solid #666666;
        }
        QCheckBox::indicator:checked {
            background-color: #4CAF50;
            border: 1px solid #4CAF50;
        }
    """)
    gated_raw_downsample_checkbox.setToolTip(
        'If enabled, apply the same PyQtGraph downsampling settings to\n'
        'the gated (region-based) raw pull. When disabled, gated raw\n'
        'is shown at full resolution regardless of the global setting.'
    )
    raw_display_layout.addWidget(gated_raw_downsample_checkbox)
    
    # Option: enable/disable selection markers (LinearRegionItem)
    region_markers_checkbox = pg.QtWidgets.QCheckBox("Show Selection Markers")
    region_markers_checkbox.setChecked(True)  # Enabled by default
    region_markers_checkbox.setStyleSheet("""
        QCheckBox {
            color: white;
            font-size: 10px;
            padding: 1px;
        }
        QCheckBox::indicator {
            width: 14px;
            height: 14px;
        }
        QCheckBox::indicator:unchecked {
            background-color: #333333;
            border: 1px solid #666666;
        }
        QCheckBox::indicator:checked {
            background-color: #4CAF50;
            border: 1px solid #4CAF50;
        }
    """)
    region_markers_checkbox.setToolTip(
        'Show or hide the region selection markers (vertical lines) on the plot.\n'
        'When disabled, the selection region and readout are hidden.'
    )
    raw_display_layout.addWidget(region_markers_checkbox)
    
    # Connect enable checkbox to enable/disable other controls
    def toggle_controls(enabled_state):
        mode_combo.setEnabled(enabled_state)
        factor_slider.setEnabled(enabled_state)
        factor_spinbox.setEnabled(enabled_state)
        max_points_spinbox.setEnabled(enabled_state)
    
    enable_checkbox.toggled.connect(toggle_controls)
    toggle_controls(enabled)  # Initialize state
    
    return raw_display_group, enable_checkbox, mode_combo, factor_spinbox, max_points_spinbox, gated_raw_downsample_checkbox, region_markers_checkbox


def create_trigger_controls(psdk, current_pre_trigger_time, current_pre_trigger_units, 
                            current_post_trigger_time, current_post_trigger_units,
                            trigger_enabled=False, trigger_threshold_adc=50, 
                            hardware_adc_sample_rate=1000000):
    """
    Create trigger control widgets with all signal connections set up.
    Returns widgets in a dictionary for easy access and flexible layout arrangement.
    
    Args:
        psdk: PicoSDK module reference
        current_pre_trigger_time: Current pre-trigger time value
        current_pre_trigger_units: Current pre-trigger time units (psdk.TIME_UNIT)
        current_post_trigger_time: Current post-trigger time value
        current_post_trigger_units: Current post-trigger time units (psdk.TIME_UNIT)
        trigger_enabled: Whether trigger is enabled by default
        trigger_threshold_adc: Default trigger threshold in ADC counts
        hardware_adc_sample_rate: Current hardware ADC sample rate (Hz) for validation
    
    Returns:
        dict: Dictionary containing all trigger widgets and handlers:
            - 'enable_checkbox': QCheckBox for enabling/disabling trigger
            - 'threshold_container': Container widget with threshold spinbox
            - 'threshold_slider': Slider placeholder (for backward compatibility)
            - 'threshold_spinbox': QSpinBox for trigger threshold
            - 'direction_combo': QComboBox for trigger direction
            - 'units_combo': QComboBox for shared time units
            - 'pre_trigger_spinbox': QDoubleSpinBox for pre-trigger time
            - 'post_trigger_spinbox': QDoubleSpinBox for post-trigger time
            - 'pre_trigger_hint': QLabel hint for pre-trigger spinbox
            - 'post_trigger_hint': QLabel hint for post-trigger spinbox
            - 'enable_handler': Function to call when enable state changes (already connected)
    """
    
    # Trigger Enable/Disable
    trigger_enable_checkbox = pg.QtWidgets.QCheckBox("Enable")
    trigger_enable_checkbox.setStyleSheet("""
        QCheckBox {
            color: white;
            font-size: 11px;
            font-weight: bold;
            padding: 2px;
        }
        QCheckBox::indicator {
            width: 16px;
            height: 16px;
        }
        QCheckBox::indicator:unchecked {
            background-color: #333333;
            border: 1px solid #666666;
        }
        QCheckBox::indicator:checked {
            background-color: #4CAF50;
            border: 1px solid #4CAF50;
        }
    """)
    trigger_enable_checkbox.setChecked(trigger_enabled)
    trigger_enable_checkbox.setToolTip(
        'Enable or disable simple trigger on Channel A.\n'
        'When disabled, streaming runs continuously without triggering.'
    )
    
    # Trigger Threshold (ADC counts) with slider + spinbox combo
    threshold_container, threshold_slider, trigger_threshold_spinbox = create_slider_spinbox_combo(
        -128, 127, trigger_threshold_adc, step=1,
        tooltip='Trigger threshold in ADC counts.\n'
                'Range: -128 to +127 for 8-bit ADC.\n'
                '0 = trigger at zero crossing.\n'
                'Positive = trigger above zero.\n'
                'Negative = trigger below zero.'
    )
    trigger_threshold_spinbox.setEnabled(trigger_enabled)
    threshold_slider.setEnabled(trigger_enabled)
    
    # Trigger Direction
    trigger_direction_combo = pg.QtWidgets.QComboBox()
    trigger_direction_combo.addItem('Rising', 2)  # TRIGGER_DIR.RISING = 2
    trigger_direction_combo.addItem('Falling', 3)  # TRIGGER_DIR.FALLING = 3
    trigger_direction_combo.addItem('Rising or Falling', 4)  # TRIGGER_DIR.RISING_OR_FALLING = 4
    trigger_direction_combo.addItem('Above', 0)  # TRIGGER_DIR.ABOVE = 0
    trigger_direction_combo.addItem('Below', 1)  # TRIGGER_DIR.BELOW = 1
    trigger_direction_combo.setCurrentIndex(2)  # Default to "Rising or Falling"
    trigger_direction_combo.setToolTip(
        'Trigger direction:\n'
        '• Rising: Trigger on rising edge (signal crosses threshold going up)\n'
        '• Falling: Trigger on falling edge (signal crosses threshold going down)\n'
        '• Rising or Falling: Trigger on either edge\n'
        '• Above: Trigger when signal is above threshold\n'
        '• Below: Trigger when signal is below threshold'
    )
    trigger_direction_combo.setStyleSheet(STYLES['dark_combobox'])
    trigger_direction_combo.setEnabled(trigger_enabled)
    
    # Shared Units Selector (applies to both pre and post trigger times)
    trigger_units_combo = pg.QtWidgets.QComboBox()
    trigger_units_combo.addItem('ns', psdk.TIME_UNIT.NS)
    trigger_units_combo.addItem('μs', psdk.TIME_UNIT.US)
    trigger_units_combo.addItem('ms', psdk.TIME_UNIT.MS)
    trigger_units_combo.addItem('s', psdk.TIME_UNIT.S)
    
    # Determine initial units (use pre_trigger_units as default, or post if pre not set)
    initial_units = current_pre_trigger_units if current_pre_trigger_units else current_post_trigger_units
    if initial_units == psdk.TIME_UNIT.NS:
        trigger_units_combo.setCurrentText('ns')
    elif initial_units == psdk.TIME_UNIT.US:
        trigger_units_combo.setCurrentText('μs')
    elif initial_units == psdk.TIME_UNIT.MS:
        trigger_units_combo.setCurrentText('ms')
    else:
        trigger_units_combo.setCurrentText('s')
    
    trigger_units_combo.setStyleSheet(STYLES['dark_combobox'])
    trigger_units_combo.setEnabled(trigger_enabled)
    trigger_units_combo.setToolTip('Time units for both pre and post trigger times')
    
    # Helper function to convert time value from one unit to another
    def convert_time_value(value, from_unit, to_unit):
        """Convert time value from one unit to another."""
        # Conversion factors to seconds
        unit_to_seconds = {
            psdk.TIME_UNIT.NS: 1e-9,
            psdk.TIME_UNIT.US: 1e-6,
            psdk.TIME_UNIT.MS: 1e-3,
            psdk.TIME_UNIT.S: 1.0
        }
        if from_unit == to_unit:
            return value
        # Convert to seconds first, then to target unit
        seconds = value * unit_to_seconds.get(from_unit, 1.0)
        return seconds / unit_to_seconds.get(to_unit, 1.0)
    
    # Store current values in seconds for conversion
    unit_to_seconds = {
        psdk.TIME_UNIT.NS: 1e-9,
        psdk.TIME_UNIT.US: 1e-6,
        psdk.TIME_UNIT.MS: 1e-3,
        psdk.TIME_UNIT.S: 1.0
    }
    pre_trigger_seconds = current_pre_trigger_time * unit_to_seconds.get(current_pre_trigger_units, 1.0)
    post_trigger_seconds = current_post_trigger_time * unit_to_seconds.get(current_post_trigger_units, 1.0)
    
    # Function to update spinbox values when units change
    def on_units_changed():
        new_unit = trigger_units_combo.currentData()
        unit_to_seconds = {
            psdk.TIME_UNIT.NS: 1e-9,
            psdk.TIME_UNIT.US: 1e-6,
            psdk.TIME_UNIT.MS: 1e-3,
            psdk.TIME_UNIT.S: 1.0
        }
        # Convert from seconds to new unit
        new_unit_factor = unit_to_seconds.get(new_unit, 1.0)
        
        # Update pre-trigger value
        new_pre_value = pre_trigger_seconds / new_unit_factor
        pre_trigger_time_spinbox.blockSignals(True)
        pre_trigger_time_spinbox.setValue(new_pre_value)
        pre_trigger_time_spinbox.blockSignals(False)
        
        # Update post-trigger value
        new_post_value = post_trigger_seconds / new_unit_factor
        post_trigger_time_spinbox.blockSignals(True)
        post_trigger_time_spinbox.setValue(new_post_value)
        post_trigger_time_spinbox.blockSignals(False)
    
    # Function to update stored seconds when spinbox values change
    def on_pre_trigger_changed(value):
        nonlocal pre_trigger_seconds
        current_unit = trigger_units_combo.currentData()
        unit_to_seconds = {
            psdk.TIME_UNIT.NS: 1e-9,
            psdk.TIME_UNIT.US: 1e-6,
            psdk.TIME_UNIT.MS: 1e-3,
            psdk.TIME_UNIT.S: 1.0
        }
        pre_trigger_seconds = value * unit_to_seconds.get(current_unit, 1.0)
    
    def on_post_trigger_changed(value):
        nonlocal post_trigger_seconds
        current_unit = trigger_units_combo.currentData()
        unit_to_seconds = {
            psdk.TIME_UNIT.NS: 1e-9,
            psdk.TIME_UNIT.US: 1e-6,
            psdk.TIME_UNIT.MS: 1e-3,
            psdk.TIME_UNIT.S: 1.0
        }
        post_trigger_seconds = value * unit_to_seconds.get(current_unit, 1.0)
    
    trigger_units_combo.currentIndexChanged.connect(on_units_changed)
    
    # Pre Trigger Time
    pre_trigger_time_spinbox = pg.QtWidgets.QDoubleSpinBox()
    pre_trigger_time_spinbox.setRange(0.0, 1e9)  # Large range to accommodate different units
    pre_trigger_time_spinbox.setSingleStep(0.1)
    pre_trigger_time_spinbox.setDecimals(3)
    
    # Set initial value in the selected units
    initial_unit = trigger_units_combo.currentData()
    unit_to_seconds_init = {
        psdk.TIME_UNIT.NS: 1e-9,
        psdk.TIME_UNIT.US: 1e-6,
        psdk.TIME_UNIT.MS: 1e-3,
        psdk.TIME_UNIT.S: 1.0
    }
    initial_pre_value = pre_trigger_seconds / unit_to_seconds_init.get(initial_unit, 1.0)
    pre_trigger_time_spinbox.setValue(initial_pre_value)
    
    # Enable scroll wheel adjustment when focused
    pre_trigger_time_spinbox.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
    # Modern styling: no buttons, no frame
    ButtonSymbols = pg.QtWidgets.QAbstractSpinBox.ButtonSymbols
    pre_trigger_time_spinbox.setButtonSymbols(ButtonSymbols.NoButtons)
    pre_trigger_time_spinbox.setFrame(False)
    
    # Enhanced tooltip with scroll wheel instructions
    scroll_hint = "Hover and scroll to adjust • Ctrl+scroll for faster"
    pre_trigger_time_spinbox.setToolTip(
        'Time BEFORE trigger event.\n'
        'Captures data leading up to the trigger.\n'
        '0 = no pre-trigger (start capture at trigger).\n\n'
        f'{scroll_hint}'
    )
    pre_trigger_time_spinbox.setStyleSheet(STYLES['dark_double_spinbox'])
    pre_trigger_time_spinbox.setEnabled(trigger_enabled)
    pre_trigger_time_spinbox.valueChanged.connect(on_pre_trigger_changed)
    pre_hint_label = make_scroll_hint_label()
    
    # Post Trigger Time
    post_trigger_time_spinbox = pg.QtWidgets.QDoubleSpinBox()
    # Calculate max time based on buffer size and sample rate
    # max_time = (buffer_size - 1) / sample_rate (in seconds)
    # For safety, use a reasonable upper limit
    max_time_seconds = (hardware_adc_sample_rate * 10) if hardware_adc_sample_rate > 0 else 1e6
    post_trigger_time_spinbox.setRange(0.0, max_time_seconds)
    post_trigger_time_spinbox.setSingleStep(0.1)
    post_trigger_time_spinbox.setDecimals(3)
    
    # Set initial value in the selected units
    initial_post_value = post_trigger_seconds / unit_to_seconds_init.get(initial_unit, 1.0)
    post_trigger_time_spinbox.setValue(initial_post_value)
    
    # Enable scroll wheel adjustment when focused
    post_trigger_time_spinbox.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
    # Modern styling: no buttons, no frame
    ButtonSymbols = pg.QtWidgets.QAbstractSpinBox.ButtonSymbols
    post_trigger_time_spinbox.setButtonSymbols(ButtonSymbols.NoButtons)
    post_trigger_time_spinbox.setFrame(False)
    
    # Enhanced tooltip with scroll wheel instructions
    post_trigger_time_spinbox.setToolTip(
        f'Time AFTER trigger event.\n'
        f'Captures data following the trigger.\n'
        f'Must be less than buffer capacity.\n\n'
        f'{scroll_hint}'
    )
    post_trigger_time_spinbox.setStyleSheet(STYLES['dark_double_spinbox'])
    post_trigger_time_spinbox.setEnabled(trigger_enabled)
    post_trigger_time_spinbox.valueChanged.connect(on_post_trigger_changed)
    post_hint_label = make_scroll_hint_label()
    
    # Connect checkbox to enable/disable controls
    def on_trigger_enable_changed(state):
        enabled = (state == 2)  # Qt.Checked = 2
        threshold_slider.setEnabled(enabled)
        trigger_threshold_spinbox.setEnabled(enabled)
        trigger_direction_combo.setEnabled(enabled)
        trigger_units_combo.setEnabled(enabled)
        pre_trigger_time_spinbox.setEnabled(enabled)
        post_trigger_time_spinbox.setEnabled(enabled)
    
    trigger_enable_checkbox.stateChanged.connect(on_trigger_enable_changed)
    
    # Return all widgets in a dictionary for easy access and flexible layout
    return {
        'enable_checkbox': trigger_enable_checkbox,
        'threshold_container': threshold_container,
        'threshold_slider': threshold_slider,
        'threshold_spinbox': trigger_threshold_spinbox,
        'direction_combo': trigger_direction_combo,
        'units_combo': trigger_units_combo,
        'pre_trigger_spinbox': pre_trigger_time_spinbox,
        'post_trigger_spinbox': post_trigger_time_spinbox,
        'pre_trigger_hint': pre_hint_label,
        'post_trigger_hint': post_hint_label,
        'enable_handler': on_trigger_enable_changed  # Already connected, but available for reference
    }


def create_periodic_logging_controls(default_log_file="", default_log_rate=1.0):
    """
    Create the periodic logging controls group for hardware downsampled values.
    
    Args:
        default_log_file: Default log file path (empty string = no default)
        default_log_rate: Default log rate in seconds (how often to write)
    
    Returns:
        tuple: (group_widget, file_path_edit, browse_button, log_rate_spinbox)
    """
    logging_group, logging_layout = create_group_widget("Periodic Logging (HW DS)")
    
    # File path selection row
    file_row = pg.QtWidgets.QHBoxLayout()
    file_row.setSpacing(4)
    file_row.addWidget(create_label_with_style('Log File:'))
    
    # File path line edit
    file_path_edit = pg.QtWidgets.QLineEdit()
    file_path_edit.setText(default_log_file)
    file_path_edit.setPlaceholderText("Select log file location...")
    file_path_edit.setStyleSheet(f"""
        QLineEdit {{{BASE_WIDGET_STYLE}}}
        QLineEdit:hover {{{BASE_WIDGET_HOVER}}}
    """)
    file_path_edit.setToolTip('Path to the log file where downsampled values will be written')
    file_row.addWidget(file_path_edit)
    
    # Browse button
    browse_button = pg.QtWidgets.QPushButton('Browse...')
    browse_button.setStyleSheet(STYLES['secondary_button'])
    browse_button.setToolTip('Browse for log file location')
    browse_button.setMaximumWidth(80)
    file_row.addWidget(browse_button)
    
    file_row.addStretch()
    logging_layout.addLayout(file_row)
    
    # Log rate control
    logging_layout.addWidget(create_label_with_style('Log Rate:'))
    
    log_rate_spinbox = create_double_spinbox_with_style(
        0.01, 3600.0, default_log_rate,  # 0.01s to 1 hour
        decimals=2, step=0.1, suffix=' s',
        tooltip='How often to write downsampled values to the log file.\n'
                'Lower values = more frequent writes (higher disk I/O).\n'
                'Higher values = less frequent writes (lower disk I/O).'
    )
    logging_layout.addWidget(log_rate_spinbox)
    
    return logging_group, file_path_edit, browse_button, log_rate_spinbox


def create_action_buttons():
    """
    Create the action buttons (Apply, Stop, and Plot Gated Raw) in a horizontal layout.
    
    Returns:
        tuple: (button_container, apply_button, stop_button, pull_region_raw_button)
    """
    # Create container widget for horizontal button layout
    button_container = pg.QtWidgets.QWidget()
    button_layout = pg.QtWidgets.QHBoxLayout()
    button_container.setLayout(button_layout)
    button_layout.setSpacing(6)
    button_layout.setContentsMargins(0, 4, 0, 0)
    
    apply_button = pg.QtWidgets.QPushButton('Apply')
    apply_button.setObjectName('applyButton')
    apply_button.setStyleSheet(STYLES['primary_button'])
    apply_button.setToolTip('Apply changes to streaming settings')
    
    stop_button = pg.QtWidgets.QPushButton('Stop')
    stop_button.setObjectName('stopButton')
    stop_button.setStyleSheet(STYLES['stop_button'])
    stop_button.setToolTip('Stop/Restart streaming')

    pull_region_raw_button = pg.QtWidgets.QPushButton('Plot Gated Raw')
    pull_region_raw_button.setStyleSheet(STYLES['secondary_button'])
    pull_region_raw_button.setToolTip('Plot only the portion of raw data that corresponds to the current selection region (gated raw)')
    pull_region_raw_button.setEnabled(False)  # Enabled after raw data has been pulled
    
    button_layout.addWidget(apply_button)
    button_layout.addWidget(stop_button)
    button_layout.addWidget(pull_region_raw_button)
    
    return button_container, apply_button, stop_button, pull_region_raw_button


def build_control_panel(config):
    """
    Build the complete control panel with all control groups.
    
    Args:
        config: Dictionary containing current configuration values:
            - psdk: PicoSDK module reference
            - DOWNSAMPLING_RATIO: Current ratio
            - DOWNSAMPLING_MODE: Current mode
            - sample_interval: Current interval
            - time_units: Current time units
            - SAMPLES_PER_BUFFER: Current buffer size
            - REFRESH_FPS: Current refresh rate
            - POLLING_INTERVAL: Current polling interval
            - TARGET_TIME_WINDOW: Current time window
            - PRE_TRIGGER_TIME: Pre-trigger time value
            - PRE_TRIGGER_TIME_UNITS: Pre-trigger time units
            - POST_TRIGGER_TIME: Post-trigger time value
            - POST_TRIGGER_TIME_UNITS: Post-trigger time units
            - hardware_adc_sample_rate: Hardware ADC sample rate (Hz)
            - RAW_DATA_DOWNSAMPLE_ENABLED: Enable PyQtGraph downsampling (default: False)
            - RAW_DATA_DOWNSAMPLE_MODE: Downsampling mode ('subsample', 'mean', 'peak', default: 'mean')
            - RAW_DATA_DOWNSAMPLE_FACTOR: Downsampling factor (default: 1)
    
    Returns:
        dict: Dictionary containing all created widgets:
            - 'panel': The main control panel widget
            - 'mode_combo': Downsampling mode combobox
            - 'ratio_spinbox': Downsampling ratio spinbox
            - 'interval_spinbox': Sample interval spinbox
            - 'units_combo': Time units combobox
            - 'hw_buffer_spinbox': Hardware buffer size spinbox
            - 'refresh_spinbox': refresh rate spinbox
            - 'poll_spinbox': Polling interval spinbox
            - 'time_window_spinbox': Time window spinbox
            - 'raw_display_enable_checkbox': Enable PyQtGraph downsampling checkbox
            - 'raw_display_mode_combo': Raw data downsampling mode combobox
            - 'raw_display_factor_spinbox': Raw data downsampling factor spinbox
            - 'raw_display_max_points_spinbox': Maximum points constraint spinbox
            - 'gated_raw_downsample_checkbox': Downsample gated raw checkbox
            - 'region_markers_checkbox': Show selection markers checkbox
            - 'pre_trigger_time_spinbox': Pre-trigger time spinbox
            - 'trigger_units_combo': Shared units combobox (applies to both pre and post trigger times)
            - 'post_trigger_time_spinbox': Post-trigger time spinbox
            - 'apply_button': Apply changes button
            - 'stop_button': Stop/restart button
    """
    # Create control panel container
    controls_panel = pg.QtWidgets.QWidget()
    controls_panel.setObjectName('controlPanel')
    # Scoped stylesheet for control panel to ensure consistent styling
    controls_panel.setStyleSheet("""
        #controlPanel {
            font-size: 9pt;
            background-color: #1a1a1a;
        }
        #controlPanel QLabel {
            font-size: 9pt;
        }
        /* Global tooltip styling for readable white text on dark background */
        QToolTip {
            background-color: #2b2b2b;
            color: white;
            border: 1px solid #555555;
            padding: 4px 8px;
            font-size: 9pt;
        }
        /* Ensure all text in control panel is readable */
        #controlPanel * {
            color: white;
        }
        /* Checkbox text styling */
        #controlPanel QCheckBox {
            color: white;
        }
    """)
    controls_layout = pg.QtWidgets.QVBoxLayout()
    controls_panel.setLayout(controls_layout)
    controls_panel.setMinimumWidth(320)
    # No maximum width - let it size to content
    controls_layout.setSpacing(10)  # More spacing between cards for better visual separation
    controls_layout.setContentsMargins(8, 8, 8, 8)  # Padding around entire panel
    
    # Helper function to create a collapsible card widget
    def create_collapsible_card_widget(title_text, default_expanded=True):
        """
        Create a collapsible card widget with expand/collapse functionality.
        
        Args:
            title_text: Title text for the card
            default_expanded: Whether the card should be expanded by default
        
        Returns:
            tuple: (card_widget, card_content_layout, toggle_function)
                - card_widget: The main card container
                - card_content_layout: Layout for card content (collapsible)
                - toggle_function: Function to toggle expand/collapse state
        """
        card_border = 1
        card_padding = 7
        card_radius = card_border + card_padding  # radius = 8px
        
        # Main card container
        card = pg.QtWidgets.QWidget()
        card.setStyleSheet(f"""
            QWidget {{
                background-color: #252525;
                border: {card_border}px solid #444444;
                border-radius: {card_radius}px;
            }}
        """)
        card_main_layout = pg.QtWidgets.QVBoxLayout()
        card.setLayout(card_main_layout)
        card_main_layout.setSpacing(4)
        card_main_layout.setContentsMargins(card_padding, card_padding, card_padding, card_padding)
        
        # Title row with expand/collapse button
        title_row = pg.QtWidgets.QHBoxLayout()
        title_row.setSpacing(6)
        title_row.setContentsMargins(0, 0, 0, 0)
        
        # Expand/collapse button (arrow icon)
        expand_button = pg.QtWidgets.QPushButton()
        expand_button.setObjectName('expandButton')
        expand_button.setFixedSize(20, 20)
        expand_button.setStyleSheet("""
            QPushButton#expandButton {
                background-color: transparent;
                border: none;
                color: #ffffff;
                font-size: 12px;
                font-weight: bold;
                padding: 0px;
                margin: 0px;
            }
            QPushButton#expandButton:hover {
                background-color: #333333;
                border-radius: 3px;
            }
        """)
        
        # Title label (clickable)
        title_label = pg.QtWidgets.QLabel(title_text)
        title_label.setStyleSheet("""
            QLabel {
                font-weight: 600;
                font-size: 9pt;
                color: #ffffff;
                padding: 0px;
                margin: 0px;
                border: none;
                background-color: transparent;
            }
        """)
        title_label.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        
        # Make title clickable
        def on_title_clicked():
            expand_button.click()
        
        title_label.mousePressEvent = lambda e: on_title_clicked()
        
        title_row.addWidget(expand_button)
        title_row.addWidget(title_label)
        title_row.addStretch()
        
        card_main_layout.addLayout(title_row)
        
        # Content container (collapsible)
        content_widget = pg.QtWidgets.QWidget()
        content_layout = pg.QtWidgets.QVBoxLayout()
        content_widget.setLayout(content_layout)
        content_layout.setSpacing(4)
        content_layout.setContentsMargins(0, 4, 0, 0)
        
        card_main_layout.addWidget(content_widget)
        
        # State tracking
        is_expanded = default_expanded
        
        # Update arrow icon based on state
        def update_arrow():
            if is_expanded:
                expand_button.setText('▼')  # Down arrow (expanded)
            else:
                expand_button.setText('▶')  # Right arrow (collapsed)
        
        # Toggle function
        def toggle_expand():
            nonlocal is_expanded
            is_expanded = not is_expanded
            content_widget.setVisible(is_expanded)
            update_arrow()
        
        # Initialize state
        content_widget.setVisible(is_expanded)
        update_arrow()
        
        # Connect button
        expand_button.clicked.connect(toggle_expand)
        
        return card, content_layout, toggle_expand
    
    # Channel & Signal Generator Settings Card (Card 1 - Top card, setup phase)
    hw_settings_card, hw_settings_card_layout, _ = create_collapsible_card_widget("Channel & Signal Generator", default_expanded=True)
    
    # Import pypicosdk for constants
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'pyPicoSDK_Playground'))
    import pypicosdk as psdk
    
    # Channel Settings Section
    hw_settings_card_layout.addWidget(create_label_with_style('Channel Settings:'))
    
    # Channel Range
    channel_range_row = pg.QtWidgets.QHBoxLayout()
    channel_range_row.setSpacing(4)
    channel_range_row.addWidget(create_label_with_style('Range:'))
    
    channel_range_combo = pg.QtWidgets.QComboBox()
    channel_range_combo.setStyleSheet(STYLES['dark_combobox'])
    # Add range options
    range_options = [
        ('10 mV', psdk.RANGE.mV10),
        ('20 mV', psdk.RANGE.mV20),
        ('50 mV', psdk.RANGE.mV50),
        ('100 mV', psdk.RANGE.mV100),
        ('200 mV', psdk.RANGE.mV200),
        ('500 mV', psdk.RANGE.mV500),
        ('1 V', psdk.RANGE.V1),
        ('2 V', psdk.RANGE.V2),
        ('5 V', psdk.RANGE.V5),
        ('10 V', psdk.RANGE.V10),
        ('20 V', psdk.RANGE.V20),
    ]
    for label, value in range_options:
        channel_range_combo.addItem(label, value)
    # Set default to mV500 (current default in main script)
    default_range_idx = next((i for i, (_, val) in enumerate(range_options) if val == psdk.RANGE.mV500), 5)
    channel_range_combo.setCurrentIndex(default_range_idx)
    channel_range_combo.setToolTip('Voltage range for channel A')
    channel_range_row.addWidget(channel_range_combo)
    channel_range_row.addStretch()
    hw_settings_card_layout.addLayout(channel_range_row)
    
    # Channel Coupling
    channel_coupling_row = pg.QtWidgets.QHBoxLayout()
    channel_coupling_row.setSpacing(4)
    channel_coupling_row.addWidget(create_label_with_style('Coupling:'))
    
    channel_coupling_combo = pg.QtWidgets.QComboBox()
    channel_coupling_combo.setStyleSheet(STYLES['dark_combobox'])
    # Add coupling options
    coupling_options = [
        ('AC', psdk.COUPLING.AC),
        ('DC', psdk.COUPLING.DC),
        ('DC 50Ω', psdk.COUPLING.DC_50OHM),
    ]
    for label, value in coupling_options:
        channel_coupling_combo.addItem(label, value)
    # Set default to match INITIAL_CONFIG['channel_coupling'] from main script
    default_coupling = config.get('channel_coupling', psdk.COUPLING.AC)
    default_coupling_idx = next((i for i, (_, val) in enumerate(coupling_options) if val == default_coupling), 0)
    channel_coupling_combo.setCurrentIndex(default_coupling_idx)
    channel_coupling_combo.setToolTip('Coupling mode for channel A (AC, DC, or DC 50Ω)')
    channel_coupling_row.addWidget(channel_coupling_combo)
    channel_coupling_row.addStretch()
    hw_settings_card_layout.addLayout(channel_coupling_row)
    
    # Channel Probe Scale
    channel_probe_row = pg.QtWidgets.QHBoxLayout()
    channel_probe_row.setSpacing(4)
    channel_probe_row.addWidget(create_label_with_style('Probe Scale:'))
    
    channel_probe_combo = pg.QtWidgets.QComboBox()
    channel_probe_combo.setStyleSheet(STYLES['dark_combobox'])
    # Add probe scale options
    probe_options = [
        ('x1', 1.0),
        ('x2', 2.0),
        ('x5', 5.0),
        ('x10', 10.0),
        ('x20', 20.0),
        ('x50', 50.0),
        ('x100', 100.0),
        ('x200', 200.0),
        ('x500', 500.0),
        ('x1000', 1000.0),
    ]
    for label, value in probe_options:
        channel_probe_combo.addItem(label, value)
    # Set default to x1 (1.0)
    channel_probe_combo.setCurrentIndex(0)
    channel_probe_combo.setToolTip('Probe attenuation factor (e.g., x10 for 10:1 probe)')
    channel_probe_row.addWidget(channel_probe_combo)
    channel_probe_row.addStretch()
    hw_settings_card_layout.addLayout(channel_probe_row)
    
    # Separator
    hw_settings_card_layout.addWidget(create_separator())
    
    # Signal Generator Settings Section
    hw_settings_card_layout.addWidget(create_label_with_style('Signal Generator Settings:'))
    
    # Sig Gen Frequency
    siggen_freq_row = pg.QtWidgets.QHBoxLayout()
    siggen_freq_row.setSpacing(4)
    siggen_freq_row.addWidget(create_label_with_style('Frequency:'))
    
    siggen_freq_spinbox = create_double_spinbox_with_style(
        0.001, 100_000_000.0, config.get('SIGGEN_FREQUENCY', 1.0),  # 0.001 Hz to 100 MHz
        decimals=3, step=1.0, suffix=' Hz',
        tooltip='Signal generator frequency in Hz'
    )
    siggen_freq_row.addWidget(siggen_freq_spinbox)
    siggen_freq_row.addStretch()
    hw_settings_card_layout.addLayout(siggen_freq_row)
    
    # Sig Gen Peak-to-Peak
    siggen_pk2pk_row = pg.QtWidgets.QHBoxLayout()
    siggen_pk2pk_row.setSpacing(4)
    siggen_pk2pk_row.addWidget(create_label_with_style('Peak-to-Peak:'))
    
    siggen_pk2pk_spinbox = create_double_spinbox_with_style(
        0.0, 5.0, config.get('SIGGEN_PK2PK', 0.95),  # 0 to 5 V
        decimals=3, step=0.01, suffix=' V',
        tooltip='Signal generator peak-to-peak voltage in volts'
    )
    siggen_pk2pk_row.addWidget(siggen_pk2pk_spinbox)
    siggen_pk2pk_row.addStretch()
    hw_settings_card_layout.addLayout(siggen_pk2pk_row)
    
    # Sig Gen Wave Type
    siggen_wave_row = pg.QtWidgets.QHBoxLayout()
    siggen_wave_row.setSpacing(4)
    siggen_wave_row.addWidget(create_label_with_style('Wave Type:'))
    
    siggen_wave_combo = pg.QtWidgets.QComboBox()
    siggen_wave_combo.setStyleSheet(STYLES['dark_combobox'])
    # Add waveform options
    waveform_options = [
        ('Sine', psdk.WAVEFORM.SINE),
        ('Square', psdk.WAVEFORM.SQUARE),
        ('Triangle', psdk.WAVEFORM.TRIANGLE),
        ('Ramp Up', psdk.WAVEFORM.RAMP_UP),
        ('Ramp Down', psdk.WAVEFORM.RAMP_DOWN),
        ('Sinc', psdk.WAVEFORM.SINC),
        ('Gaussian', psdk.WAVEFORM.GAUSSIAN),
        ('Half Sine', psdk.WAVEFORM.HALF_SINE),
        ('DC Voltage', psdk.WAVEFORM.DC_VOLTAGE),
        ('PWM', psdk.WAVEFORM.PWM),
        ('White Noise', psdk.WAVEFORM.WHITENOISE),
        ('PRBS', psdk.WAVEFORM.PRBS),
    ]
    for label, value in waveform_options:
        siggen_wave_combo.addItem(label, value)
    # Set default to SINE (current default in main script)
    default_wave_idx = next((i for i, (_, val) in enumerate(waveform_options) if val == psdk.WAVEFORM.SINE), 0)
    siggen_wave_combo.setCurrentIndex(default_wave_idx)
    siggen_wave_combo.setToolTip('Signal generator waveform type')
    siggen_wave_row.addWidget(siggen_wave_combo)
    siggen_wave_row.addStretch()
    hw_settings_card_layout.addLayout(siggen_wave_row)
    
    controls_layout.addWidget(hw_settings_card)
    
    # HW Device Settings Card (Card 2 - Core acquisition settings)
    acquisition_card, acquisition_card_layout, _ = create_collapsible_card_widget("HW Device Settings", default_expanded=True)
    
    # Create all control groups
    downsample_group, mode_combo, ratio_spinbox = create_downsampling_controls(
        config['psdk'],
        config['DOWNSAMPLING_RATIO'],
        config['DOWNSAMPLING_MODE']
    )
    acquisition_card_layout.addWidget(downsample_group)
    
    interval_group, interval_spinbox, units_combo = create_interval_controls(
        config['psdk'],
        config['sample_interval'],
        config['time_units']
    )
    acquisition_card_layout.addWidget(interval_group)
    
    hw_buffer_group, hw_buffer_spinbox = create_buffer_controls(
        config['SAMPLES_PER_BUFFER']
    )
    acquisition_card_layout.addWidget(hw_buffer_group)
    
    controls_layout.addWidget(acquisition_card)
    
    # Performance Card (Card 6 - Frequently Adjusted, collapsed by default, moved to bottom)
    performance_card, performance_card_layout, _ = create_collapsible_card_widget("Performance", default_expanded=False)
    
    # Display rate and poll interval on same row
    perf_row1 = pg.QtWidgets.QHBoxLayout()
    perf_row1.setSpacing(4)
    
    perf_row1.addWidget(create_label_with_style('Display Rate:'))
    refresh_spinbox = create_spinbox_with_style(
        1, 120, config['REFRESH_FPS'],
        tooltip='How often the plot updates (higher = smoother but more CPU)'
    )
    refresh_spinbox.setSuffix(' FPS')
    perf_row1.addWidget(refresh_spinbox)
    
    perf_row1.addSpacing(8)
    
    perf_row1.addWidget(create_label_with_style('Poll Interval:'))
    poll_spinbox = create_double_spinbox_with_style(
        0.01, 100.0, config['POLLING_INTERVAL'] * 1000,  # Convert seconds to ms
        decimals=2, step=0.1, suffix=' ms',
        tooltip='How often to check hardware for new data (lower = less latency)'
    )
    perf_row1.addWidget(poll_spinbox)
    perf_row1.addStretch()
    
    performance_card_layout.addLayout(perf_row1)
    
    # Time span control - use helper function
    time_span_row = pg.QtWidgets.QHBoxLayout()
    time_span_row.setSpacing(4)
    time_span_row.addWidget(create_label_with_style('Time Span:'))
    
    time_window_spinbox, hint_label = create_time_window_spinbox(config['TARGET_TIME_WINDOW'])
    time_span_row.addWidget(time_window_spinbox)
    time_span_row.addWidget(hint_label)
    time_span_row.addStretch()
    
    performance_card_layout.addLayout(time_span_row)
    
    # Trigger Card (Card 4 - Important but not always used)
    trigger_card, trigger_card_layout, _ = create_collapsible_card_widget("Trigger", default_expanded=True)
    
    # Create all trigger widgets using the builder function
    trigger_widgets = create_trigger_controls(
        config['psdk'],
        config.get('PRE_TRIGGER_TIME', 0.0),
        config.get('PRE_TRIGGER_TIME_UNITS', config['psdk'].TIME_UNIT.MS),
        config.get('POST_TRIGGER_TIME', 1.0),
        config.get('POST_TRIGGER_TIME_UNITS', config['psdk'].TIME_UNIT.MS),
        trigger_enabled=config.get('TRIGGER_ENABLED', False),
        trigger_threshold_adc=config.get('TRIGGER_THRESHOLD_ADC', 50),
        hardware_adc_sample_rate=config.get('hardware_adc_sample_rate', 1000000)
    )
    
    # Arrange widgets in card layout
    # Enable and threshold on same row
    trigger_row1 = pg.QtWidgets.QHBoxLayout()
    trigger_row1.setSpacing(4)
    trigger_row1.addWidget(trigger_widgets['enable_checkbox'])
    trigger_row1.addSpacing(8)
    trigger_row1.addWidget(create_label_with_style('Threshold (ADC):'))
    trigger_row1.addWidget(trigger_widgets['threshold_container'])
    trigger_row1.addStretch()
    trigger_card_layout.addLayout(trigger_row1)
    
    # Direction and units on same row
    trigger_row2 = pg.QtWidgets.QHBoxLayout()
    trigger_row2.setSpacing(4)
    trigger_row2.addWidget(create_label_with_style('Direction:'))
    trigger_row2.addWidget(trigger_widgets['direction_combo'])
    trigger_row2.addSpacing(8)
    trigger_row2.addWidget(create_label_with_style('Time Units:'))
    trigger_row2.addWidget(trigger_widgets['units_combo'])
    trigger_row2.addStretch()
    trigger_card_layout.addLayout(trigger_row2)
    
    # Pre and Post trigger time side by side
    trigger_time_row = pg.QtWidgets.QHBoxLayout()
    trigger_time_row.setSpacing(4)
    
    # Pre trigger time
    trigger_time_row.addWidget(create_label_with_style('Pre Trigger Time:'))
    trigger_time_row.addWidget(trigger_widgets['pre_trigger_spinbox'])
    trigger_time_row.addWidget(trigger_widgets['pre_trigger_hint'])
    
    trigger_time_row.addSpacing(8)
    
    # Post trigger time
    trigger_time_row.addWidget(create_label_with_style('Post Trigger Time:'))
    trigger_time_row.addWidget(trigger_widgets['post_trigger_spinbox'])
    trigger_time_row.addWidget(trigger_widgets['post_trigger_hint'])
    
    trigger_time_row.addStretch()
    trigger_card_layout.addLayout(trigger_time_row)
    
    controls_layout.addWidget(trigger_card)
    
    # Raw Data Display Card (Card 7 - Less frequently changed, moved to bottom)
    raw_display_card, raw_display_card_layout, _ = create_collapsible_card_widget("Raw Data Display", default_expanded=False)
    
    # Enable checkbox
    raw_display_enable_checkbox = pg.QtWidgets.QCheckBox("Enable PyQtGraph Downsampling")
    raw_display_enable_checkbox.setChecked(config.get('RAW_DATA_DOWNSAMPLE_ENABLED', True))
    raw_display_enable_checkbox.setStyleSheet("""
        QCheckBox {
            color: white;
            font-size: 11px;
            padding: 2px;
        }
        QCheckBox::indicator {
            width: 14px;
            height: 14px;
            border: 1px solid #555555;
            background-color: #2a2a2a;
            border-radius: 3px;
        }
        QCheckBox::indicator:checked {
            background-color: #4444ff;
            border-color: #5555ff;
        }
    """)
    raw_display_enable_checkbox.setToolTip(
        'Enable PyQtGraph built-in downsampling for raw data visualization.\n'
        'Useful for displaying large raw datasets without performance issues.'
    )
    
    # Mode combo
    raw_display_mode_combo = pg.QtWidgets.QComboBox()
    raw_display_mode_combo.addItem('Subsample', 'subsample')
    raw_display_mode_combo.addItem('Mean', 'mean')
    raw_display_mode_combo.addItem('Peak', 'peak')
    mode_index = raw_display_mode_combo.findData(config.get('RAW_DATA_DOWNSAMPLE_MODE', 'subsample'))
    if mode_index >= 0:
        raw_display_mode_combo.setCurrentIndex(mode_index)
    raw_display_mode_combo.setStyleSheet(STYLES['dark_combobox'])
    raw_display_mode_combo.setToolTip(
        'Downsampling mode:\n'
        '• Subsample: Fastest, selects every N-th sample\n'
        '• Mean: Computes mean of N samples (balanced)\n'
        '• Peak: Shows min/max envelope (best visual quality)'
    )
    
    # Factor spinbox
    factor_container, factor_slider, raw_display_factor_spinbox = create_slider_spinbox_combo(
        1, 10000, config.get('RAW_DATA_DOWNSAMPLE_FACTOR', 100), step=1,
        tooltip='Downsampling factor (1 = no downsampling, 2 = show every 2nd sample, etc.)\n'
                'Higher values improve performance but reduce detail.\n'
                'Note: Factor may be automatically increased to meet Max Points constraint.'
    )
    
    # Max points spinbox
    raw_display_max_points_spinbox = create_spinbox_with_style(
        1000, 100_000_000, config.get('RAW_DATA_MAX_POINTS', 500_000), step=1000,
        tooltip='Maximum number of downsampled points to display.\n'
                'Factor will be automatically adjusted if needed to meet this constraint.\n'
                'Helps maintain performance with large raw datasets.'
    )
    
    # Enable and mode on same row
    raw_row1 = pg.QtWidgets.QHBoxLayout()
    raw_row1.setSpacing(4)
    raw_row1.addWidget(raw_display_enable_checkbox)
    raw_row1.addSpacing(8)
    raw_row1.addWidget(create_label_with_style('Mode:'))
    raw_row1.addWidget(raw_display_mode_combo)
    raw_row1.addStretch()
    
    raw_display_card_layout.addLayout(raw_row1)
    
    # Factor and max points on same row
    raw_row2 = pg.QtWidgets.QHBoxLayout()
    raw_row2.setSpacing(4)
    raw_row2.addWidget(create_label_with_style('Factor:'))
    raw_row2.addWidget(factor_container)
    raw_row2.addSpacing(8)
    raw_row2.addWidget(create_label_with_style('Max Points:'))
    raw_row2.addWidget(raw_display_max_points_spinbox)
    raw_row2.addStretch()
    
    raw_display_card_layout.addLayout(raw_row2)
    
    # Enable/disable handler
    def toggle_raw_controls(enabled_state):
        raw_display_mode_combo.setEnabled(enabled_state)
        factor_slider.setEnabled(enabled_state)
        raw_display_factor_spinbox.setEnabled(enabled_state)
        raw_display_max_points_spinbox.setEnabled(enabled_state)
    
    raw_display_enable_checkbox.toggled.connect(toggle_raw_controls)
    toggle_raw_controls(config.get('RAW_DATA_DOWNSAMPLE_ENABLED', True))
    
    # Gated raw controls (moved from separate card)
    gated_row = pg.QtWidgets.QHBoxLayout()
    gated_row.setSpacing(4)
    
    # Gated raw downsampling checkbox
    gated_raw_downsample_checkbox = pg.QtWidgets.QCheckBox("Downsample Gated Raw")
    gated_raw_downsample_checkbox.setChecked(False)
    gated_raw_downsample_checkbox.setStyleSheet("""
        QCheckBox {
            color: white;
            font-size: 10px;
            padding: 1px;
        }
        QCheckBox::indicator {
            width: 14px;
            height: 14px;
        }
        QCheckBox::indicator:unchecked {
            background-color: #333333;
            border: 1px solid #666666;
        }
        QCheckBox::indicator:checked {
            background-color: #4CAF50;
            border: 1px solid #4CAF50;
        }
    """)
    gated_raw_downsample_checkbox.setToolTip(
        'If enabled, apply the same PyQtGraph downsampling settings to\n'
        'the gated (region-based) raw pull. When disabled, gated raw\n'
        'is shown at full resolution regardless of the global setting.'
    )
    
    # Region markers checkbox
    region_markers_checkbox = pg.QtWidgets.QCheckBox("Show Selection Markers")
    region_markers_checkbox.setChecked(True)
    region_markers_checkbox.setStyleSheet("""
        QCheckBox {
            color: white;
            font-size: 10px;
            padding: 1px;
        }
        QCheckBox::indicator {
            width: 14px;
            height: 14px;
        }
        QCheckBox::indicator:unchecked {
            background-color: #333333;
            border: 1px solid #666666;
        }
        QCheckBox::indicator:checked {
            background-color: #4CAF50;
            border: 1px solid #4CAF50;
        }
    """)
    region_markers_checkbox.setToolTip(
        'Show or hide the region selection markers (vertical lines) on the plot.\n'
        'When disabled, the selection region and readout are hidden.'
    )
    
    gated_row.addWidget(gated_raw_downsample_checkbox)
    gated_row.addSpacing(8)
    gated_row.addWidget(region_markers_checkbox)
    gated_row.addStretch()
    
    raw_display_card_layout.addLayout(gated_row)
    
    # Periodic Logging Card (Card 6 - Optional/Advanced, expanded by default)
    logging_card, logging_card_layout, _ = create_collapsible_card_widget("Periodic Logging (HW DS)", default_expanded=True)
    
    # Enable checkbox
    periodic_log_enable_checkbox = pg.QtWidgets.QCheckBox("Enable Periodic Logging")
    periodic_log_enable_checkbox.setChecked(config.get('PERIODIC_LOG_ENABLED', False))
    periodic_log_enable_checkbox.setStyleSheet("""
        QCheckBox {
            color: white;
            font-size: 11px;
            padding: 2px;
        }
        QCheckBox::indicator {
            width: 14px;
            height: 14px;
            border: 1px solid #555555;
            background-color: #2a2a2a;
            border-radius: 3px;
        }
        QCheckBox::indicator:checked {
            background-color: #2674f0;
            border: 1px solid #3b84ff;
        }
        QCheckBox::indicator:hover {
            border: 1px solid #666666;
        }
    """)
    periodic_log_enable_checkbox.setToolTip(
        'Enable or disable periodic logging of downsampled values to file.\n'
        'When disabled, no data will be written even if a file path is set.'
    )
    logging_card_layout.addWidget(periodic_log_enable_checkbox)
    
    # File path selection row
    file_row = pg.QtWidgets.QHBoxLayout()
    file_row.setSpacing(4)
    file_row.addWidget(create_label_with_style('Log File:'))
    
    # File path line edit
    file_path_edit = pg.QtWidgets.QLineEdit()
    file_path_edit.setText(config.get('PERIODIC_LOG_FILE', ''))
    file_path_edit.setPlaceholderText("Select log file location...")
    file_path_edit.setStyleSheet(f"""
        QLineEdit {{{BASE_WIDGET_STYLE}}}
        QLineEdit:hover {{{BASE_WIDGET_HOVER}}}
    """)
    file_path_edit.setToolTip('Path to the log file where downsampled values will be written')
    file_row.addWidget(file_path_edit)
    
    # Browse button
    browse_button = pg.QtWidgets.QPushButton('Browse...')
    browse_button.setStyleSheet(STYLES['secondary_button'])
    browse_button.setToolTip('Browse for log file location')
    browse_button.setMaximumWidth(80)
    
    # Connect browse button to file dialog
    def on_browse_clicked():
        file_path, _ = pg.QtWidgets.QFileDialog.getSaveFileName(
            None,
            "Select Log File Location",
            file_path_edit.text() if file_path_edit.text() else "",
            "NumPy Array Files (*.npy);;All Files (*.*)"
        )
        if file_path:
            # Ensure .npy extension
            if not file_path.endswith('.npy'):
                file_path += '.npy'
            file_path_edit.setText(file_path)
    
    browse_button.clicked.connect(on_browse_clicked)
    file_row.addWidget(browse_button)
    file_row.addStretch()
    logging_card_layout.addLayout(file_row)
    
    # Log rate control
    logging_card_layout.addWidget(create_label_with_style('Log Rate:'))
    
    log_rate_spinbox = create_double_spinbox_with_style(
        0.01, 3600.0, config.get('PERIODIC_LOG_RATE', 1.0),  # 0.01s to 1 hour
        decimals=2, step=0.1, suffix=' s',
        tooltip='How often to write downsampled values to the log file.\n'
                'Lower values = more frequent writes (higher disk I/O).\n'
                'Higher values = less frequent writes (lower disk I/O).'
    )
    logging_card_layout.addWidget(log_rate_spinbox)
    
    # Log File Analysis Card (Card 7 - Optional/Advanced, collapsed by default)
    analysis_card, analysis_card_layout, _ = create_collapsible_card_widget("Log File Analysis", default_expanded=False)
    
    # File path selection row
    analysis_file_row = pg.QtWidgets.QHBoxLayout()
    analysis_file_row.setSpacing(4)
    analysis_file_row.addWidget(create_label_with_style('Log File:'))
    
    # File path line edit for analysis
    analysis_file_path_edit = pg.QtWidgets.QLineEdit()
    analysis_file_path_edit.setPlaceholderText("Select log file to analyze...")
    analysis_file_path_edit.setStyleSheet(f"""
        QLineEdit {{{BASE_WIDGET_STYLE}}}
        QLineEdit:hover {{{BASE_WIDGET_HOVER}}}
    """)
    analysis_file_path_edit.setToolTip('Path to the .npy log file to analyze')
    analysis_file_row.addWidget(analysis_file_path_edit)
    
    # Browse button for analysis file
    analysis_browse_button = pg.QtWidgets.QPushButton('Browse...')
    analysis_browse_button.setStyleSheet(STYLES['secondary_button'])
    analysis_browse_button.setToolTip('Browse for log file to analyze')
    analysis_browse_button.setMaximumWidth(80)
    
    # Connect browse button to file dialog
    def on_analysis_browse_clicked():
        file_path, _ = pg.QtWidgets.QFileDialog.getOpenFileName(
            None,
            "Select Log File to Analyze",
            analysis_file_path_edit.text() if analysis_file_path_edit.text() else "",
            "NumPy Array Files (*.npy);;All Files (*.*)"
        )
        if file_path:
            analysis_file_path_edit.setText(file_path)
    
    analysis_browse_button.clicked.connect(on_analysis_browse_clicked)
    analysis_file_row.addWidget(analysis_browse_button)
    analysis_file_row.addStretch()
    analysis_card_layout.addLayout(analysis_file_row)
    
    # Helper function to create styled message boxes
    def create_styled_message_box(icon_type, title, text):
        """Create a QMessageBox with dark theme styling."""
        msg_box = pg.QtWidgets.QMessageBox()
        msg_box.setWindowTitle(title)
        msg_box.setText(text)
        
        # Set icon - try different ways to access the Icon enum
        try:
            # Try accessing Icon enum directly
            Icon = pg.QtWidgets.QMessageBox.Icon
            if icon_type == 1:
                msg_box.setIcon(Icon.Information)
            elif icon_type == 2:
                msg_box.setIcon(Icon.Warning)
            elif icon_type == 3:
                msg_box.setIcon(Icon.Critical)
            elif icon_type == 4:
                msg_box.setIcon(Icon.Question)
            else:
                msg_box.setIcon(Icon.Information)
        except AttributeError:
            # Fallback: try accessing as class attribute
            try:
                if icon_type == 1:
                    msg_box.setIcon(pg.QtWidgets.QMessageBox.Information)
                elif icon_type == 2:
                    msg_box.setIcon(pg.QtWidgets.QMessageBox.Warning)
                elif icon_type == 3:
                    msg_box.setIcon(pg.QtWidgets.QMessageBox.Critical)
                elif icon_type == 4:
                    msg_box.setIcon(pg.QtWidgets.QMessageBox.Question)
                else:
                    msg_box.setIcon(pg.QtWidgets.QMessageBox.Information)
            except AttributeError:
                # Last resort: don't set icon, just use default
                pass
        
        # Apply dark theme styling
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: #252525;
                color: white;
            }
            QMessageBox QLabel {
                color: white;
                background-color: transparent;
            }
            QMessageBox QPushButton {
                background-color: #555555;
                color: white;
                border: 1px solid #444444;
                border-radius: 4px;
                padding: 4px 10px;
                min-width: 80px;
                min-height: 26px;
            }
            QMessageBox QPushButton:hover {
                background-color: #666666;
            }
            QMessageBox QPushButton:pressed {
                background-color: #444444;
            }
        """)
        
        return msg_box
    
    # Analysis button
    analyze_button = pg.QtWidgets.QPushButton('Analyze')
    analyze_button.setStyleSheet(STYLES['primary_button'])
    analyze_button.setToolTip('Run analysis: statistics and plots')
    
    # Connect button to launch analysis tool
    def launch_analysis():
        """Run log analysis directly and display results in console."""
        import os
        import sys
        
        # Import analysis functions directly
        # log_analysis_tool.py is in the same directory as this file
        script_dir = os.path.dirname(os.path.abspath(__file__))
        analysis_tool_path = os.path.join(script_dir, 'log_analysis_tool.py')
        
        file_path = analysis_file_path_edit.text().strip()
        if not file_path:
            msg = create_styled_message_box(
                2,  # Warning
                "No File Selected",
                "Please select a log file to analyze."
            )
            msg.exec()
            return
        
        if not os.path.exists(file_path):
            msg = create_styled_message_box(
                2,  # Warning
                "File Not Found",
                f"The selected file does not exist:\n{file_path}"
            )
            msg.exec()
            return
        
        try:
            # Import analysis functions
            import importlib.util
            spec = importlib.util.spec_from_file_location("log_analysis_tool", analysis_tool_path)
            if spec is None or spec.loader is None:
                raise ImportError("Could not load analysis tool module")
            analysis_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(analysis_module)
            
            # Load and analyze the file
            print("\n" + "=" * 70)
            print("LOG FILE ANALYSIS")
            print("=" * 70)
            print(f"Analyzing: {file_path}")
            print(f"File size: {os.path.getsize(file_path) / 1024:.2f} KB")
            print()
            
            # Load data
            data = analysis_module.load_log_file(file_path)
            print(f"✓ Loaded {len(data):,} samples")
            
            # Validate data
            validation = analysis_module.validate_data(data)
            if validation['issues']:
                print("⚠ Data validation issues found:")
                for issue in validation['issues']:
                    print(f"  - {issue}")
            else:
                print("✓ Data validation passed")
            print()
            
            # Calculate statistics
            stats = analysis_module.calculate_statistics(data)
            if 'error' in stats:
                print(f"⚠ Could not calculate statistics: {stats['error']}")
                stats = None
            
            # Create plots with statistics displayed on plot
            print("Generating plots with statistics...")
            analysis_module.create_plots(data, output_dir=None, show_plots=True, stats=stats)
            print("✓ Analysis complete - statistics displayed on plot")
            print("=" * 70)
            print()
            
        except Exception as e:
            import traceback
            error_msg = f"Error during analysis:\n{str(e)}\n\n{traceback.format_exc()}"
            print(f"\n[ERROR] {error_msg}")
            msg = create_styled_message_box(
                3,  # Critical
                "Analysis Error",
                f"Failed to analyze log file:\n{str(e)}"
            )
            msg.exec()
    
    analyze_button.clicked.connect(launch_analysis)
    
    analysis_buttons_row = pg.QtWidgets.QHBoxLayout()
    analysis_buttons_row.setSpacing(6)
    analysis_buttons_row.addWidget(analyze_button)
    analysis_buttons_row.addStretch()
    analysis_card_layout.addLayout(analysis_buttons_row)
    
    # Reorder cards: Add cards in better UX order
    # (Already added: hw_settings_card, acquisition_card, trigger_card, raw_display_card)
    # Now add: logging_card, analysis_card, then performance_card and raw_display_card at the bottom
    controls_layout.addWidget(logging_card)
    controls_layout.addWidget(analysis_card)
    controls_layout.addWidget(performance_card)
    controls_layout.addWidget(raw_display_card)
    
    # Add spacer and action buttons
    controls_layout.addStretch()
    
    button_container, apply_button, stop_button, pull_region_raw_button = create_action_buttons()
    controls_layout.addWidget(button_container)
    
    # Return all widgets in a dictionary
    return {
        'panel': controls_panel,
        'mode_combo': mode_combo,
        'ratio_spinbox': ratio_spinbox,
        'interval_spinbox': interval_spinbox,
        'units_combo': units_combo,
        'hw_buffer_spinbox': hw_buffer_spinbox,
        'refresh_spinbox': refresh_spinbox,
        'poll_spinbox': poll_spinbox,
        'time_window_spinbox': time_window_spinbox,
        'raw_display_enable_checkbox': raw_display_enable_checkbox,
        'raw_display_mode_combo': raw_display_mode_combo,
        'raw_display_factor_spinbox': raw_display_factor_spinbox,
        'raw_display_max_points_spinbox': raw_display_max_points_spinbox,
        'gated_raw_downsample_checkbox': gated_raw_downsample_checkbox,
        'region_markers_checkbox': region_markers_checkbox,
        'trigger_enable_checkbox': trigger_widgets['enable_checkbox'],
        'trigger_threshold_spinbox': trigger_widgets['threshold_spinbox'],
        'trigger_direction_combo': trigger_widgets['direction_combo'],
        'pre_trigger_time_spinbox': trigger_widgets['pre_trigger_spinbox'],
        'trigger_units_combo': trigger_widgets['units_combo'],
        'post_trigger_time_spinbox': trigger_widgets['post_trigger_spinbox'],
        'periodic_log_enable_checkbox': periodic_log_enable_checkbox,
        'periodic_log_file_edit': file_path_edit,
        'periodic_log_browse_button': browse_button,
        'periodic_log_rate_spinbox': log_rate_spinbox,
        'analysis_file_path_edit': analysis_file_path_edit,
        'analysis_browse_button': analysis_browse_button,
        'analyze_button': analyze_button,
        'channel_range_combo': channel_range_combo,
        'channel_coupling_combo': channel_coupling_combo,
        'channel_probe_combo': channel_probe_combo,
        'siggen_freq_spinbox': siggen_freq_spinbox,
        'siggen_pk2pk_spinbox': siggen_pk2pk_spinbox,
        'siggen_wave_combo': siggen_wave_combo,
        'apply_button': apply_button,
        'stop_button': stop_button,
        'pull_region_raw_button': pull_region_raw_button
    }

