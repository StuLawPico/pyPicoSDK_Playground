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
    }
}

# Base widget styles to reduce duplication
BASE_WIDGET_STYLE = """
    background-color: #333333;
    color: white;
    border: 1px solid #666666;
    padding: 2px 6px;
    font-size: 11px;
    min-width: 70px;
"""

BASE_WIDGET_HOVER = """
    border-color: #888888;
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
    """,
    
    'primary_button': f"""
        QPushButton {{
            background-color: #4444ff;
            {BASE_BUTTON_STYLE}
        }}
        QPushButton:hover {{{BASE_BUTTON_HOVER}}}
        QPushButton:pressed {{{BASE_BUTTON_PRESSED}}}
        QPushButton:disabled {{{BASE_BUTTON_DISABLED}}}
    """,
    
    'stop_button': f"""
        QPushButton {{
            background-color: #ff4444;
            {BASE_BUTTON_STYLE}
        }}
        QPushButton:hover {{
            background-color: #ff6666;
        }}
        QPushButton:pressed {{
            background-color: #cc3333;
        }}
        QPushButton:disabled {{{BASE_BUTTON_DISABLED}}}
    """,
    
    'slider': """
        QSlider::groove:horizontal {
            background: #333333;
            height: 6px;
            border-radius: 3px;
        }
        QSlider::handle:horizontal {
            background: #4444ff;
            width: 14px;
            margin: -4px 0;
            border-radius: 7px;
        }
        QSlider::handle:horizontal:hover {
            background: #6666ff;
        }
    """,
    
    'section_label': """
        color: #000000;
        font-weight: bold;
        font-size: 10px;
        background-color: #f0f0f0;
        padding: 1px 3px;
        border-radius: 2px;
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
            font-size: 11px;
            font-weight: bold;
            border: 1px solid #555555;
            border-radius: 4px;
            margin-top: 8px;
            padding-top: 6px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 1px 4px;
            color: #000000;
            background-color: #f0f0f0;
            border-radius: 2px;
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
    layout.setSpacing(2)
    layout.setContentsMargins(6, 6, 6, 4)
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
    spinbox.setStyleSheet(STYLES[style])
    if tooltip:
        spinbox.setToolTip(tooltip)
    return spinbox


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
    if suffix:
        spinbox.setSuffix(suffix)
    spinbox.setStyleSheet(STYLES['dark_double_spinbox'])
    if tooltip:
        spinbox.setToolTip(tooltip)
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
    display.setStyleSheet(f"""
        QLabel {{
            background-color: {color_scheme['bg_color']};
            color: {color_scheme['text_color']};
            border: 1px solid {color_scheme['border_color']};
            padding: 2px 6px;
            font-size: 11px;
            font-weight: bold;
            border-radius: 3px;
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
    status_bar_main_layout = pg.QtWidgets.QVBoxLayout()
    status_bar.setLayout(status_bar_main_layout)
    status_bar.setStyleSheet("background-color: #1a1a1a; padding: 4px;")
    status_bar_main_layout.setContentsMargins(5, 2, 5, 2)
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
    downsampled_rate_label, downsampled_rate_display = create_status_display_widget('Downsampled:', '0.0 MSPS', 'downsampled_rate')
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

    # Row 2: Memory metrics
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
    Create the downsampling controls group.
    
    Args:
        psdk: PicoSDK module reference
        current_ratio: Current downsampling ratio value
        current_mode: Current downsampling mode
    
    Returns:
        tuple: (group_widget, mode_combo, ratio_spinbox)
    """
    downsample_group, downsample_layout = create_group_widget("Downsampling")
    
    # Mode selection
    downsample_layout.addWidget(create_label_with_style('Mode:'))
    
    mode_combo = pg.QtWidgets.QComboBox()
    mode_combo.addItem('Decimate', psdk.RATIO_MODE.DECIMATE)
    mode_combo.addItem('Average', psdk.RATIO_MODE.AVERAGE)
    mode_combo.setCurrentText(
        'Decimate' if current_mode == psdk.RATIO_MODE.DECIMATE else 'Average'
    )
    mode_combo.setStyleSheet(STYLES['dark_combobox'])
    downsample_layout.addWidget(mode_combo)
    
    # Ratio selection
    downsample_layout.addWidget(create_label_with_style('Ratio:'))
    
    ratio_spinbox = create_spinbox_with_style(64, 640000, current_ratio, step=64)
    ratio_spinbox.valueChanged.connect(
        lambda v: ratio_spinbox.setValue(validate_ratio(v))
    )
    downsample_layout.addWidget(ratio_spinbox)
    
    return downsample_group, mode_combo, ratio_spinbox


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
    
    # Interval value
    interval_layout.addWidget(create_label_with_style('Interval:'))
    interval_spinbox = create_spinbox_with_style(1, 1000000, current_interval)
    interval_layout.addWidget(interval_spinbox)
    
    # Time units
    interval_layout.addWidget(create_label_with_style('Units:'))
    
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
    interval_layout.addWidget(units_combo)
    
    return interval_group, interval_spinbox, units_combo


def create_buffer_controls(current_buffer_size):
    """
    Create the hardware buffer size controls group.
    
    Args:
        current_buffer_size: Current buffer size value
    
    Returns:
        tuple: (group_widget, hw_buffer_spinbox)
    """
    hw_buffer_group, hw_buffer_layout = create_group_widget("HW Buffer")
    
    hw_buffer_layout.addWidget(create_label_with_style('Buffer Size:'))
    
    hw_buffer_spinbox = create_spinbox_with_style(
        1000, 10_000_000, current_buffer_size, step=1000,
        tooltip='Size of hardware double buffers (downsampled samples).\n'
                'Larger = better safety margin, but uses more device memory.'
    )
    hw_buffer_layout.addWidget(hw_buffer_spinbox)
    
    # Info label
    hw_buffer_info = pg.QtWidgets.QLabel('Auto-optimized on Apply')
    hw_buffer_info.setStyleSheet("color: #666666; font-size: 9px; font-style: italic;")
    hw_buffer_layout.addWidget(hw_buffer_info)
    
    return hw_buffer_group, hw_buffer_spinbox


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


def create_time_window_controls(current_time_window):
    """
    Create the display time window controls group.
    
    Args:
        current_time_window: Current time window value (seconds)
    
    Returns:
        tuple: (group_widget, time_window_slider, time_window_value_label)
    """
    time_window_group = pg.QtWidgets.QGroupBox("Display Window")
    time_window_layout = pg.QtWidgets.QVBoxLayout()
    time_window_group.setLayout(time_window_layout)
    time_window_group.setStyleSheet(STYLES['groupbox'])
    time_window_layout.setSpacing(2)
    time_window_layout.setContentsMargins(6, 6, 6, 4)
    
    # Title row with inline value display
    title_row = pg.QtWidgets.QHBoxLayout()
    title_row.setSpacing(4)
    
    time_window_label = pg.QtWidgets.QLabel('Time Span:')
    time_window_label.setStyleSheet(STYLES['section_label'])
    title_row.addWidget(time_window_label)
    
    # Compact value display label on same line
    time_window_value_label = pg.QtWidgets.QLabel()
    time_window_value_label.setStyleSheet(STYLES['value_display_label'])
    title_row.addWidget(time_window_value_label)
    
    title_row.addStretch()
    time_window_layout.addLayout(title_row)
    
    # Slider
    try:
        # Qt6 style
        time_window_slider = pg.QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
    except AttributeError:
        # Qt5 style
        time_window_slider = pg.QtWidgets.QSlider(QtCore.Qt.Horizontal)
    
    time_window_slider.setMinimum(1)
    time_window_slider.setMaximum(10)
    time_window_slider.setValue(int(current_time_window))
    
    try:
        time_window_slider.setTickPosition(pg.QtWidgets.QSlider.TickPosition.TicksBelow)
    except AttributeError:
        time_window_slider.setTickPosition(pg.QtWidgets.QSlider.TicksBelow)
    
    time_window_slider.setTickInterval(1)
    time_window_slider.setStyleSheet(STYLES['slider'])
    time_window_slider.setToolTip(
        'Adjust the time span of data visible in the plot.\n'
        'Changes apply when you click "Apply Changes".'
    )
    time_window_layout.addWidget(time_window_slider)
    
    # Function to update label
    def update_time_window_label(value):
        if value == 1:
            time_window_value_label.setText(f"{value}s")
        else:
            time_window_value_label.setText(f"{value}s")
    
    # Connect and initialize
    time_window_slider.valueChanged.connect(update_time_window_label)
    update_time_window_label(int(current_time_window))
    
    return time_window_group, time_window_slider, time_window_value_label


def create_trigger_controls(current_max_post_trigger_samples, trigger_enabled=True, trigger_threshold_adc=50, buffer_size=1000000):
    """
    Create the trigger settings controls group.
    
    Args:
        current_max_post_trigger_samples: Current max post trigger samples value
        trigger_enabled: Whether trigger is enabled by default
        trigger_threshold_adc: Default trigger threshold in ADC counts
        buffer_size: Current buffer size to limit max post trigger
    
    Returns:
        tuple: (group_widget, trigger_enable_checkbox, trigger_threshold_spinbox, max_post_trigger_spinbox)
    """
    trigger_group = pg.QtWidgets.QGroupBox("Trigger Settings")
    trigger_layout = pg.QtWidgets.QVBoxLayout()
    trigger_group.setLayout(trigger_layout)
    trigger_group.setStyleSheet(STYLES['groupbox'])
    trigger_layout.setSpacing(2)
    trigger_layout.setContentsMargins(6, 6, 6, 4)
    
    # Trigger Enable/Disable
    trigger_enable_checkbox = pg.QtWidgets.QCheckBox("Enable Simple Trigger")
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
    trigger_enable_checkbox.setChecked(trigger_enabled)  # Use parameter
    trigger_enable_checkbox.setToolTip(
        'Enable or disable simple trigger on Channel A.\n'
        'When disabled, streaming runs continuously without triggering.'
    )
    trigger_layout.addWidget(trigger_enable_checkbox)
    
    # Add small spacer
    trigger_layout.addSpacing(4)
    
    # Trigger Threshold (ADC counts)
    threshold_label = pg.QtWidgets.QLabel('Threshold (ADC):')
    threshold_label.setStyleSheet(STYLES['section_label'])
    trigger_layout.addWidget(threshold_label)
    
    trigger_threshold_spinbox = pg.QtWidgets.QSpinBox()
    trigger_threshold_spinbox.setRange(-128, 127)  # 8-bit ADC range
    trigger_threshold_spinbox.setSingleStep(1)
    trigger_threshold_spinbox.setValue(trigger_threshold_adc)
    trigger_threshold_spinbox.setToolTip(
        'Trigger threshold in ADC counts.\n'
        'Range: -128 to +127 for 8-bit ADC.\n'
        '0 = trigger at zero crossing.\n'
        'Positive = trigger above zero.\n'
        'Negative = trigger below zero.'
    )
    trigger_threshold_spinbox.setStyleSheet(STYLES['dark_spinbox'])
    trigger_threshold_spinbox.setEnabled(trigger_enabled)  # Enabled based on trigger state
    trigger_layout.addWidget(trigger_threshold_spinbox)
    
    # Add small spacer
    trigger_layout.addSpacing(4)
    
    # Max Pre Trigger Samples
    max_pre_label = pg.QtWidgets.QLabel('Max Pre Trigger:')
    max_pre_label.setStyleSheet(STYLES['section_label'])
    trigger_layout.addWidget(max_pre_label)
    
    max_pre_trigger_spinbox = pg.QtWidgets.QSpinBox()
    max_pre_trigger_spinbox.setRange(0, 10_000_000)
    max_pre_trigger_spinbox.setSingleStep(100)
    max_pre_trigger_spinbox.setValue(0)
    max_pre_trigger_spinbox.setToolTip(
        'Maximum number of samples BEFORE trigger event.\n'
        'Captures data leading up to the trigger.\n'
        '0 = no pre-trigger (start capture at trigger).'
    )
    max_pre_trigger_spinbox.setStyleSheet(STYLES['dark_spinbox'])
    max_pre_trigger_spinbox.setEnabled(trigger_enabled)  # Enabled based on trigger state
    trigger_layout.addWidget(max_pre_trigger_spinbox)
    
    # Add small spacer
    trigger_layout.addSpacing(2)
    
    # Max Post Trigger Samples
    max_post_label = pg.QtWidgets.QLabel('Max Post Trigger:')
    max_post_label.setStyleSheet(STYLES['section_label'])
    trigger_layout.addWidget(max_post_label)
    
    max_post_trigger_spinbox = pg.QtWidgets.QSpinBox()
    # Set range with buffer size as upper limit (must be less than buffer size)
    max_allowed = buffer_size - 1
    max_post_trigger_spinbox.setRange(100, max_allowed)
    max_post_trigger_spinbox.setSingleStep(100)
    max_post_trigger_spinbox.setValue(current_max_post_trigger_samples)
    max_post_trigger_spinbox.setToolTip(
        f'Maximum number of samples AFTER trigger event.\n'
        f'Range: 100 to {max_allowed:,} samples (must be less than buffer size {buffer_size:,}).\n'
        f'If no trigger is set, this defines the maximum samples to store.'
    )
    max_post_trigger_spinbox.setStyleSheet(STYLES['dark_spinbox'])
    max_post_trigger_spinbox.setEnabled(trigger_enabled)  # Enabled based on trigger state
    trigger_layout.addWidget(max_post_trigger_spinbox)
    
    # Connect checkbox to enable/disable controls
    def on_trigger_enable_changed(state):
        enabled = (state == 2)  # Qt.Checked = 2
        trigger_threshold_spinbox.setEnabled(enabled)
        max_pre_trigger_spinbox.setEnabled(enabled)
        max_post_trigger_spinbox.setEnabled(enabled)
    
    trigger_enable_checkbox.stateChanged.connect(on_trigger_enable_changed)
    
    return trigger_group, trigger_enable_checkbox, trigger_threshold_spinbox, max_pre_trigger_spinbox, max_post_trigger_spinbox


def create_action_buttons():
    """
    Create the action buttons (Apply and Stop) in a horizontal layout.
    
    Returns:
        tuple: (button_container, apply_button, stop_button)
    """
    # Create container widget for horizontal button layout
    button_container = pg.QtWidgets.QWidget()
    button_layout = pg.QtWidgets.QHBoxLayout()
    button_container.setLayout(button_layout)
    button_layout.setSpacing(4)
    button_layout.setContentsMargins(0, 0, 0, 0)
    
    apply_button = pg.QtWidgets.QPushButton('Apply')
    apply_button.setStyleSheet(STYLES['primary_button'])
    apply_button.setToolTip('Apply changes to streaming settings')
    
    stop_button = pg.QtWidgets.QPushButton('Stop')
    stop_button.setStyleSheet(STYLES['stop_button'])
    stop_button.setToolTip('Stop/Restart streaming')
    
    button_layout.addWidget(apply_button)
    button_layout.addWidget(stop_button)
    
    return button_container, apply_button, stop_button


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
            - MAX_POST_TRIGGER_SAMPLES: Max post trigger samples
    
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
            - 'time_window_slider': Time window slider
            - 'time_window_value_label': Time window value label
            - 'max_post_trigger_spinbox': Max post trigger samples spinbox
            - 'apply_button': Apply changes button
            - 'stop_button': Stop/restart button
    """
    # Create control panel container
    controls_panel = pg.QtWidgets.QWidget()
    controls_layout = pg.QtWidgets.QVBoxLayout()
    controls_panel.setLayout(controls_layout)
    controls_panel.setMinimumWidth(300)
    controls_panel.setMaximumWidth(400)
    controls_layout.setSpacing(4)
    controls_layout.setContentsMargins(4, 4, 4, 4)
    
    # Create all control groups
    downsample_group, mode_combo, ratio_spinbox = create_downsampling_controls(
        config['psdk'],
        config['DOWNSAMPLING_RATIO'],
        config['DOWNSAMPLING_MODE']
    )
    controls_layout.addWidget(downsample_group)
    
    interval_group, interval_spinbox, units_combo = create_interval_controls(
        config['psdk'],
        config['sample_interval'],
        config['time_units']
    )
    controls_layout.addWidget(interval_group)
    
    hw_buffer_group, hw_buffer_spinbox = create_buffer_controls(
        config['SAMPLES_PER_BUFFER']
    )
    controls_layout.addWidget(hw_buffer_group)
    
    performance_group, refresh_spinbox, poll_spinbox = create_performance_controls(
        config['REFRESH_FPS'],
        config['POLLING_INTERVAL']
    )
    controls_layout.addWidget(performance_group)
    
    time_window_group, time_window_slider, time_window_value_label = create_time_window_controls(
        config['TARGET_TIME_WINDOW']
    )
    controls_layout.addWidget(time_window_group)
    
    trigger_group, trigger_enable_checkbox, trigger_threshold_spinbox, max_pre_trigger_spinbox, max_post_trigger_spinbox = create_trigger_controls(
        config['MAX_POST_TRIGGER_SAMPLES'],
        config.get('TRIGGER_ENABLED', True),
        config.get('TRIGGER_THRESHOLD_ADC', 50),
        config['SAMPLES_PER_BUFFER']
    )
    controls_layout.addWidget(trigger_group)
    
    # Add spacer and action buttons
    controls_layout.addStretch()
    
    button_container, apply_button, stop_button = create_action_buttons()
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
        'time_window_slider': time_window_slider,
        'time_window_value_label': time_window_value_label,
        'trigger_enable_checkbox': trigger_enable_checkbox,
        'trigger_threshold_spinbox': trigger_threshold_spinbox,
        'max_pre_trigger_spinbox': max_pre_trigger_spinbox,
        'max_post_trigger_spinbox': max_post_trigger_spinbox,
        'apply_button': apply_button,
        'stop_button': stop_button
    }

