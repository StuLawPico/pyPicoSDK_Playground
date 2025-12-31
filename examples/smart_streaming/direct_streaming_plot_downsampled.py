"""
Direct streaming example for a PicoScope 6000E device with PyQtGraph - Downsampled Modes Only

Description:
  Demonstrates continuous streaming data capture and plotting using direct wrapper calls.
  Uses PyQtGraph for real-time plotting with threading for data acquisition.
  This version only supports downsampled modes (decimate and average).

Features:
- Threading: Data acquisition and plotting run in separate threads
- PyQtGraph: Fast real-time plotting
- Circular buffer: Efficient rolling data storage
- Downsampled modes only: Decimate and average modes supported
- Auto-scrolling: Continuous sample indexing with automatic view updates
- Dynamic downsampling: User can change ratio and mode during streaming

Requirements:
- PicoScope 6000E
- Python packages: pyqtgraph numpy pypicosdk PyQt5 (or PyQt6)

Setup:
  - Connect Channel A to the AWG output
"""
from numba import njit
import time
import threading
import sys
import numpy as np
from collections import deque
import json
from datetime import datetime
import os

# PyQtGraph imports
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'pyPicoSDK_Playground'))
import pypicosdk as psdk


# Import UI components module
from ui_components import build_control_panel, STYLES, create_status_display_widget, create_separator, STATUS_COLOR_SCHEMES, create_status_bar

# Import helper modules
from hardware_helpers import (
    calculate_sample_rate, register_double_buffers, start_hardware_streaming,
    stop_hardware_streaming, clear_hardware_buffers,
    compute_interval_from_msps, configure_default_trigger, apply_trigger_configuration,
    calculate_optimal_buffer_size, validate_buffer_size, time_to_samples,
    TIME_UNIT_NAMES, TIME_UNIT_TO_SECONDS,
    pull_raw_samples_from_device, get_trigger_position_from_device
)
import data_processing
from data_processing import (
    drain_remaining_buffers, calculate_raw_data_time_alignment
)
from ui_helpers import (
    update_buffer_status, update_efficiency_display
)
from ui_helpers import (
    collect_ui_settings, calculate_what_changed, validate_and_optimize_settings,
    apply_performance_settings, apply_time_window, apply_streaming_restart,
    update_max_post_trigger_range, apply_channel_siggen_settings
)

# Custom signal for thread-safe communication
class PlotUpdateSignal(QtCore.QObject):
    title_updated = QtCore.pyqtSignal(str)
    data_updated = QtCore.pyqtSignal(object, object)  # x_data, y_data
    buffer_status_updated = QtCore.pyqtSignal(int, int)  # current, total
    efficiency_updated = QtCore.pyqtSignal(float, float, str)  # efficiency %, jitter %, status
    trigger_fired = QtCore.pyqtSignal(int)  # trigger_at sample index


# Check Qt version for compatibility
try:
    # Try to determine Qt version for better error reporting
    qt_version = QtCore.QT_VERSION_STR if hasattr(QtCore, 'QT_VERSION_STR') else "Unknown"
    print(f"Using Qt version: {qt_version}")
except:
    print("Qt version detection failed, but continuing...")

# ============================================================================
# INITIAL CONFIGURATION
# ============================================================================
# All initial/default values in one place
# These are used for both hardware initialization and UI initialization

INITIAL_CONFIG = {
    # Streaming Configuration
    'downsampling_ratio': 64000,
    'downsampling_mode': psdk.RATIO_MODE.DECIMATE,
    'sample_interval': 1,  # Request sample interval in nanoseconds
    'time_units': psdk.TIME_UNIT.NS,
    
    # Buffer Configuration
    'samples_per_buffer': 1000000,  # Samples per hardware buffer (will be auto-calculated if optimal)
    'target_time_window': 1.0,  # Target time window in seconds (user-adjustable via slider)
    'python_ring_buffer': 100_000,  # Initial Python circular buffer size (will be recalculated based on ratio and time window)
    
    # Channel Configuration
    'channel_range': psdk.RANGE.mV500,
    'channel_coupling': psdk.COUPLING.AC,
    'channel_probe_scale': 1.0,
    
    # Signal Generator Configuration
    'siggen_frequency': 1.0,  # Hz
    'siggen_pk2pk': 0.95,  # V
    'siggen_wave_type': psdk.WAVEFORM.SINE,
    
    # Trigger Configuration
    'trigger_enabled': False,
    'trigger_threshold_adc': 50,  # Trigger threshold in ADC counts
    'trigger_direction': psdk.TRIGGER_DIR.RISING_OR_FALLING,
    'pre_trigger_time': 0.0,
    'pre_trigger_time_units': psdk.TIME_UNIT.MS,
    'post_trigger_time': 1.0,
    'post_trigger_time_units': psdk.TIME_UNIT.MS,
    
    # Display Configuration
    'refresh_fps': 30,  # Plot refresh rate in frames per second
    'raw_data_downsample_enabled': True,  # Enable PyQtGraph downsampling for raw data
    'raw_data_downsample_mode': 'subsample',  # Downsampling mode: 'subsample', 'mean', or 'peak'
    'raw_data_downsample_factor': 100,  # Downsampling factor (1 = no downsampling)
    'raw_data_max_points': 500_000,  # Maximum number of downsampled points to display
    
    # System Configuration (not user-changeable via UI, but part of initial config)
    'polling_interval': 0.001,  # Hardware polling interval in seconds (1ms)
    'adc_data_type': psdk.DATA_TYPE.INT8_T,  # 8-bit signed integer (-128 to +127)
    'adc_numpy_type': np.int8,
    'use_opengl': False,  # OpenGL acceleration disabled for simplicity
    'plot_pen_width': 1,  # Line width
    'antialias': False,  # Disable antialiasing for performance
    
    # Periodic Logging Configuration
    'periodic_log_enabled': False,  # Enable/disable periodic logging
    'periodic_log_file': "",  # Log file path (empty = disabled)
    'periodic_log_rate': 1.0,  # Log rate in seconds (how often to write)
}

# Optional: configure target streaming rate in MSPS (mega-samples per second)
# Set to a float (e.g., 0.3 for 300 kS/s, 1.0 for 1 MS/s) or None to keep defaults
STREAM_RATE_MSPS = None  # Disabled - using explicit sample_interval instead

# System Constants (not part of configuration, never change)
SYSTEM_CONSTANTS = {
    'settings_update_delay_sec': 0.5,  # Delay for thread synchronization during settings updates
    'buffer_clear_delay_sec': 0.1,  # Delay after clearing hardware buffers
    'streaming_stop_delay_sec': 0.5,  # Delay after stopping streaming before clearing buffers
    'drain_buffer_timeout_sec': 2.0,  # Maximum time to spend draining buffers after stop
    'drain_buffer_sleep_sec': 0.05,  # Sleep interval between drain attempts
    'min_ring_buffer_samples': 100,  # Minimum ring buffer size for smooth plotting
    'min_hardware_buffer_samples': 1000,  # Minimum hardware buffer size
    'ms_to_seconds': 1000.0,  # Conversion factor: milliseconds to seconds
    'seconds_to_ms': 1000.0,  # Conversion factor: seconds to milliseconds
    'percentage_multiplier': 100.0,  # Conversion factor: decimal to percentage
}

# Legacy constants for backward compatibility (will be removed in future)
# These map to INITIAL_CONFIG values
SAMPLES_PER_BUFFER = INITIAL_CONFIG['samples_per_buffer']
TARGET_TIME_WINDOW = INITIAL_CONFIG['target_time_window']
PYTHON_RING_BUFFER = INITIAL_CONFIG['python_ring_buffer']
REFRESH_FPS = INITIAL_CONFIG['refresh_fps']
sample_interval = INITIAL_CONFIG['sample_interval']
time_units = INITIAL_CONFIG['time_units']
DOWNSAMPLING_RATIO = INITIAL_CONFIG['downsampling_ratio']
DOWNSAMPLING_MODE = INITIAL_CONFIG['downsampling_mode']
PRE_TRIGGER_TIME = INITIAL_CONFIG['pre_trigger_time']
PRE_TRIGGER_TIME_UNITS = INITIAL_CONFIG['pre_trigger_time_units']
POST_TRIGGER_TIME = INITIAL_CONFIG['post_trigger_time']
POST_TRIGGER_TIME_UNITS = INITIAL_CONFIG['post_trigger_time_units']
RAW_DATA_DOWNSAMPLE_ENABLED = INITIAL_CONFIG['raw_data_downsample_enabled']
RAW_DATA_DOWNSAMPLE_MODE = INITIAL_CONFIG['raw_data_downsample_mode']
RAW_DATA_DOWNSAMPLE_FACTOR = INITIAL_CONFIG['raw_data_downsample_factor']
RAW_DATA_MAX_POINTS = INITIAL_CONFIG['raw_data_max_points']
TRIGGER_ENABLED = INITIAL_CONFIG['trigger_enabled']
TRIGGER_THRESHOLD_ADC = INITIAL_CONFIG['trigger_threshold_adc']
TRIGGER_DIRECTION = INITIAL_CONFIG['trigger_direction']
ADC_DATA_TYPE = INITIAL_CONFIG['adc_data_type']
ADC_NUMPY_TYPE = INITIAL_CONFIG['adc_numpy_type']
USE_OPENGL = INITIAL_CONFIG['use_opengl']
PLOT_PEN_WIDTH = INITIAL_CONFIG['plot_pen_width']
ANTIALIAS = INITIAL_CONFIG['antialias']
POLLING_INTERVAL = INITIAL_CONFIG['polling_interval']
PERIODIC_LOG_ENABLED = INITIAL_CONFIG['periodic_log_enabled']
PERIODIC_LOG_FILE = INITIAL_CONFIG['periodic_log_file']
PERIODIC_LOG_RATE = INITIAL_CONFIG['periodic_log_rate']
SETTINGS_UPDATE_DELAY_SEC = SYSTEM_CONSTANTS['settings_update_delay_sec']
BUFFER_CLEAR_DELAY_SEC = SYSTEM_CONSTANTS['buffer_clear_delay_sec']
STREAMING_STOP_DELAY_SEC = SYSTEM_CONSTANTS['streaming_stop_delay_sec']
DRAIN_BUFFER_TIMEOUT_SEC = SYSTEM_CONSTANTS['drain_buffer_timeout_sec']
DRAIN_BUFFER_SLEEP_SEC = SYSTEM_CONSTANTS['drain_buffer_sleep_sec']
MIN_RING_BUFFER_SAMPLES = SYSTEM_CONSTANTS['min_ring_buffer_samples']
MIN_HARDWARE_BUFFER_SAMPLES = SYSTEM_CONSTANTS['min_hardware_buffer_samples']
MS_TO_SECONDS = SYSTEM_CONSTANTS['ms_to_seconds']
SECONDS_TO_MS = SYSTEM_CONSTANTS['seconds_to_ms']
PERCENTAGE_MULTIPLIER = SYSTEM_CONSTANTS['percentage_multiplier']

# Runtime state variables (calculated/updated during execution)
MAX_PRE_TRIGGER_SAMPLES = 0  # Pre-trigger samples (calculated from time)
MAX_POST_TRIGGER_SAMPLES = None  # Will be initialized after buffer calculation
TRIGGER_EVENT_COUNT = 0  # Counter for trigger events

# ============================================================================
# HARDWARE INITIALIZATION
# ============================================================================

# Initialize PicoScope hardware
print("Initializing PicoScope...")
scope = psdk.psospa()
#scope = psdk.ps6000a()
scope.open_unit(resolution=psdk.RESOLUTION._8BIT)
print(f"Connected to: {scope.get_unit_serial()}")



# If configured, override sample_interval/time_units from MSPS
if STREAM_RATE_MSPS is not None:
    try:
        computed_interval, computed_units = compute_interval_from_msps(STREAM_RATE_MSPS)
        INITIAL_CONFIG['sample_interval'] = computed_interval
        INITIAL_CONFIG['time_units'] = computed_units
        # Update legacy constants for backward compatibility
        sample_interval = computed_interval
        time_units = computed_units
        print(f"Configured streaming interval from {STREAM_RATE_MSPS} MSPS -> interval={computed_interval} units={computed_units}")
    except Exception as e:
        print(f"[WARNING] Failed to set interval from MSPS ({STREAM_RATE_MSPS}): {e}. Using defaults.")

# Configure signal generator for test signal
scope.set_siggen(
    frequency=INITIAL_CONFIG['siggen_frequency'],
    pk2pk=INITIAL_CONFIG['siggen_pk2pk'],
    wave_type=INITIAL_CONFIG['siggen_wave_type']
)

# Enable channel A with configured range and coupling
# This accommodates the signal without clipping
scope.set_channel(
    channel=psdk.CHANNEL.A,
    range=INITIAL_CONFIG['channel_range'],
    coupling=INITIAL_CONFIG['channel_coupling'],
    probe_scale=INITIAL_CONFIG['channel_probe_scale']
)
# ============================================================================
# DOUBLE BUFFER SETUP
# ============================================================================
# Double buffering prevents data loss during continuous acquisition

# Auto-calculate optimal buffer size for initial ratio
try:
    max_available_memory = scope.get_maximum_available_memory()
    # Calculate optimal buffer size with 95% safety margin
    optimal_initial_buffer = calculate_optimal_buffer_size(max_available_memory, INITIAL_CONFIG['downsampling_ratio'])

    print(f"  Memory usage: {optimal_initial_buffer * INITIAL_CONFIG['downsampling_ratio']:,} / {max_available_memory:,} ({(optimal_initial_buffer * INITIAL_CONFIG['downsampling_ratio']) / max_available_memory * 100:.1f}%)")

    # Update the buffer size in config and legacy constant
    INITIAL_CONFIG['samples_per_buffer'] = optimal_initial_buffer
    SAMPLES_PER_BUFFER = optimal_initial_buffer

except Exception as e:
    print(f"[WARNING] Could not auto-calculate initial buffer size: {e}")
    print(f"  Using default: {INITIAL_CONFIG['samples_per_buffer']:,} samples")

# Calculate initial trigger samples from time values (will be updated after ADC rate is known)
# For now, use a default calculation assuming 1 MSPS
default_adc_rate = 1e6  # 1 MSPS
MAX_PRE_TRIGGER_SAMPLES = time_to_samples(INITIAL_CONFIG['pre_trigger_time'], INITIAL_CONFIG['pre_trigger_time_units'], default_adc_rate)
MAX_POST_TRIGGER_SAMPLES = time_to_samples(INITIAL_CONFIG['post_trigger_time'], INITIAL_CONFIG['post_trigger_time_units'], default_adc_rate)
pre_units_name = TIME_UNIT_NAMES.get(INITIAL_CONFIG['pre_trigger_time_units'], '?')
post_units_name = TIME_UNIT_NAMES.get(INITIAL_CONFIG['post_trigger_time_units'], '?')
print(f"  Initial trigger times: pre={INITIAL_CONFIG['pre_trigger_time']} {pre_units_name}, post={INITIAL_CONFIG['post_trigger_time']} {post_units_name}")
print(f"  Initial trigger samples (at {default_adc_rate/1e6:.1f} MSPS): pre={MAX_PRE_TRIGGER_SAMPLES:,}, post={MAX_POST_TRIGGER_SAMPLES:,}")

print("\nSetting up double buffers...")

# Clear any existing buffers
scope.set_data_buffer(psdk.CHANNEL.A, 0, action=psdk.ACTION.CLEAR_ALL)

# Create buffers
buffer_0 = np.zeros(INITIAL_CONFIG['samples_per_buffer'], dtype=INITIAL_CONFIG['adc_numpy_type'])
buffer_1 = np.zeros(INITIAL_CONFIG['samples_per_buffer'], dtype=INITIAL_CONFIG['adc_numpy_type'])

# Register buffers with hardware (downsampled mode)
print("Registering double buffers...")
register_double_buffers(scope, buffer_0, buffer_1, INITIAL_CONFIG['samples_per_buffer'], INITIAL_CONFIG['adc_data_type'], INITIAL_CONFIG['downsampling_mode'])
print("[OK] Double buffer setup complete")

# ============================================================================
# CONFIGURE TRIGGER (after buffer setup)
# ============================================================================

# Configure simple trigger with default settings (after buffers are registered)
try:
    print(f"[CONFIG] Configuring default trigger: channel=A, threshold={INITIAL_CONFIG['trigger_threshold_adc']} ADC")
    print(f"[CONFIG] Trigger enabled: {INITIAL_CONFIG['trigger_enabled']}, Max post trigger: {MAX_POST_TRIGGER_SAMPLES:,} samples")

    configure_default_trigger(scope, INITIAL_CONFIG['trigger_enabled'], INITIAL_CONFIG['trigger_threshold_adc'], INITIAL_CONFIG['trigger_direction'])

except Exception as e:
    print(f"[WARNING] Error configuring default trigger: {e}")
    print(f"[INFO] Trigger will be disabled - can be enabled later via UI controls")

# ============================================================================
# START HARDWARE STREAMING
# ============================================================================

print("Starting hardware streaming...")
print(f"[STARTUP] Final configuration before streaming:")
print(f"  - Trigger enabled: {INITIAL_CONFIG['trigger_enabled']}")
print(f"  - Trigger threshold: {INITIAL_CONFIG['trigger_threshold_adc']} ADC counts")
print(f"  - Max post trigger: {MAX_POST_TRIGGER_SAMPLES:,} samples")
print(f"  - Buffer size: {INITIAL_CONFIG['samples_per_buffer']:,} samples")


actual_interval = start_hardware_streaming(scope, INITIAL_CONFIG['sample_interval'], INITIAL_CONFIG['time_units'],
                                          MAX_PRE_TRIGGER_SAMPLES, MAX_POST_TRIGGER_SAMPLES,
                                          INITIAL_CONFIG['downsampling_ratio'], INITIAL_CONFIG['downsampling_mode'], INITIAL_CONFIG['trigger_enabled'])

print(f"Actual sample interval: {actual_interval} {INITIAL_CONFIG['time_units']}")
# Calculate sample rate based on the time units
sample_rate = calculate_sample_rate(actual_interval, INITIAL_CONFIG['time_units'])
print(f"Actual sample rate: {sample_rate:.2f} Hz")

# Store hardware ADC sample rate for position tracking
hardware_adc_sample_rate = sample_rate
print(f"Stored hardware ADC sample rate for tracking: {hardware_adc_sample_rate:.2f} Hz")

# Calculate and cache time conversion factor (1 / sample_rate) for efficient time series calculation
# This factor is only recalculated when settings change, not on every plot update
time_conversion_factor = 1.0 / hardware_adc_sample_rate if hardware_adc_sample_rate > 0 else None
print(f"Cached time conversion factor: {time_conversion_factor:.12e} s/sample (1 / {hardware_adc_sample_rate:.2f} Hz)")

# Update initial rate display
initial_msps = sample_rate / 1_000_000
print(f"Initial sample rate: {initial_msps:.3f} MSPS")

# Compute and set initial minimum polling interval based on buffer fill time
downsampled_rate_hz = hardware_adc_sample_rate / DOWNSAMPLING_RATIO
if downsampled_rate_hz > 0:
    min_poll_seconds = SAMPLES_PER_BUFFER / downsampled_rate_hz
    min_poll_ms = min_poll_seconds * 1000.0
    try:
        status_displays['min_poll'].setText(f"{min_poll_ms:.2f} ms")
    except Exception:
        pass

# ============================================================================
# PYQTGRAPH SETUP
# ============================================================================

print("Initializing PyQtGraph...")

# Configure PyQtGraph
pg.setConfigOptions(
    useOpenGL=False,
    antialias=ANTIALIAS,
    useNumba=True,
    enableExperimental=True
)

# Create Qt application (required for PyQtGraph)
app = QtWidgets.QApplication(sys.argv)

# Set global typography
font = app.font()
font.setFamily("Segoe UI")
font.setPointSize(9)
app.setFont(font)

# Set dark background for main application areas
app.setStyleSheet("""
    QMainWindow {
        background-color: #1a1a1a;
    }
    QScrollArea {
        background-color: #1a1a1a;
    }
    QWidget {
        background-color: #1a1a1a;
    }
    /* Global tooltip styling for readable white text on dark background */
    QToolTip {
        background-color: #2b2b2b;
        color: white;
        border: 1px solid #555555;
        padding: 4px 8px;
        font-size: 9pt;
    }
""")

# Create main window with buttons and plot
main_window = pg.QtWidgets.QMainWindow()
main_window.setWindowTitle('PicoScope Direct Streaming - PyQtGraph Downsampled Modes Only')
main_window.resize(1200, 700)

# Create central widget and layout
central_widget = pg.QtWidgets.QWidget()
central_widget.setStyleSheet("background-color: #1a1a1a;")
main_window.setCentralWidget(central_widget)

# Main horizontal layout: plot on left, controls on right
main_layout = pg.QtWidgets.QHBoxLayout()
central_widget.setLayout(main_layout)

# Create control panel using UI components module
# Build control panel using INITIAL_CONFIG
# Create config dict with INITIAL_CONFIG values plus additional runtime values
ui_config = {
    **INITIAL_CONFIG,  # Spread all initial config values
    'psdk': psdk,
    'hardware_adc_sample_rate': hardware_adc_sample_rate,
    # Map to legacy keys that build_control_panel expects (for backward compatibility)
    'DOWNSAMPLING_RATIO': INITIAL_CONFIG['downsampling_ratio'],
    'DOWNSAMPLING_MODE': INITIAL_CONFIG['downsampling_mode'],
    'sample_interval': INITIAL_CONFIG['sample_interval'],
    'time_units': INITIAL_CONFIG['time_units'],
    'SAMPLES_PER_BUFFER': INITIAL_CONFIG['samples_per_buffer'],
    'REFRESH_FPS': INITIAL_CONFIG['refresh_fps'],
    'POLLING_INTERVAL': INITIAL_CONFIG['polling_interval'],
    'TARGET_TIME_WINDOW': INITIAL_CONFIG['target_time_window'],
    'PRE_TRIGGER_TIME': INITIAL_CONFIG['pre_trigger_time'],
    'PRE_TRIGGER_TIME_UNITS': INITIAL_CONFIG['pre_trigger_time_units'],
    'POST_TRIGGER_TIME': INITIAL_CONFIG['post_trigger_time'],
    'POST_TRIGGER_TIME_UNITS': INITIAL_CONFIG['post_trigger_time_units'],
    'TRIGGER_ENABLED': INITIAL_CONFIG['trigger_enabled'],
    'TRIGGER_THRESHOLD_ADC': INITIAL_CONFIG['trigger_threshold_adc'],
    'RAW_DATA_DOWNSAMPLE_ENABLED': INITIAL_CONFIG['raw_data_downsample_enabled'],
    'RAW_DATA_DOWNSAMPLE_MODE': INITIAL_CONFIG['raw_data_downsample_mode'],
    'RAW_DATA_DOWNSAMPLE_FACTOR': INITIAL_CONFIG['raw_data_downsample_factor'],
    'RAW_DATA_MAX_POINTS': INITIAL_CONFIG['raw_data_max_points'],
}
control_widgets = build_control_panel(ui_config)

# Extract widgets from returned dictionary
controls_panel = control_widgets['panel']
mode_combo = control_widgets['mode_combo']
ratio_spinbox = control_widgets['ratio_spinbox']
interval_spinbox = control_widgets['interval_spinbox']
units_combo = control_widgets['units_combo']
hw_buffer_spinbox = control_widgets['hw_buffer_spinbox']
refresh_spinbox = control_widgets['refresh_spinbox']
poll_spinbox = control_widgets['poll_spinbox']
time_window_spinbox = control_widgets['time_window_spinbox']
trigger_enable_checkbox = control_widgets['trigger_enable_checkbox']
trigger_threshold_spinbox = control_widgets['trigger_threshold_spinbox']
trigger_direction_combo = control_widgets['trigger_direction_combo']
pre_trigger_time_spinbox = control_widgets['pre_trigger_time_spinbox']
trigger_units_combo = control_widgets['trigger_units_combo']
post_trigger_time_spinbox = control_widgets['post_trigger_time_spinbox']
raw_display_enable_checkbox = control_widgets['raw_display_enable_checkbox']
raw_display_mode_combo = control_widgets['raw_display_mode_combo']
raw_display_factor_spinbox = control_widgets['raw_display_factor_spinbox']
raw_display_max_points_spinbox = control_widgets['raw_display_max_points_spinbox']
gated_raw_downsample_checkbox = control_widgets['gated_raw_downsample_checkbox']
region_markers_checkbox = control_widgets['region_markers_checkbox']
periodic_log_enable_checkbox = control_widgets['periodic_log_enable_checkbox']
periodic_log_file_edit = control_widgets['periodic_log_file_edit']
periodic_log_browse_button = control_widgets['periodic_log_browse_button']
periodic_log_rate_spinbox = control_widgets['periodic_log_rate_spinbox']
channel_range_combo = control_widgets['channel_range_combo']
channel_coupling_combo = control_widgets['channel_coupling_combo']
channel_probe_combo = control_widgets['channel_probe_combo']
siggen_freq_spinbox = control_widgets['siggen_freq_spinbox']
siggen_pk2pk_spinbox = control_widgets['siggen_pk2pk_spinbox']
siggen_wave_combo = control_widgets['siggen_wave_combo']
apply_button = control_widgets['apply_button']
stop_button = control_widgets['stop_button']
pull_region_raw_button = control_widgets['pull_region_raw_button']

# Note: All control panel widgets are now created via ui_components module
# ============================================================================

# ============= STATUS BAR (TOP OF PLOT AREA) =============
# Create container for plot area with status bar on top
plot_container = pg.QtWidgets.QWidget()
plot_container.setStyleSheet("background-color: #1a1a1a;")
plot_layout = pg.QtWidgets.QVBoxLayout()
plot_container.setLayout(plot_layout)
plot_layout.setContentsMargins(0, 0, 0, 0)  # Remove margins
plot_layout.setSpacing(2)  # Minimal spacing

# Create status bar using UI components
status_bar, status_displays = create_status_bar()

# Create PyQtGraph widget
win = pg.GraphicsLayoutWidget()

# Add status bar and plot to plot container
plot_layout.addWidget(status_bar)
plot_layout.addWidget(win)

# Wrap control panel in scroll area for better fit
control_scroll_area = pg.QtWidgets.QScrollArea()
control_scroll_area.setWidget(controls_panel)
control_scroll_area.setWidgetResizable(True)
control_scroll_area.setHorizontalScrollBarPolicy(
    QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
control_scroll_area.setVerticalScrollBarPolicy(
    QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
control_scroll_area.setFrameShape(pg.QtWidgets.QFrame.Shape.NoFrame)
control_scroll_area.setStyleSheet("background-color: #1a1a1a;")

# Use QSplitter for resizable panels - users can drag the divider to adjust widths
splitter = pg.QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
splitter.addWidget(plot_container)
splitter.addWidget(control_scroll_area)

# Set stretch factors: plot can grow, control panel maintains its size
splitter.setStretchFactor(0, 1)  # Plot area (index 0) can expand
splitter.setStretchFactor(1, 0)  # Control panel (index 1) maintains fixed width

# Set initial sizes: plot gets most space, control panel starts at 320px
# Note: Actual sizes will be calculated from available window width
splitter.setSizes([1000, 320])  # Relative sizes - Qt will scale proportionally

# Set minimum widths
plot_container.setMinimumWidth(400)  # Ensure plot has reasonable minimum
control_scroll_area.setMinimumWidth(320)  # Keep existing minimum for controls

# Style the splitter handle to match dark theme
splitter.setStyleSheet("""
    QSplitter::handle {
        background-color: #444444;
        width: 4px;
    }
    QSplitter::handle:hover {
        background-color: #555555;
    }
""")

# Add splitter to main layout (it takes full space)
main_layout.addWidget(splitter)

# Show the main window
main_window.show()

# Update initial rate displays
status_displays['adc_rate'].setText(f"{initial_msps:.3f} MSPS")
initial_downsampled_msps = initial_msps / DOWNSAMPLING_RATIO
initial_downsampled_khz = initial_downsampled_msps * 1000  # Convert MSPS to kHz
status_displays['downsampled_rate'].setText(f"{initial_downsampled_khz:.3f} kHz")

# Update initial memory requirement display
memory_required = SAMPLES_PER_BUFFER * DOWNSAMPLING_RATIO
status_displays['memory_req'].setText(f"{memory_required:,} samples")

# Update display window with actual size
status_displays['display_window'].setText(f'0.0 s (0 / {PYTHON_RING_BUFFER:,})')

# Update initial min poll interval display (after UI exists)
try:
    down_rate_hz_init = hardware_adc_sample_rate / DOWNSAMPLING_RATIO
    if down_rate_hz_init > 0:
        min_poll_ms_init = (SAMPLES_PER_BUFFER / down_rate_hz_init) * 1000.0
        status_displays['min_poll'].setText(f"{min_poll_ms_init:.2f} ms")
except Exception:
    pass

# Get and display maximum available memory from device (cache for later use)
try:
    max_available_memory = scope.get_maximum_available_memory()
    status_displays['max_memory'].setText(f"{max_available_memory:,} samples")
    print(f"Maximum available device memory: {max_available_memory:,} samples")
    # Cache this value - can't query it while streaming
    cached_max_memory = max_available_memory
except Exception as e:
    print(f"[WARNING] Could not get maximum memory: {e}")
    status_displays['max_memory'].setText("Unknown")
    cached_max_memory = None


# ============================================================================
# APPLY BUTTON HANDLERS
# ============================================================================

def on_apply_button_clicked():
    """
    Handle apply button click - coordinate settings updates.
    Main orchestrator that delegates to helper functions.
    """
    global DOWNSAMPLING_RATIO, DOWNSAMPLING_MODE, sample_interval, time_units
    global SAMPLES_PER_BUFFER, REFRESH_FPS, POLLING_INTERVAL, TARGET_TIME_WINDOW
    global MAX_PRE_TRIGGER_SAMPLES, MAX_POST_TRIGGER_SAMPLES
    global PRE_TRIGGER_TIME, PRE_TRIGGER_TIME_UNITS, POST_TRIGGER_TIME, POST_TRIGGER_TIME_UNITS
    global TRIGGER_ENABLED, TRIGGER_THRESHOLD_ADC, TRIGGER_DIRECTION
    global hardware_adc_sample_rate, PYTHON_RING_BUFFER
    global settings_update_in_progress
    global data_array, x_data, ring_head, ring_filled
    global buffer_0, buffer_1, trigger_fired
    global PERIODIC_LOG_ENABLED, PERIODIC_LOG_FILE, PERIODIC_LOG_RATE

    # Step 1: Collect all UI values
    settings = collect_ui_settings(ratio_spinbox, mode_combo, interval_spinbox, units_combo,
                                  hw_buffer_spinbox, refresh_spinbox, poll_spinbox,
                                  time_window_spinbox, pre_trigger_time_spinbox, trigger_units_combo,
                                  post_trigger_time_spinbox, trigger_units_combo,  # Same combo, passed twice for compatibility
                                  trigger_enable_checkbox, trigger_threshold_spinbox, trigger_direction_combo,
                                  periodic_log_enable_checkbox, periodic_log_file_edit, periodic_log_rate_spinbox,
                                  channel_range_combo, channel_coupling_combo, channel_probe_combo,
                                  siggen_freq_spinbox, siggen_pk2pk_spinbox, siggen_wave_combo)

    # Step 2: Determine what changed
    current_settings = {
        'DOWNSAMPLING_RATIO': DOWNSAMPLING_RATIO,
        'DOWNSAMPLING_MODE': DOWNSAMPLING_MODE,
        'sample_interval': sample_interval,
        'time_units': time_units,
        'SAMPLES_PER_BUFFER': SAMPLES_PER_BUFFER,
        'REFRESH_FPS': REFRESH_FPS,
        'POLLING_INTERVAL': POLLING_INTERVAL,
        'TARGET_TIME_WINDOW': TARGET_TIME_WINDOW,
        'MAX_PRE_TRIGGER_SAMPLES': MAX_PRE_TRIGGER_SAMPLES,
        'MAX_POST_TRIGGER_SAMPLES': MAX_POST_TRIGGER_SAMPLES,
        'PRE_TRIGGER_TIME': PRE_TRIGGER_TIME,
        'PRE_TRIGGER_TIME_UNITS': PRE_TRIGGER_TIME_UNITS,
        'POST_TRIGGER_TIME': POST_TRIGGER_TIME,
        'POST_TRIGGER_TIME_UNITS': POST_TRIGGER_TIME_UNITS,
        'TRIGGER_ENABLED': TRIGGER_ENABLED,
        'TRIGGER_THRESHOLD_ADC': TRIGGER_THRESHOLD_ADC,
        'TRIGGER_DIRECTION': TRIGGER_DIRECTION,
        # Channel and signal generator settings from INITIAL_CONFIG
        'channel_range': INITIAL_CONFIG['channel_range'],
        'channel_coupling': INITIAL_CONFIG['channel_coupling'],
        'channel_probe_scale': INITIAL_CONFIG['channel_probe_scale'],
        'siggen_frequency': INITIAL_CONFIG['siggen_frequency'],
        'siggen_pk2pk': INITIAL_CONFIG['siggen_pk2pk'],
        'siggen_wave_type': INITIAL_CONFIG['siggen_wave_type']
    }

    settings_changed, performance_changed, time_window_changed, trigger_changed, channel_changed, siggen_changed = calculate_what_changed(settings, current_settings)

    # Debug output
    print(f"[DEBUG] Change detection: settings={settings_changed}, performance={performance_changed}, "
          f"time_window={time_window_changed}, trigger={trigger_changed}, channel={channel_changed}, siggen={siggen_changed}")
    if trigger_changed:
        print(f"[DEBUG] Trigger change details:")
        print(f"  enabled: {current_settings['TRIGGER_ENABLED']} -> {settings['new_trigger_enabled']}")
        print(f"  threshold: {current_settings['TRIGGER_THRESHOLD_ADC']} -> {settings['new_trigger_threshold']}")
        print(f"  direction: {current_settings.get('TRIGGER_DIRECTION')} -> {settings['new_trigger_direction']}")
    if channel_changed:
        print(f"[DEBUG] Channel change details (requires restart):")
        if 'new_channel_range' in settings:
            print(f"  channel_range: {current_settings.get('channel_range')} -> {settings['new_channel_range']}")
        if 'new_channel_coupling' in settings:
            print(f"  channel_coupling: {current_settings.get('channel_coupling')} -> {settings['new_channel_coupling']}")
        if 'new_channel_probe_scale' in settings:
            print(f"  channel_probe_scale: {current_settings.get('channel_probe_scale')} -> {settings['new_channel_probe_scale']}")
    if siggen_changed:
        print(f"[DEBUG] SigGen change details (no restart needed):")
        if 'new_siggen_frequency' in settings:
            print(f"  siggen_frequency: {current_settings.get('siggen_frequency')} -> {settings['new_siggen_frequency']}")
        if 'new_siggen_pk2pk' in settings:
            print(f"  siggen_pk2pk: {current_settings.get('siggen_pk2pk')} -> {settings['new_siggen_pk2pk']}")
        if 'new_siggen_wave_type' in settings:
            print(f"  siggen_wave_type: {current_settings.get('siggen_wave_type')} -> {settings['new_siggen_wave_type']}")

    # Step 3: Early exit if nothing changed
    if not (settings_changed or performance_changed or time_window_changed or trigger_changed or siggen_changed):
        print("No changes detected")
        return

    # Step 3.5: Prevent trigger changes if trigger has already fired
    if trigger_changed and trigger_fired:
        print("[ERROR] Cannot change trigger settings after trigger has fired.")
        print("  Please restart streaming manually or change other settings to restart.")
        print("  Trigger changes are disabled to prevent inconsistent behavior.")
        return

    # Step 4: Print what's changing
    print(f"\n[UPDATE] Updating settings:")
    if settings_changed:
        print(f"  Streaming: ratio={settings['new_ratio']} (current: {DOWNSAMPLING_RATIO}), "
              f"mode={settings['new_mode']}, interval={settings['new_interval']}, "
              f"units={settings['new_units']}, hw_buffer={settings['new_buffer_size']} (current: {SAMPLES_PER_BUFFER})")
        # Print trigger times (samples will be calculated during validation)
        pre_units_str = TIME_UNIT_NAMES.get(settings['new_pre_trigger_units'], '?')
        post_units_str = TIME_UNIT_NAMES.get(settings['new_post_trigger_units'], '?')
        print(f"  Trigger times: pre={settings['new_pre_trigger_time']} {pre_units_str}, "
              f"post={settings['new_post_trigger_time']} {post_units_str}")
    if channel_changed:
        print(f"  Channel (requires restart): range={settings.get('new_channel_range', 'unchanged')}, "
              f"coupling={settings.get('new_channel_coupling', 'unchanged')}, "
              f"probe_scale={settings.get('new_channel_probe_scale', 'unchanged')}")
    if performance_changed:
        print(f"  Performance: refresh={settings['new_refresh_fps']} FPS, "
              f"poll={settings['new_poll_interval']*1000:.2f}ms")
    if time_window_changed:
        print(f"  Time Window: {TARGET_TIME_WINDOW:.1f}s -> {settings['new_time_window']:.1f}s")
    if trigger_changed:
        direction_name = {psdk.TRIGGER_DIR.RISING: 'Rising',
                         psdk.TRIGGER_DIR.FALLING: 'Falling',
                         psdk.TRIGGER_DIR.RISING_OR_FALLING: 'Rising or Falling',
                         psdk.TRIGGER_DIR.ABOVE: 'Above',
                         psdk.TRIGGER_DIR.BELOW: 'Below'}.get(settings['new_trigger_direction'], 'Unknown')
        print(f"  Trigger: enabled={settings['new_trigger_enabled']}, threshold={settings['new_trigger_threshold']} ADC, direction={direction_name}")

    # Step 5: Validate and optimize settings
    # Provide current values so validation can detect ratio/buffer changes correctly
    settings['current_ratio'] = DOWNSAMPLING_RATIO
    settings['current_buffer_size'] = SAMPLES_PER_BUFFER
    settings['current_time_window'] = TARGET_TIME_WINDOW
    settings['current_mode'] = DOWNSAMPLING_MODE
    settings['current_interval'] = sample_interval
    settings['current_units'] = time_units
    settings['current_max_pre_trigger'] = MAX_PRE_TRIGGER_SAMPLES
    settings['current_max_post_trigger'] = MAX_POST_TRIGGER_SAMPLES
    settings['PRE_TRIGGER_TIME'] = PRE_TRIGGER_TIME
    settings['PRE_TRIGGER_TIME_UNITS'] = PRE_TRIGGER_TIME_UNITS
    settings['POST_TRIGGER_TIME'] = POST_TRIGGER_TIME
    settings['POST_TRIGGER_TIME_UNITS'] = POST_TRIGGER_TIME_UNITS
    settings['current_trigger_enabled'] = TRIGGER_ENABLED
    settings['current_trigger_threshold'] = TRIGGER_THRESHOLD_ADC
    settings['current_trigger_direction'] = TRIGGER_DIRECTION
    # Add current channel settings for comparison during restart
    settings['current_channel_range'] = INITIAL_CONFIG['channel_range']
    settings['current_channel_coupling'] = INITIAL_CONFIG['channel_coupling']
    settings['current_channel_probe_scale'] = INITIAL_CONFIG['channel_probe_scale']
    is_valid, settings = validate_and_optimize_settings(settings, cached_max_memory, hw_buffer_spinbox, hardware_adc_sample_rate, scope)
    if not is_valid:
        print("[ERROR] Validation failed - settings not applied")
        return  # Validation failed, error already printed

    print(f"[DEBUG] After validation: ratio={settings['new_ratio']}, buffer_size={settings['new_buffer_size']}")

    # Print trigger samples after validation (now available)
    if settings_changed and ('new_max_pre_trigger' in settings and 'new_max_post_trigger' in settings):
        print(f"  Trigger samples: pre={settings['new_max_pre_trigger']:,}, post={settings['new_max_post_trigger']:,}")

    # Step 6: Apply performance settings (no restart needed)
    if performance_changed:
        REFRESH_FPS, POLLING_INTERVAL = apply_performance_settings(settings, timer)

    # Step 6.5: Update periodic logging settings (no restart needed, applies immediately)
    if 'new_periodic_log_enabled' in settings:
        PERIODIC_LOG_ENABLED = settings['new_periodic_log_enabled']
    if 'new_periodic_log_file' in settings:
        PERIODIC_LOG_FILE = settings['new_periodic_log_file']
    if 'new_periodic_log_rate' in settings:
        PERIODIC_LOG_RATE = settings['new_periodic_log_rate']
    if 'new_periodic_log_enabled' in settings or 'new_periodic_log_file' in settings or 'new_periodic_log_rate' in settings:
        if PERIODIC_LOG_ENABLED and PERIODIC_LOG_FILE:
            print(f"[PERIODIC LOG] Settings updated: enabled=True, file={PERIODIC_LOG_FILE}, rate={PERIODIC_LOG_RATE:.2f}s")
        else:
            print(f"[PERIODIC LOG] Logging disabled (enabled={PERIODIC_LOG_ENABLED}, file={PERIODIC_LOG_FILE})")

    # Step 6.6: Apply signal generator settings immediately (no restart needed)
    # Note: Channel settings are handled during restart (Step 8) due to hardware limitations
    if siggen_changed:
        print(f"[UPDATE] Applying signal generator settings (no restart needed)...")
        # Create settings dict with only siggen settings for immediate application
        siggen_settings = {}
        if 'new_siggen_frequency' in settings:
            siggen_settings['new_siggen_frequency'] = settings['new_siggen_frequency']
        if 'new_siggen_pk2pk' in settings:
            siggen_settings['new_siggen_pk2pk'] = settings['new_siggen_pk2pk']
        if 'new_siggen_wave_type' in settings:
            siggen_settings['new_siggen_wave_type'] = settings['new_siggen_wave_type']
        
        success = apply_channel_siggen_settings(siggen_settings, scope)
        if success:
            # Update INITIAL_CONFIG to track current values
            if 'new_siggen_frequency' in settings:
                INITIAL_CONFIG['siggen_frequency'] = settings['new_siggen_frequency']
            if 'new_siggen_pk2pk' in settings:
                INITIAL_CONFIG['siggen_pk2pk'] = settings['new_siggen_pk2pk']
            if 'new_siggen_wave_type' in settings:
                INITIAL_CONFIG['siggen_wave_type'] = settings['new_siggen_wave_type']
            print(f"[UPDATE] Signal generator settings applied successfully")
        else:
            print(f"[ERROR] Failed to apply signal generator settings")

    # Step 7: Handle time window changes
    should_return, new_ring_buffer = apply_time_window(settings, settings_changed, performance_changed,
                                                      data_lock, PYTHON_RING_BUFFER, data_array, x_data,
                                                      ring_head, ring_filled, hardware_adc_sample_rate,
                                                      plot, plot_signal, scope=scope)
    # Don't return early if trigger changed - trigger enable/disable requires restart
    if should_return and not trigger_changed:
        return

    # Step 8: Apply streaming restart if needed
    # Trigger enable/disable requires restart because auto_stop parameter must be set when starting streaming
    needs_restart = settings_changed or trigger_changed

    print(f"[DEBUG] Restart needed: {needs_restart} (settings_changed={settings_changed}, trigger_changed={trigger_changed})")

    if needs_restart:
        # Set global flag to pause streaming thread
        global settings_update_in_progress
        settings_update_in_progress = True
        print("Signaling streaming thread to pause for settings update...")
        time.sleep(SETTINGS_UPDATE_DELAY_SEC)  # Give thread time to see the flag

        # Clear plot to prevent size mismatch errors when buffer size changes
        curve.clear()

        try:
            success, new_rate, new_ring_buffer, new_data_array, new_x_data, new_ring_head, new_ring_filled, new_buffer_0, new_buffer_1 = apply_streaming_restart(
                settings, scope, buffer_0, buffer_1, data_lock,
                PYTHON_RING_BUFFER, data_array, x_data,
                ring_head, ring_filled, hardware_adc_sample_rate,
                settings_update_event,
                efficiency_history, perf_samples_window,
                status_displays, plot_signal, mode_combo, cached_max_memory, plot=plot)
            if success:
                # Update global variables
                DOWNSAMPLING_RATIO = settings['new_ratio']
                DOWNSAMPLING_MODE = settings['new_mode']
                sample_interval = settings['new_interval']
                time_units = settings['new_units']
                SAMPLES_PER_BUFFER = settings['new_buffer_size']
                TARGET_TIME_WINDOW = settings['new_time_window']
                MAX_PRE_TRIGGER_SAMPLES = settings['new_max_pre_trigger']
                MAX_POST_TRIGGER_SAMPLES = settings['new_max_post_trigger']
                PRE_TRIGGER_TIME = settings['new_pre_trigger_time']
                PRE_TRIGGER_TIME_UNITS = settings['new_pre_trigger_units']
                POST_TRIGGER_TIME = settings['new_post_trigger_time']
                POST_TRIGGER_TIME_UNITS = settings['new_post_trigger_units']
                
                # Update UI spinbox to reflect validated pre-trigger time (may have been auto-adjusted)
                # This ensures the UI shows the actual value being used
                pre_trigger_time_spinbox.blockSignals(True)
                pre_trigger_time_spinbox.setValue(PRE_TRIGGER_TIME)
                pre_trigger_time_spinbox.blockSignals(False)
                # Update channel settings in INITIAL_CONFIG if changed
                if channel_changed:
                    if 'new_channel_range' in settings:
                        INITIAL_CONFIG['channel_range'] = settings['new_channel_range']
                    if 'new_channel_coupling' in settings:
                        INITIAL_CONFIG['channel_coupling'] = settings['new_channel_coupling']
                    if 'new_channel_probe_scale' in settings:
                        INITIAL_CONFIG['channel_probe_scale'] = settings['new_channel_probe_scale']
                TRIGGER_ENABLED = settings['new_trigger_enabled']
                TRIGGER_THRESHOLD_ADC = settings['new_trigger_threshold']
                TRIGGER_DIRECTION = settings['new_trigger_direction']
                trigger_fired = False  # Reset trigger fired flag on successful restart
                hardware_adc_sample_rate = new_rate
                PYTHON_RING_BUFFER = new_ring_buffer

                # Update periodic logging settings (if provided)
                if 'new_periodic_log_enabled' in settings:
                    PERIODIC_LOG_ENABLED = settings['new_periodic_log_enabled']
                if 'new_periodic_log_file' in settings:
                    PERIODIC_LOG_FILE = settings['new_periodic_log_file']
                if 'new_periodic_log_rate' in settings:
                    PERIODIC_LOG_RATE = settings['new_periodic_log_rate']
                if PERIODIC_LOG_ENABLED and PERIODIC_LOG_FILE:
                    print(f"[PERIODIC LOG] Logging enabled: file={PERIODIC_LOG_FILE}, rate={PERIODIC_LOG_RATE:.2f}s")
                else:
                    print(f"[PERIODIC LOG] Logging disabled (enabled={PERIODIC_LOG_ENABLED}, file={PERIODIC_LOG_FILE})")

                # Recalculate time conversion factor with new hardware rate
                # This is only done when settings change, not on every plot update
                global time_conversion_factor
                time_conversion_factor = 1.0 / new_rate if new_rate > 0 else None
                print(f"[SETTINGS] Time conversion factor recalculated: {time_conversion_factor:.12e} s/sample (1 / {new_rate:.2f} Hz)")
                # Update ring buffer arrays (critical - must update global references)
                data_array = new_data_array
                x_data = new_x_data
                ring_head = new_ring_head
                ring_filled = new_ring_filled
                # Update hardware buffers (critical - must update global references)
                buffer_0 = new_buffer_0
                buffer_1 = new_buffer_1

                # Update X-range to match new time window (now in time, not samples)
                # X-axis is now time-based (seconds), so range is simply 0 to time_window
                # Y-axis remains fixed (ADC counts), selection window unaffected
                new_time_window = settings['new_time_window']
                plot.setXRange(0, new_time_window, padding=0)
                print(f"[SETTINGS] X-axis range updated to time-based: 0 to {new_time_window:.3f} seconds")
                print(f"[SETTINGS] Time series will be recalculated based on actual hardware ADC rate: {new_rate:.2f} Hz")
        finally:
            # Always clear the flag and signal the thread to resume
            settings_update_in_progress = False
            settings_update_event.set()
            print("Signaled streaming thread to resume")
    else:
        print("[OK] Settings applied (no streaming restart needed)")


def on_stop_button_clicked():
    """Handle stop button click.

    Behaviors:
    - While streaming: acts as an immediate stop (existing behavior).
    - After trigger/auto-stop: acts as a 'Restart' button, restarting streaming
      with current settings but with trigger disabled.
    """
    global stop_streaming, streaming_stopped, trigger_fired
    global TRIGGER_ENABLED, hardware_adc_sample_rate, time_conversion_factor
    global ring_head, ring_filled, data_array

    if not streaming_stopped:
        # Normal stop path while streaming
        print("\n User requested streaming stop - stopping hardware immediately...")
        streaming_stopped = True
        stop_streaming = True
        trigger_fired = False  # Reset trigger fired flag on manual stop

        # Stop hardware immediately
        stop_hardware_streaming(scope)

        # Update UI - disable button and show stopped state
        stop_button.setText('Stopped')
        stop_button.setEnabled(False)  # Disable after stop
        plot_signal.title_updated.emit("Hardware Stopped - Draining Buffers...")
    else:
        # Streaming is already stopped. If this was due to a trigger/auto-stop,
        # treat the button as a "Restart" control.
        if trigger_fired:
            print("\n[RESTART] User requested restart after trigger - restarting without trigger...")
            try:
                # DEBUG: Check if scope handle is still valid
                handle_valid = False
                device_reopened = False
                try:
                    unit_serial = scope.get_unit_serial()
                    print(f"[RESTART DEBUG] Scope handle is valid - Connected to: {unit_serial}")
                    handle_valid = True
                except Exception as e:
                    print(f"[RESTART DEBUG ERROR] Scope handle check failed: {e}")
                    print(f"[RESTART DEBUG ERROR] Attempting to re-open device...")
                    # TODO: Investigate why get_values() in RAW mode requires device re-opening
                    # The handle becomes invalid after get_values() is called, even though
                    # the device is still physically connected. This may be due to the SDK
                    # switching device modes (streaming -> block capture) and not properly
                    # restoring the handle state. Need to investigate if there's a way to
                    # restore handle validity without re-opening, or if we need to avoid
                    # calling get_values() in a way that invalidates the handle.
                    try:
                        # Re-open the device (this resets all settings, so we need to restore them)
                        scope.open_unit(resolution=psdk.RESOLUTION._8BIT)
                        unit_serial = scope.get_unit_serial()
                        print(f"[RESTART DEBUG] Device re-opened successfully - Connected to: {unit_serial}")
                        device_reopened = True
                        handle_valid = True

                        # Restore device settings that were lost during re-open
                        # Use current configuration values instead of hardcoded defaults
                        print("[RESTART] Restoring device settings after re-open...")
                        scope.set_siggen(
                            frequency=INITIAL_CONFIG['siggen_frequency'],
                            pk2pk=INITIAL_CONFIG['siggen_pk2pk'],
                            wave_type=INITIAL_CONFIG['siggen_wave_type']
                        )
                        scope.set_channel(
                            channel=psdk.CHANNEL.A,
                            range=INITIAL_CONFIG['channel_range'],
                            coupling=INITIAL_CONFIG['channel_coupling'],
                            probe_scale=INITIAL_CONFIG['channel_probe_scale']
                        )
                        print("[RESTART] Device settings restored from INITIAL_CONFIG (siggen and channel)")
                    except Exception as reopen_error:
                        print(f"[RESTART DEBUG ERROR] Failed to re-open device: {reopen_error}")
                        print(f"[RESTART ERROR] Cannot restart - device handle is invalid and cannot be restored")
                        return

                if not handle_valid:
                    print(f"[RESTART ERROR] Cannot proceed - handle is invalid")
                    return

                # Disable trigger for the restarted session
                TRIGGER_ENABLED = False
                try:
                    trigger_enable_checkbox.setChecked(False)
                except Exception:
                    # If checkbox is unavailable for any reason, continue safely
                    pass

                # Reset control flags
                stop_streaming = False
                streaming_stopped = False
                trigger_fired = False

                # Reset ring buffer state and clear data
                try:
                    with data_lock:
                        data_array.fill(0)
                        ring_head = 0
                        ring_filled = 0
                except Exception as e:
                    print(f"[RESTART WARNING] Failed to fully reset ring buffer: {e}")

                # Clear old traces from previous trigger session
                global raw_full_data, raw_full_x_data
                try:
                    # Clear the main streaming curve (blue trace)
                    curve.setData([], [])
                    # Clear the red trace (raw data overlay)
                    raw_curve.setData([], [])
                    # Clear the green trace (gated raw data)
                    gated_raw_curve.setData([], [])
                    # Clear cached raw data arrays
                    raw_full_data = None
                    raw_full_x_data = None
                    print("[RESTART] Cleared all old traces from plot (blue, red, and green)")
                except Exception as e:
                    print(f"[RESTART WARNING] Failed to clear plot traces: {e}")

                # After get_values() in RAW mode, device may be in block capture mode
                # Follow the same pattern as apply_streaming_restart: explicitly stop, clear, then re-register
                print("[RESTART] Stopping device (ensuring clean state)...")
                stop_hardware_streaming(scope)  # Explicit stop, even if already stopped
                time.sleep(0.1)  # Brief delay for state transition

                # Clear hardware buffers (this clears any RAW mode buffers from raw data pull)
                print("[RESTART] Clearing all buffers (including RAW mode buffers)...")
                clear_hardware_buffers(scope)

                # Re-register streaming buffers (device needs to be back in streaming mode)
                # This is critical: after get_values() in RAW mode, we must re-register streaming buffers
                print(f"[RESTART] Re-registering streaming buffers ({SAMPLES_PER_BUFFER:,} samples, {DOWNSAMPLING_MODE} mode)...")
                register_double_buffers(scope, buffer_0, buffer_1, SAMPLES_PER_BUFFER, ADC_DATA_TYPE, DOWNSAMPLING_MODE)

                # Configure trigger as disabled
                configure_default_trigger(scope, TRIGGER_ENABLED, TRIGGER_THRESHOLD_ADC, TRIGGER_DIRECTION)

                # Get actual sample interval BEFORE starting streaming
                # This ensures we know the actual rate before configuring post-trigger samples
                unit_to_seconds = TIME_UNIT_TO_SECONDS.get(time_units, 1.0)
                requested_interval_s = sample_interval * unit_to_seconds
                nearest_interval_dict = scope.get_nearest_sampling_interval(requested_interval_s)
                actual_interval_s = nearest_interval_dict['actual_sample_interval']
                actual_interval = actual_interval_s / unit_to_seconds  # Convert back to original units
                
                # Calculate actual sample rate
                sample_rate = calculate_sample_rate(actual_interval, time_units)
                hardware_adc_sample_rate = sample_rate
                time_conversion_factor = 1.0 / hardware_adc_sample_rate if hardware_adc_sample_rate > 0 else None
                print(f"[RESTART] Actual sample interval: {actual_interval} {time_units}")
                print(f"[RESTART] Sample rate: {sample_rate:.2f} Hz")
                print(f"[RESTART] Time conversion factor: {time_conversion_factor:.12e} s/sample")
                
                # Reset post-trigger samples to initial value when restarting without trigger
                # When trigger is disabled, maxPostTriggerSamples is used as "maximum samples to store"
                # We should reset to initial value (1.0 ms) to avoid memory issues from previous triggered runs
                global MAX_POST_TRIGGER_SAMPLES, MAX_PRE_TRIGGER_SAMPLES, POST_TRIGGER_TIME, POST_TRIGGER_TIME_UNITS
                if not TRIGGER_ENABLED:
                    # Reset to initial post-trigger time (1.0 ms) and recalculate based on actual rate
                    initial_post_trigger_time = INITIAL_CONFIG['post_trigger_time']  # 1.0 ms
                    initial_post_trigger_units = INITIAL_CONFIG['post_trigger_time_units']  # TIME_UNIT.MS
                    MAX_POST_TRIGGER_SAMPLES = time_to_samples(initial_post_trigger_time, initial_post_trigger_units, sample_rate)
                    POST_TRIGGER_TIME = initial_post_trigger_time
                    POST_TRIGGER_TIME_UNITS = initial_post_trigger_units
                    print(f"[RESTART] Reset post-trigger to initial value: {initial_post_trigger_time} {TIME_UNIT_NAMES.get(initial_post_trigger_units, '?')} = {MAX_POST_TRIGGER_SAMPLES:,} samples (at {sample_rate/1e6:.3f} MSPS)")
                    
                    # Also reset pre-trigger to initial value (0.0 ms = 0 samples)
                    initial_pre_trigger_time = INITIAL_CONFIG['pre_trigger_time']  # 0.0 ms
                    initial_pre_trigger_units = INITIAL_CONFIG['pre_trigger_time_units']  # TIME_UNIT.MS
                    MAX_PRE_TRIGGER_SAMPLES = time_to_samples(initial_pre_trigger_time, initial_pre_trigger_units, sample_rate)
                    print(f"[RESTART] Reset pre-trigger to initial value: {initial_pre_trigger_time} {TIME_UNIT_NAMES.get(initial_pre_trigger_units, '?')} = {MAX_PRE_TRIGGER_SAMPLES:,} samples")
                
                # Update status bar displays BEFORE starting streaming
                try:
                    adc_msps = sample_rate / 1_000_000
                    status_displays['adc_rate'].setText(f"{adc_msps:.3f} MSPS")

                    downsampled_rate_hz = hardware_adc_sample_rate / DOWNSAMPLING_RATIO
                    downsampled_khz = downsampled_rate_hz / 1000.0
                    status_displays['downsampled_rate'].setText(f"{downsampled_khz:.3f} kHz")

                    if downsampled_rate_hz > 0:
                        min_poll_seconds = SAMPLES_PER_BUFFER / downsampled_rate_hz
                        min_poll_ms = min_poll_seconds * 1000.0
                        status_displays['min_poll'].setText(f"{min_poll_ms:.2f} ms")
                except Exception as e:
                    print(f"[RESTART WARNING] Failed to update status displays: {e}")

                # NOW start hardware streaming (LAST, after all settings are configured)
                print("[RESTART] Starting hardware streaming with trigger disabled...")
                actual_interval = start_hardware_streaming(
                    scope,
                    sample_interval,
                    time_units,
                    MAX_PRE_TRIGGER_SAMPLES,
                    MAX_POST_TRIGGER_SAMPLES,
                    DOWNSAMPLING_RATIO,
                    DOWNSAMPLING_MODE,
                    TRIGGER_ENABLED
                )
                print(f"[RESTART] Hardware streaming started successfully")

                # Update plot title and stop button UI
                plot_signal.title_updated.emit(
                    f"Real-time Streaming Data - {DOWNSAMPLING_RATIO}:1 {mode_combo.currentText()} (Restarted, trigger disabled)"
                )
                stop_button.setText('Stop Streaming')
                stop_button.setEnabled(True)

                # Start new data acquisition thread
                stream_thread = threading.Thread(
                    target=streaming_thread,
                    args=(hardware_adc_sample_rate,),
                    daemon=True
                )
                stream_thread.start()
                print("[RESTART] Data acquisition thread restarted successfully")
            except Exception as e:
                print(f"[RESTART ERROR] Failed to restart streaming after trigger: {e}")
                import traceback
                traceback.print_exc()
                plot_signal.title_updated.emit("Error Restarting After Trigger - See Console")
        else:
            # Already stopped and no trigger context; nothing to do.
            print("[INFO] Stop/Restart button clicked, but streaming is already stopped and no trigger restart is pending.")

# Connect button handlers
apply_button.clicked.connect(on_apply_button_clicked)
stop_button.clicked.connect(on_stop_button_clicked)

# Create plot item with performance optimizations
plot = win.addPlot(title=f"Real-time Streaming Data - {DOWNSAMPLING_RATIO}:1 {mode_combo.currentText()} - Initializing...")
plot.setLabel('left', 'Amplitude', units='ADC Counts')
plot.setLabel('bottom', 'Time', units='s')
plot.showGrid(x=True, y=True, alpha=0.3)

# Setup plot optimizations using helper function
data_processing.setup_plot_optimizations(plot, TARGET_TIME_WINDOW, hardware_adc_sample_rate, scope=scope)

# Create plot curves using helper functions
curve = data_processing.create_plot_curve(plot, ANTIALIAS)
raw_curve = data_processing.create_raw_data_curve(plot, ANTIALIAS)

# Note: X-axis range is already set in setup_plot_optimizations()
# Y-axis is constrained to ADC limits and locked via setLimits()
# No auto-range needed since we set explicit ranges

# Create a separate green curve for gated raw data (region-selected portion)
gated_raw_curve = plot.plot(
    pen=pg.mkPen(color='green', width=1),       # Green line connecting points
    symbol='x',                                  # X symbol for gated raw data points
    symbolSize=4,                                # Larger size for better visibility
    symbolBrush='green',                         # Green color for gated raw data
    symbolPen=pg.mkPen(color='green', width=1), # Green border
    antialias=ANTIALIAS,                          # Antialiasing setting
    clipToView=True,                              # Only render visible data
    autoDownsample=False,                         # Manual downsampling control
    name='Gated Raw Data'                         # Legend name
)

# Set z-values to control visual layering (higher values draw on top)
# Green trace at back (bottom layer), red trace in middle, blue trace on top
gated_raw_curve.setZValue(0)  # Green trace at back
raw_curve.setZValue(1)        # Red trace in middle
curve.setZValue(2)            # Blue trace on top

# ============================================================================
# INTERACTIVE REGION SELECTION (LinearRegionItem)
# ============================================================================

# Add a vertical selection band on the X-axis using PyQtGraph's LinearRegionItem.
# This operates purely on the already-downsampled plot data for performance.
region = pg.LinearRegionItem()
region.setZValue(5)  # Ensure region is drawn above the curve
plot.addItem(region)

# Initialize region to 25% of the X range at the start; user can drag/resize as needed.
# Get the plot's X range to calculate 25% of it
try:
    x_range = plot.viewRange()[0]  # Get (x_min, x_max) from plot
    x_min, x_max = x_range
    x_span = x_max - x_min
    region_width = x_span * 0.25  # 25% of X range
    region_start = x_min  # Start at beginning of plot
    region_end = region_start + region_width
except (AttributeError, IndexError, TypeError):
    # Fallback if plot range not available yet - use ring buffer size
    try:
        initial_max_x = float(PYTHON_RING_BUFFER)
        region_width = initial_max_x * 0.25
    except NameError:
        region_width = 1000.0 * 0.25  # Fallback to 25% of 1000
    region_start = 0.0
    region_end = region_start + region_width

region.setRegion((region_start, region_end))
print(f"[REGION] Selection window initialized: {region_start:.0f} to {region_end:.0f} ({region_width:.0f} samples, 25% of X range)")

# Note: Region selection markers are used only for selecting gated raw area
# No on-graph readout or console printouts needed

# ============================================================================
# DATA STORAGE AND THREADING SETUP
# ============================================================================

print("Setting up data management...")

# Calculate initial ring buffer size based on time window
# Ring buffer size = (time_window × ADC_rate) / ratio
# Use minimum of MIN_RING_BUFFER_SAMPLES for smooth plotting (scatter plot doesn't need many points)
calculated_buffer = int((TARGET_TIME_WINDOW * hardware_adc_sample_rate) / DOWNSAMPLING_RATIO)
PYTHON_RING_BUFFER = max(MIN_RING_BUFFER_SAMPLES, calculated_buffer)
print(f"Initial ring buffer size: {PYTHON_RING_BUFFER:,} downsampled samples")
print(f"  Time window: {TARGET_TIME_WINDOW:.1f}s, ADC rate: {hardware_adc_sample_rate:.2f} Hz, Ratio: {DOWNSAMPLING_RATIO}:1")

# Pre-allocate arrays
x_data = np.arange(PYTHON_RING_BUFFER, dtype=np.float32)           # X-axis sample indices
data_array = np.zeros(PYTHON_RING_BUFFER, dtype=np.float32)       # Y-axis data circular buffer
# Ring buffer state
ring_head = 0                    # Next write index (0..PYTHON_RING_BUFFER-1)
ring_filled = 0                  # Number of valid samples in buffer (<= PYTHON_RING_BUFFER)

# Note: time_conversion_factor is initialized above after hardware_adc_sample_rate is known

# Threading and synchronization variables
current_buffer_index = 0       # Active hardware buffer index
data_lock = threading.Lock()   # Thread-safe access
stop_streaming = False         # Stop streaming flag
data_updated = False           # New data available flag
streaming_stopped = False      # User stopped streaming flag
trigger_fired = False          # Flag indicating trigger has fired and stopped streaming
trigger_at_sample = 0           # Sample index where trigger occurred (for time alignment)
settings_update_in_progress = False  # Settings update in progress flag
settings_update_event = threading.Event()  # Event to coordinate settings updates

# Performance tracking variables
perf_samples_window = deque()  # (timestamp, n_samples)
perf_window_secs = 1.0
perf_script_hz = 0.0
perf_plot_last_time = time.perf_counter()
perf_plot_fps = 0.0

# Efficiency tracking for jitter calculation
efficiency_history = deque(maxlen=50)  # Last 50 efficiency measurements
efficiency_avg = 0.0
efficiency_jitter = 0.0

# Efficiency display update throttling (limit to ~10 FPS to reduce UI overhead)
EFFICIENCY_UPDATE_INTERVAL_SEC = 0.1  # Update max every 100ms (10 FPS)
efficiency_last_update_time = 0.0
pending_efficiency_avg = 0.0
pending_efficiency_jitter = 0.0
pending_efficiency_status = "initializing"

# Cached raw data for region-based pulls
raw_full_data = None
raw_full_x_data = None

# Create signal object for thread-safe communication
plot_signal = PlotUpdateSignal()


# ============================================================================
# NUMBA-OPTIMIZED RING BUFFER UPDATE FUNCTION
# ============================================================================

@njit
def update_ring_buffer_vectorized(new_data, data_array, ring_head, ring_filled, buffer_size):
    """
    Numba-optimized function to update ring buffer with new samples using vectorized operations.

    This replaces the slow Python loop with fast compiled code that processes entire batches
    at once using NumPy array operations.

    Args:
        new_data: NumPy array of new samples to add (1D float32 array)
        data_array: Ring buffer array to update (modified in place)
        ring_head: Current head position in ring buffer
        ring_filled: Current number of filled samples
        buffer_size: Total size of ring buffer

    Returns:
        tuple: (new_ring_head, new_ring_filled) - updated buffer state
    """
    n_samples = len(new_data)

    if n_samples == 0:
        return ring_head, ring_filled

    # Ensure ring_head is within valid range (safety check)
    if ring_head < 0 or ring_head >= buffer_size:
        ring_head = ring_head % buffer_size

    # Calculate how many samples we can write before wrapping
    space_until_wrap = buffer_size - ring_head
    samples_to_end = min(n_samples, space_until_wrap)

    # Write first segment (up to end of buffer)
    # Use explicit loop for first segment to ensure exact size match (Numba will optimize this)
    for i in range(samples_to_end):
        data_array[ring_head + i] = new_data[i]

    # If we need to wrap around, write remaining samples at the beginning
    if n_samples > samples_to_end:
        remaining_samples = n_samples - samples_to_end
        # Use explicit loop for wrap-around segment
        for i in range(remaining_samples):
            data_array[i] = new_data[samples_to_end + i]

    # Update ring head (wraps automatically with modulo)
    new_ring_head = (ring_head + n_samples) % buffer_size

    # Update filled count (capped at buffer_size)
    new_ring_filled = min(ring_filled + n_samples, buffer_size)

    return new_ring_head, new_ring_filled


# ============================================================================
# STREAMING DATA ACQUISITION THREAD
# ============================================================================

def create_log_metadata(hardware_adc_rate, downsampling_ratio, downsampling_mode,
                        sample_interval, time_units, log_rate, channel='A'):
    """
    Create metadata dictionary for log file.

    Args:
        hardware_adc_rate: Hardware ADC sampling rate (Hz)
        downsampling_ratio: Downsampling ratio
        downsampling_mode: Downsampling mode (DECIMATE or AVERAGE)
        sample_interval: Sample interval value
        time_units: Time units (NS, US, MS, S)
        log_rate: Logging rate in seconds
        channel: Channel identifier

    Returns:
        dict: Metadata dictionary
    """
    # Convert time units to string
    time_unit_names = {
        psdk.TIME_UNIT.NS: 'ns',
        psdk.TIME_UNIT.US: 'μs',
        psdk.TIME_UNIT.MS: 'ms',
        psdk.TIME_UNIT.S: 's'
    }
    time_unit_str = time_unit_names.get(time_units, 'unknown')

    # Convert downsampling mode to string
    mode_names = {
        psdk.RATIO_MODE.DECIMATE: 'DECIMATE',
        psdk.RATIO_MODE.AVERAGE: 'AVERAGE'
    }
    mode_str = mode_names.get(downsampling_mode, 'unknown')

    # Calculate effective downsampled rate
    downsampled_rate = hardware_adc_rate / downsampling_ratio if downsampling_ratio > 0 else 0

    metadata = {
        'log_start_time': datetime.now().isoformat(),
        'hardware_settings': {
            'channel': channel,
            'adc_sample_rate_hz': float(hardware_adc_rate),
            'adc_sample_rate_msps': float(hardware_adc_rate / 1e6),
            'sample_interval': float(sample_interval),
            'sample_interval_units': time_unit_str
        },
        'downsampling_settings': {
            'ratio': int(downsampling_ratio),
            'mode': mode_str,
            'downsampled_rate_hz': float(downsampled_rate),
            'downsampled_rate_khz': float(downsampled_rate / 1e3)
        },
        'logging_settings': {
            'log_rate_seconds': float(log_rate),
            'sample_selection': 'first_sample'  # Which sample from batch is logged
        },
        'data_format': {
            'file_type': 'numpy_array',
            'data_type': 'float32',
            'units': 'ADC_counts'
        }
    }
    return metadata


def save_log_metadata(file_path, metadata):
    """
    Save metadata to a JSON file alongside the .npy file.

    Args:
        file_path: Path to .npy file
        metadata: Metadata dictionary to save
    """
    try:
        # Create metadata file path (same name, .json extension)
        metadata_path = os.path.splitext(file_path)[0] + '_metadata.json'
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
    except Exception as e:
        print(f"[PERIODIC LOG] Error saving metadata to {metadata_path}: {e}")


def update_log_metadata_sample_count(file_path, sample_count):
    """
    Update the sample count in the metadata file.

    Args:
        file_path: Path to .npy file
        sample_count: Current number of samples logged
    """
    try:
        metadata_path = os.path.splitext(file_path)[0] + '_metadata.json'
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            metadata['logging_stats'] = {
                'total_samples_logged': int(sample_count),
                'last_update_time': datetime.now().isoformat()
            }
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
    except Exception as e:
        print(f"[PERIODIC LOG] Error updating metadata: {e}")


def append_sample_to_log_file(file_path, sample_value, metadata=None, is_first_sample=False):
    """
    Append a single sample value to a numpy array file.
    If file doesn't exist, creates it. If it exists, loads and appends.

    Args:
        file_path: Path to .npy file
        sample_value: Single sample value to append (scalar or array)
        metadata: Optional metadata dictionary (saved if is_first_sample is True)
        is_first_sample: If True, save metadata file
    """
    try:
        if os.path.exists(file_path):
            # Load existing array
            existing_data = np.load(file_path)
            # Append new sample
            new_data = np.append(existing_data, sample_value)
            # Save back
            np.save(file_path, new_data)
            # Update sample count in metadata
            update_log_metadata_sample_count(file_path, len(new_data))
        else:
            # Create new array with first sample
            np.save(file_path, np.array([sample_value]))
            # Save metadata if provided
            if metadata is not None:
                save_log_metadata(file_path, metadata)
            else:
                # Update sample count even if metadata wasn't provided
                update_log_metadata_sample_count(file_path, 1)
    except Exception as e:
        print(f"[PERIODIC LOG] Error writing to {file_path}: {e}")


def streaming_thread(hardware_adc_rate):
    """
    Background thread for continuous data acquisition from PicoScope hardware.

    Args:
        hardware_adc_rate: The actual ADC sampling rate (Hz)
    """
    global current_buffer_index, stop_streaming, data_updated, streaming_stopped, ring_head, ring_filled, perf_script_hz
    global efficiency_history, efficiency_avg, efficiency_jitter, hardware_adc_sample_rate, DOWNSAMPLING_RATIO
    global TRIGGER_EVENT_COUNT, trigger_fired, PERIODIC_LOG_FILE, PERIODIC_LOG_RATE
    global sample_interval, time_units

    print("Starting data acquisition thread...")

    # Wait for hardware to be ready
    print("Waiting for hardware to initialize...")
    try:
        scope.is_ready()
        print("[OK] Hardware initialization complete")
        print(f"Streaming thread - hardware ADC rate: {hardware_adc_rate:.2f} Hz")

        # Update plot title
        plot_signal.title_updated.emit(f"Real-time Streaming Data - {DOWNSAMPLING_RATIO}:1 {mode_combo.currentText()}")
    except Exception as e:
        print(f"[WARNING] Hardware initialization failed: {e}")
        plot_signal.title_updated.emit("Real-time Streaming Data - Initialization Failed")
        return

    # Track previous sample count to detect trigger (when samples go from >0 to 0)
    prev_n_samples = 0
    was_streaming = False  # Track if we ever had samples (to know we were streaming)

    # Periodic logging state
    last_log_time = time.perf_counter()
    log_metadata_created = False  # Track if metadata has been created for current log file

    while not stop_streaming:
        try:
            # Check if settings update is in progress
            if settings_update_in_progress:
                print("Streaming thread: Settings update in progress, pausing...")
                settings_update_event.wait()  # Wait for settings update to complete
                settings_update_event.clear()  # Clear the event for next time
                print("Streaming thread: Settings update complete, resuming...")
                continue

            # Poll hardware for accumulated samples (downsampled mode)
            info = scope.get_streaming_latest_values(
                channel=psdk.CHANNEL.A,
                ratio_mode=DOWNSAMPLING_MODE,
                data_type=ADC_DATA_TYPE
            )

            n_samples = info['no of samples']
            buffer_index = info['Buffer index'] % 2
            start_index = info.get('start index', 0)  # Get start index from hardware
            triggered = info.get('triggered?', False)  # Check if trigger event occurred
            trigger_at = info.get('triggered at', 0)  # Sample index where trigger occurred
            auto_stopped = info.get('auto stopped?', False)  # Check if hardware auto-stopped

            # Track if we were streaming (had samples > 0 at some point)
            if n_samples > 0:
                was_streaming = True

            # Detect trigger: when hardware auto-stops and trigger is enabled
            # The 'auto stopped?' flag indicates hardware stopped (likely due to trigger when trigger is enabled)
            if TRIGGER_ENABLED and n_samples == 0 and auto_stopped:
                # Only treat as trigger if we were previously streaming (to avoid false positives at startup)
                if was_streaming:
                    global trigger_at_sample
                    TRIGGER_EVENT_COUNT += 1
                    trigger_fired = True  # Mark that trigger has fired
                    trigger_at_sample = trigger_at  # Store trigger sample index for time alignment
                    print(f"[TRIGGER] Trigger event #{TRIGGER_EVENT_COUNT} detected @ sample {trigger_at:,}")
                    print(f"[TRIGGER] Hardware auto-stop engaged - streaming stopped by trigger")

                    # Emit signal to update UI (thread-safe)
                    plot_signal.trigger_fired.emit(trigger_at)

                    # Cleanly exit the loop on trigger; hardware auto-stop will have engaged.
                    streaming_stopped = True
                    stop_streaming = True
                    break
                # else: Auto-stopped but we never had samples - startup condition, ignore

            # Also check the triggered flag if it's set (backup detection method)
            elif TRIGGER_ENABLED and n_samples == 0 and triggered and was_streaming:
                # Trigger flag is set and we were streaming - treat as trigger event
                TRIGGER_EVENT_COUNT += 1
                trigger_fired = True
                print(f"[TRIGGER] Trigger event #{TRIGGER_EVENT_COUNT} detected via triggered flag @ sample {trigger_at:,}")
                plot_signal.trigger_fired.emit(trigger_at)
                streaming_stopped = True
                stop_streaming = True
                break

            # Update previous sample count for next iteration
            prev_n_samples = n_samples

            if n_samples > 0:
                # Select the correct hardware buffer
                current_buffer = buffer_0 if buffer_index == 0 else buffer_1

                # Get new data from buffer (downsampled mode - continuous data)
                new_data = current_buffer[start_index:start_index + n_samples].astype(np.float32)

                # Periodic logging: append first sample from new_data if logging is enabled and time has elapsed
                if PERIODIC_LOG_ENABLED and PERIODIC_LOG_FILE and len(new_data) > 0:
                    current_time = time.perf_counter()
                    time_since_last_log = current_time - last_log_time
                    if time_since_last_log >= PERIODIC_LOG_RATE:
                        # Take first sample from new_data (simplest approach)
                        sample_to_log = float(new_data[0])

                        # Check if this is the first sample (file doesn't exist yet)
                        is_first_sample = not os.path.exists(PERIODIC_LOG_FILE)

                        # Create metadata if this is the first sample or if metadata hasn't been created yet
                        metadata = None
                        if is_first_sample or not log_metadata_created:
                            metadata = create_log_metadata(
                                hardware_adc_rate=hardware_adc_sample_rate,
                                downsampling_ratio=DOWNSAMPLING_RATIO,
                                downsampling_mode=DOWNSAMPLING_MODE,
                                sample_interval=sample_interval,
                                time_units=time_units,
                                log_rate=PERIODIC_LOG_RATE,
                                channel='A'
                            )
                            log_metadata_created = True

                        # Append sample with metadata
                        append_sample_to_log_file(PERIODIC_LOG_FILE, sample_to_log,
                                                 metadata=metadata, is_first_sample=is_first_sample)
                        last_log_time = current_time

                # Track buffer positions
                streaming_thread.last_end_index = start_index + n_samples
                streaming_thread.last_buffer_index = buffer_index

                # Update script ingest rate tracking FIRST (used for efficiency)
                now_ts = time.perf_counter()
                perf_samples_window.append((now_ts, int(n_samples)))
                window_start = now_ts - perf_window_secs
                while perf_samples_window and perf_samples_window[0][0] < window_start:
                    perf_samples_window.popleft()
                if perf_samples_window and (perf_samples_window[-1][0] - perf_samples_window[0][0]) > 0:
                    window_duration = perf_samples_window[-1][0] - perf_samples_window[0][0]
                    samples_in_window = sum(s for _, s in perf_samples_window)
                    with data_lock:
                        perf_script_hz = samples_in_window / window_duration
                else:
                    with data_lock:
                        perf_script_hz = 0.0

                # Calculate efficiency: actual sample rate vs expected downsampled rate
                expected_rate = hardware_adc_sample_rate / DOWNSAMPLING_RATIO  # Expected samples per second
                if expected_rate > 0 and perf_script_hz > 0:
                    efficiency = (perf_script_hz / expected_rate) * 100
                else:
                    efficiency = 0.0

                # Track efficiency history for jitter calculation
                efficiency_history.append(efficiency)

                # Calculate average efficiency and jitter (standard deviation)
                if len(efficiency_history) >= 10:  # Need at least 10 samples for meaningful stats
                    efficiency_avg = np.mean(efficiency_history)
                    efficiency_jitter = np.std(efficiency_history)

                    # Determine system status based on efficiency and jitter
                    if efficiency_avg >= 95 and efficiency_jitter < 5:
                        status = "excellent"  # Green - Excellent performance
                    elif efficiency_avg >= 90 and efficiency_jitter < 10:
                        status = "good"       # Green - Good performance
                    elif efficiency_avg >= 80 or efficiency_jitter < 15:
                        status = "warning"    # Yellow - Minor issues
                    else:
                        status = "critical"   # Red - Falling behind
                else:
                    # Not enough data yet
                    efficiency_avg = efficiency
                    efficiency_jitter = 0.0
                    status = "initializing"

                # Throttle efficiency display updates to reduce UI overhead
                # Only update every EFFICIENCY_UPDATE_INTERVAL_SEC seconds (10 FPS max)
                now_ts = time.perf_counter()
                global efficiency_last_update_time, pending_efficiency_avg, pending_efficiency_jitter, pending_efficiency_status
                time_since_last_update = now_ts - efficiency_last_update_time

                # Store pending values for throttled update
                pending_efficiency_avg = efficiency_avg
                pending_efficiency_jitter = efficiency_jitter
                pending_efficiency_status = status

                # Only emit signal if enough time has passed
                if time_since_last_update >= EFFICIENCY_UPDATE_INTERVAL_SEC:
                    plot_signal.efficiency_updated.emit(efficiency_avg, efficiency_jitter, status)
                    efficiency_last_update_time = now_ts

                # Skip if no new samples
                if new_data.size == 0:
                    time.sleep(POLLING_INTERVAL)
                    continue

                # Process new data through circular buffer using Numba-optimized function
                with data_lock:
                    # Use vectorized Numba-compiled function for fast batch processing
                    ring_head, ring_filled = update_ring_buffer_vectorized(
                        new_data, data_array, ring_head, ring_filled, PYTHON_RING_BUFFER
                    )

                    # Update display elements
                    plot_signal.buffer_status_updated.emit(ring_filled, PYTHON_RING_BUFFER)

                    # Flag plot update
                    data_updated = True

                # Handle buffer switching
                if buffer_index != current_buffer_index:
                    current_buffer_index = buffer_index
                    new_buffer_index = 1 - buffer_index
                    new_buffer = buffer_0 if new_buffer_index == 0 else buffer_1

                    # Re-register buffer (single buffer for switching)
                    scope.set_data_buffer(psdk.CHANNEL.A, SAMPLES_PER_BUFFER, buffer=new_buffer,
                                        action=psdk.ACTION.ADD, datatype=ADC_DATA_TYPE, ratio_mode=DOWNSAMPLING_MODE)

            time.sleep(POLLING_INTERVAL)

        except Exception as e:
            print(f"Error in streaming thread: {e}")
            break

    # Handle streaming stopped by user (Option A: Clean Stop - drain buffers)
    if streaming_stopped:
        # Use centralized buffer draining function
        total_drained, ring_head, ring_filled = drain_remaining_buffers(
            scope, buffer_0, buffer_1, data_array, ring_head, ring_filled,
            PYTHON_RING_BUFFER, data_lock, plot_signal, DOWNSAMPLING_MODE, ADC_DATA_TYPE
        )
        # Note: ring_head and ring_filled are updated from return values

        # DEBUG: Check handle validity after drain completes
        try:
            unit_serial = scope.get_unit_serial()
            print(f"[STREAMING THREAD DEBUG] Handle valid after drain - Connected to: {unit_serial}")
        except Exception as e:
            print(f"[STREAMING THREAD DEBUG ERROR] Handle invalid after drain: {e}")

    print("Data acquisition thread stopped")

# ============================================================================
# PYQTGRAPH PLOT UPDATE FUNCTION
# ============================================================================

def update_plot():
    """
    Update the PyQtGraph plot with latest streaming data.
    """
    global data_updated, perf_plot_last_time, perf_plot_fps, time_conversion_factor

    # Use helper function to update plot with cached time conversion factor
    # Factor is only recalculated when settings change, not on every plot update
    plot_updated = data_processing.update_plot(curve, data_array, ring_head, ring_filled, PYTHON_RING_BUFFER,
                              DOWNSAMPLING_RATIO, data_lock, data_updated, time_conversion_factor)

    if plot_updated:
        # Update plot FPS timing (overlay removed to reduce UI overhead)
        now = time.perf_counter()
        dt = now - perf_plot_last_time
        if dt > 0:
            perf_plot_fps = 1.0 / dt
        perf_plot_last_time = now


# Region selection handler removed - markers are used only for gated raw selection
# No readout or printouts needed

def update_buffer_status_wrapper(current, total):
    """Update the display window time and sample count in top bar"""
    update_buffer_status(current, total, DOWNSAMPLING_RATIO, hardware_adc_sample_rate, status_displays)

# ============================================================================
# QT TIMER FOR PLOT UPDATES
# ============================================================================

# Connect signals to slots for thread-safe communication
plot_signal.title_updated.connect(plot.setTitle)
plot_signal.buffer_status_updated.connect(lambda current, total: update_buffer_status_wrapper(current, total))

# Region selection markers are used only for gated raw selection
# No handler needed - on_pull_region_raw_clicked() reads region directly

def update_efficiency_display_wrapper(efficiency, jitter, status):
    """
    Update the efficiency display with color coding based on both efficiency and jitter.

    Args:
        efficiency: Average efficiency percentage
        jitter: Standard deviation of efficiency (consistency metric)
        status: Overall status ('excellent', 'good', 'warning', 'critical', 'initializing')
    """
    update_efficiency_display(efficiency, jitter, status, status_displays)

plot_signal.efficiency_updated.connect(update_efficiency_display_wrapper)

def on_trigger_fired(trigger_at):
    """
    Handle trigger fired event - update UI to show trigger state and automatically pull raw data.

    Args:
        trigger_at: Sample index where trigger occurred
    """
    global streaming_stopped
    print(f"[UI] Trigger fired - updating stop button to 'Restart' state")

    # DEBUG: Check handle validity immediately when trigger fires
    try:
        unit_serial = scope.get_unit_serial()
        print(f"[TRIGGER DEBUG] Handle valid when trigger fired - Connected to: {unit_serial}")
    except Exception as e:
        print(f"[TRIGGER DEBUG ERROR] Handle invalid when trigger fired: {e}")

    try:
        # Update stop button to show restart state (user can restart streaming)
        stop_button.setText('Restart')
        stop_button.setEnabled(True)  # Allow user to click to restart

        # Update plot title to indicate trigger
        plot_signal.title_updated.emit(f"Triggered @ sample {trigger_at:,} - Streaming Stopped")

        # Mark as stopped (trigger causes stop)
        streaming_stopped = True

        # Automatically pull raw data (red trace) after a short delay to allow UI updates
        print(f"[UI] Automatically pulling raw data (red trace) after trigger event...")
        QtCore.QTimer.singleShot(100, on_pull_raw_samples_clicked)  # 100ms delay for UI responsiveness

    except Exception as e:
        print(f"[UI ERROR] Exception in on_trigger_fired: {e}")
        import traceback
        traceback.print_exc()

def on_pull_raw_samples_clicked():
    """
    Pull raw (non-downsampled) samples from device memory after trigger event.
    Creates a new buffer, reads raw data, and overlays it on the plot aligned in time.
    """
    global trigger_at_sample, hardware_adc_sample_rate, ring_filled, DOWNSAMPLING_RATIO, data_lock, MAX_POST_TRIGGER_SAMPLES, MAX_PRE_TRIGGER_SAMPLES
    global raw_full_data, raw_full_x_data

    if not trigger_fired:
        print("[ERROR] Cannot pull raw samples - trigger has not fired")
        return

    # DEBUG: Check handle validity BEFORE raw pull
    try:
        unit_serial = scope.get_unit_serial()
        print(f"[RAW PULL DEBUG] Handle valid BEFORE pull - Connected to: {unit_serial}")
    except Exception as e:
        print(f"[RAW PULL DEBUG ERROR] Handle invalid BEFORE pull: {e}")

    print(f"\n[RAW SAMPLES] Pulling raw samples from device memory...")
    print(f"[RAW SAMPLES] Trigger occurred at sample {trigger_at_sample:,} (downsampled space)")

    # DEBUG: Check handle validity BEFORE raw pull operations
    try:
        unit_serial = scope.get_unit_serial()
        print(f"[RAW PULL DEBUG] Handle valid BEFORE pull - Connected to: {unit_serial}")
    except Exception as e:
        print(f"[RAW PULL DEBUG ERROR] Handle invalid BEFORE pull: {e}")
        return

    try:
        # Get max available memory first
        max_available = scope.get_maximum_available_memory()

        # Use the already-calculated MAX_PRE_TRIGGER_SAMPLES from validation
        # This ensures we use the validated value (which may have been auto-adjusted to minimum)
        # rather than recalculating from the spinbox which might not reflect the validated value
        old_max_pre_trigger = MAX_PRE_TRIGGER_SAMPLES
        
        # Validate that current pre-trigger meets minimum requirement based on poll interval
        # Minimum pre-trigger must be at least one poll interval worth of samples
        poll_interval_seconds = POLLING_INTERVAL
        min_pre_trigger_samples = int(poll_interval_seconds * hardware_adc_sample_rate)
        
        if MAX_PRE_TRIGGER_SAMPLES < min_pre_trigger_samples:
            print(f"[RAW SAMPLES] Current pre-trigger ({MAX_PRE_TRIGGER_SAMPLES:,}) is less than minimum ({min_pre_trigger_samples:,})")
            print(f"[RAW SAMPLES]   Minimum based on poll interval ({poll_interval_seconds*1000:.2f} ms) and sample rate ({hardware_adc_sample_rate/1e6:.3f} MSPS)")
            print(f"[RAW SAMPLES]   Adjusting to minimum: {min_pre_trigger_samples:,} samples")
            MAX_PRE_TRIGGER_SAMPLES = min_pre_trigger_samples
        
        # Cap pre-trigger to available memory
        max_pre_trigger_allowed = max_available - MAX_POST_TRIGGER_SAMPLES
        if MAX_PRE_TRIGGER_SAMPLES > max_pre_trigger_allowed:
            print(f"[RAW SAMPLES] Pre-trigger ({MAX_PRE_TRIGGER_SAMPLES:,}) exceeds available memory limit ({max_pre_trigger_allowed:,})")
            print(f"[RAW SAMPLES]   Capping to: {max_pre_trigger_allowed:,} samples")
            MAX_PRE_TRIGGER_SAMPLES = max(0, max_pre_trigger_allowed)
        
        if old_max_pre_trigger != MAX_PRE_TRIGGER_SAMPLES:
            print(f"[RAW SAMPLES] MAX_PRE_TRIGGER_SAMPLES: {old_max_pre_trigger:,} -> {MAX_PRE_TRIGGER_SAMPLES:,}")
        else:
            print(f"[RAW SAMPLES] Using validated pre-trigger samples: {MAX_PRE_TRIGGER_SAMPLES:,}")

        # Calculate total raw samples from pre + post trigger samples
        total_raw_samples = MAX_PRE_TRIGGER_SAMPLES + MAX_POST_TRIGGER_SAMPLES

        # Limit total_raw_samples to available memory
        if total_raw_samples > max_available:
            print(f"[WARNING] Calculated {total_raw_samples:,} samples (pre={MAX_PRE_TRIGGER_SAMPLES:,} + post={MAX_POST_TRIGGER_SAMPLES:,}) exceeds available memory ({max_available:,})")
            total_raw_samples = max_available
            print(f"[RAW SAMPLES] Limited to {total_raw_samples:,} samples (max available memory)")

        # Validate total_raw_samples before attempting to pull
        if total_raw_samples <= 0:
            error_msg = f"[ERROR] Invalid total_raw_samples: {total_raw_samples:,}. Cannot pull raw data."
            print(error_msg)
            print(f"[ERROR] Pre-trigger samples: {MAX_PRE_TRIGGER_SAMPLES:,}, Post-trigger samples: {MAX_POST_TRIGGER_SAMPLES:,}")
            print(f"[ERROR] Please reduce pre-trigger time or check your settings.")
            return

        if total_raw_samples > max_available:
            error_msg = f"[ERROR] Total samples ({total_raw_samples:,}) still exceeds max available memory ({max_available:,}) after limiting."
            print(error_msg)
            print(f"[ERROR] Pre-trigger samples: {MAX_PRE_TRIGGER_SAMPLES:,}, Post-trigger samples: {MAX_POST_TRIGGER_SAMPLES:,}")
            print(f"[ERROR] Please reduce pre-trigger time to fit within device memory limits.")
            return

        # Additional sanity check - SDK wrapper now uses c_uint64 for buffer size
        # Using 4 billion as conservative limit (actual SDK may support larger)
        MAX_SDK_BUFFER_SAMPLES = 4_000_000_000  # Conservative limit (4 billion samples)
        if total_raw_samples > MAX_SDK_BUFFER_SAMPLES:
            error_msg = f"[ERROR] Total samples ({total_raw_samples:,}) exceeds buffer limit ({MAX_SDK_BUFFER_SAMPLES:,})."
            print(error_msg)
            print(f"[ERROR] This is likely due to incorrect pre-trigger time settings.")
            print(f"[ERROR] Pre-trigger time: {user_pre_trigger_time} {TIME_UNIT_NAMES.get(user_pre_trigger_units, '?')}")
            print(f"[ERROR] Available memory: {max_available:,} samples")
            print(f"[ERROR] Please reduce pre-trigger time to keep total samples under {MAX_SDK_BUFFER_SAMPLES:,}.")
            return

        print(f"[RAW SAMPLES] Reading {total_raw_samples:,} raw samples (pre={MAX_PRE_TRIGGER_SAMPLES:,} + post={MAX_POST_TRIGGER_SAMPLES:,}, no downsampling)")

        # Pull raw samples from device using helper function
        raw_data, n_raw_samples = pull_raw_samples_from_device(scope, total_raw_samples, ADC_DATA_TYPE)

        # DEBUG: Check handle validity AFTER raw pull (after get_values call)
        try:
            unit_serial = scope.get_unit_serial()
            print(f"[RAW PULL DEBUG] Handle valid AFTER pull - Connected to: {unit_serial}")
        except Exception as e:
            print(f"[RAW PULL DEBUG ERROR] Handle invalid AFTER pull: {e}")
            print(f"[RAW PULL DEBUG ERROR] get_values() may have invalidated the handle!")

        if raw_data is None or n_raw_samples == 0:
            return

        # Get trigger position from device using helper function
        triggered_at_raw = get_trigger_position_from_device(scope, trigger_at_sample, DOWNSAMPLING_RATIO)

        # Calculate time alignment using helper function
        with data_lock:
            current_ring_filled = ring_filled

        raw_x_data, raw_end_pos, raw_start_pos = calculate_raw_data_time_alignment(
            current_ring_filled, DOWNSAMPLING_RATIO, trigger_at_sample, n_raw_samples,
            hardware_adc_sample_rate
        )

        # Print alignment details
        print(f"[RAW SAMPLES] Time alignment:")
        print(f"  Downsampled trace end position: {raw_end_pos:,.0f} (ring_filled={current_ring_filled:,} * ratio={DOWNSAMPLING_RATIO})")
        print(f"  Trigger at downsampled sample: {trigger_at_sample:,}")
        print(f"  Trigger at raw sample: {triggered_at_raw:,}")
        print(f"  MAX_PRE_TRIGGER_SAMPLES: {MAX_PRE_TRIGGER_SAMPLES:,}")
        print(f"  MAX_POST_TRIGGER_SAMPLES: {MAX_POST_TRIGGER_SAMPLES:,}")
        print(f"  Expected total raw length: {MAX_POST_TRIGGER_SAMPLES + MAX_PRE_TRIGGER_SAMPLES:,} (pre + post)")
        print(f"  Raw data samples retrieved: {n_raw_samples:,} (requested: {total_raw_samples:,})")
        print(f"  Raw trace end position: {raw_end_pos:,.0f} samples (matches downsampled trace end)")
        print(f"  Raw trace start position: {raw_start_pos:,.0f} samples")
        if hardware_adc_sample_rate is not None and hardware_adc_sample_rate > 0:
            # Time-based x-axis
            print(f"  Raw data x-axis range: {raw_x_data[0]:.9f} to {raw_x_data[-1]:.9f} seconds")
            time_span = raw_x_data[-1] - raw_x_data[0]
            expected_time_span = (n_raw_samples - 1) / hardware_adc_sample_rate
            time_per_sample = 1.0 / hardware_adc_sample_rate
            print(f"  Raw trace spans: {time_span:.9f} seconds ({n_raw_samples:,} samples)")
            print(f"  Expected time span: {expected_time_span:.9f} seconds")
            print(f"  Time per raw sample: {time_per_sample:.12e} seconds (1 / {hardware_adc_sample_rate:.2f} Hz)")
            # Check for duplicate time values (would indicate calculation error)
            if len(raw_x_data) > 1:
                time_diffs = np.diff(raw_x_data)
                min_diff = np.min(time_diffs)
                max_diff = np.max(time_diffs)
                expected_diff = time_per_sample
                if min_diff < expected_diff * 0.99 or max_diff > expected_diff * 1.01:
                    print(f"  [WARNING] Time spacing inconsistent! Min diff: {min_diff:.12e}, Max diff: {max_diff:.12e}, Expected: {expected_diff:.12e}")
                else:
                    print(f"  [OK] Time spacing correct: {min_diff:.12e} seconds between samples")
        else:
            # Sample-based x-axis
            print(f"  Raw data x-axis range: {raw_x_data[0]:,.0f} to {raw_x_data[-1]:,.0f} samples")
            print(f"  Raw trace spans: {n_raw_samples:,} samples")

        # Apply PyQtGraph downsampling settings if enabled
        enabled = raw_display_enable_checkbox.isChecked()
        if enabled:
            # Get mode from combo box (map display text to mode string)
            mode_text = raw_display_mode_combo.currentText()
            # Map display text to PyQtGraph mode strings
            mode_map = {'Subsample': 'subsample', 'Mean': 'mean', 'Peak': 'peak'}
            mode = mode_map.get(mode_text, 'mean')  # Default to 'mean' if not found

            # Get user-set factor and max points constraint
            user_factor = raw_display_factor_spinbox.value()
            max_points = int(raw_display_max_points_spinbox.value())

            # Calculate required factor to meet max_points constraint
            # factor = ceil(n_raw_samples / max_points)
            if n_raw_samples > max_points:
                required_factor = int(np.ceil(n_raw_samples / max_points))
                # Use the maximum of user factor and required factor
                factor = max(user_factor, required_factor)

                if factor > user_factor:
                    print(f"[RAW SAMPLES] Auto-adjusting factor: {user_factor} -> {factor} to meet max_points constraint ({max_points:,} points)")
                    print(f"[RAW SAMPLES]   Raw samples: {n_raw_samples:,}, Max points: {max_points:,}, Required factor: {required_factor}")
                    # Update the spinbox to show the adjusted factor
                    raw_display_factor_spinbox.setValue(factor)
            else:
                factor = user_factor
                print(f"[RAW SAMPLES] Using user-set factor: {factor} (raw samples: {n_raw_samples:,} <= max_points: {max_points:,})")

            # Set downsampling factor (mode parameter not supported in setDownsampling())
            raw_curve.setDownsampling(ds=factor, auto=False)

            # Try to set downsampling mode via opts dictionary if available
            mode_set = False
            try:
                if hasattr(raw_curve, 'opts') and isinstance(raw_curve.opts, dict):
                    raw_curve.opts['downsampleMethod'] = mode
                    mode_set = True
            except (AttributeError, TypeError, KeyError):
                pass

            if mode_set:
                print(f"[RAW SAMPLES] PyQtGraph downsampling enabled: factor={factor}, mode={mode}")
            else:
                print(f"[RAW SAMPLES] PyQtGraph downsampling enabled: factor={factor} (mode '{mode}' may not be available in this PyQtGraph version)")
        else:
            raw_curve.setDownsampling(ds=1, auto=False)
            print(f"[RAW SAMPLES] PyQtGraph downsampling disabled")

        # Cache full aligned raw data for region-based operations
        raw_full_data = raw_data
        raw_full_x_data = raw_x_data

        # Update the raw curve with aligned data (full span)
        raw_curve.setData(raw_full_x_data, raw_full_data)
        print(f"[RAW SAMPLES] Raw data plotted as overlay (red X symbols) - aligned with downsampled data")

        # Auto-range X-axis to fit the red trace (raw data), but keep Y-axis fixed
        # This provides "view all" functionality specifically for the raw data on X-axis only
        vb = plot.getViewBox()
        # Get X bounds from raw data and set X-range manually (Y-axis stays fixed)
        if len(raw_full_x_data) > 0:
            x_min = float(raw_full_x_data[0])
            x_max = float(raw_full_x_data[-1])
            # Add small padding for visibility
            x_padding = (x_max - x_min) * 0.02  # 2% padding
            plot.setXRange(x_min - x_padding, x_max + x_padding, padding=0)
            print(f"[RAW SAMPLES] X-axis set to fit raw data: {x_min:.6f} to {x_max:.6f} seconds")
        # Re-enforce Y-axis limits to ensure they stay fixed
        data_processing.update_y_axis_from_adc_limits(plot, scope)
        print(f"[RAW SAMPLES] Y-axis remains fixed at -130 to +130")

        # Disable full-pull button after pulling (can only pull once per trigger)
        # Enable region-based raw button now that we have cached raw data
        pull_region_raw_button.setEnabled(True)

        print(f"[RAW SAMPLES] Raw samples successfully pulled and overlaid on plot")

    except Exception as e:
        print(f"[ERROR] Failed to pull raw samples: {e}")
        import traceback
        traceback.print_exc()


def on_pull_region_raw_clicked():
    """
    Plot only the portion of cached raw data that lies within the current
    LinearRegionItem selection, using the aligned raw_full_x_data array.

    This does NOT re-pull from the device; it reuses the last full raw capture
    pulled via on_pull_raw_samples_clicked() and slices it in downsampled
    index space to match the current region bounds.
    """
    global raw_full_data, raw_full_x_data

    if raw_full_data is None or raw_full_x_data is None:
        print("[RAW REGION] No cached raw data available. Pull full raw samples first.")
        return

    try:
        x0, x1 = region.getRegion()
    except Exception:
        print("[RAW REGION] Unable to read region bounds.")
        return

    if x1 <= x0:
        print("[RAW REGION] Empty or invalid region; nothing to plot.")
        return

    # Map region bounds into raw_full_x_data space
    x = raw_full_x_data
    y = raw_full_data

    if x is None or y is None or len(x) == 0 or len(y) == 0:
        print("[RAW REGION] Cached raw arrays are empty.")
        return

    # raw_full_x_data is now time-based (seconds), not sample indices
    # Region bounds (x0, x1) are also in time (seconds)
    # Use searchsorted to find the indices in the time-based array
    # This handles the case where raw data may have negative start times
    i_start = np.searchsorted(x, x0, side='left')
    i_end = np.searchsorted(x, x1, side='right')

    # Clamp to valid range
    i_start = max(0, min(i_start, len(x) - 1))
    i_end = max(i_start + 1, min(i_end, len(x)))

    if i_end <= i_start:
        print("[RAW REGION] Region does not overlap cached raw data.")
        return

    x_slice = x[i_start:i_end]
    y_slice = y[i_start:i_end]

    if x_slice.size == 0 or y_slice.size == 0:
        print("[RAW REGION] Region slice is empty after bounds check.")
        return

    # Optionally apply PyQtGraph downsampling to gated raw, based on UI setting
    if gated_raw_downsample_checkbox.isChecked() and raw_display_enable_checkbox.isChecked():
        # Use same factor and (best-effort) mode as the full raw display settings
        user_factor = raw_display_factor_spinbox.value()
        max_points = int(raw_display_max_points_spinbox.value())

        # Calculate required factor to meet max_points constraint for gated region
        n_gated_samples = len(y_slice)
        if n_gated_samples > max_points:
            required_factor = int(np.ceil(n_gated_samples / max_points))
            factor = max(user_factor, required_factor)
        else:
            factor = user_factor

        gated_raw_curve.setDownsampling(ds=factor, auto=False)
        try:
            mode_text = raw_display_mode_combo.currentText()
            mode_map = {'Subsample': 'subsample', 'Mean': 'mean', 'Peak': 'peak'}
            mode = mode_map.get(mode_text, 'mean')
            if hasattr(gated_raw_curve, 'opts') and isinstance(gated_raw_curve.opts, dict):
                gated_raw_curve.opts['downsampleMethod'] = mode
        except Exception:
            pass
        print(f"[RAW REGION] Gated raw downsampling enabled: factor={factor}")
    else:
        # Show gated raw at full resolution regardless of global downsampling
        gated_raw_curve.setDownsampling(ds=1, auto=False)
        print("[RAW REGION] Gated raw downsampling disabled (full resolution).")

    # Plot the region subset on the separate gated raw curve (green)
    # Note: raw_curve (red) remains visible with full raw data
    gated_raw_curve.setData(x_slice, y_slice)
    # x_slice is time-based (seconds), so format appropriately
    if len(x_slice) > 0:
        print(f"[RAW REGION] Plotted gated raw (green): x=[{float(x_slice[0]):.6f}, {float(x_slice[-1]):.6f}] seconds "
              f"({x_slice.size:,} samples)")
    else:
        print(f"[RAW REGION] No data in selected region")

def on_region_markers_toggled(enabled):
    """
    Handle toggling of region selection markers visibility.
    When enabled, constrains the region to the currently visible/zoomed area.

    Args:
        enabled: True to show markers, False to hide
    """
    if enabled:
        # Get current view range (visible area)
        x_range = plot.viewRange()[0]  # (x_min, x_max)
        view_x_min, view_x_max = x_range

        # Constrain region bounds to current view
        region.setBounds((view_x_min, view_x_max))

        # Get current region bounds
        current_region = region.getRegion()
        current_start, current_end = current_region

        # If region extends outside visible area, adjust it to fit
        region_updated = False
        if current_start < view_x_min:
            current_start = view_x_min
            region_updated = True
        if current_end > view_x_max:
            current_end = view_x_max
            region_updated = True
        if current_start > view_x_max:
            # Region is completely outside view, center it in view
            view_span = view_x_max - view_x_min
            current_start = view_x_min + view_span * 0.25
            current_end = view_x_min + view_span * 0.75
            region_updated = True
        elif current_end < view_x_min:
            # Region is completely outside view, center it in view
            view_span = view_x_max - view_x_min
            current_start = view_x_min + view_span * 0.25
            current_end = view_x_min + view_span * 0.75
            region_updated = True

        if region_updated:
            region.setRegion((current_start, current_end))

        region.show()
    else:
        region.hide()

# Connect trigger fired signal
plot_signal.trigger_fired.connect(on_trigger_fired)

# Connect pull pre trigger data button
# Connect region-based raw pull button
pull_region_raw_button.clicked.connect(on_pull_region_raw_clicked)

# Connect region markers visibility checkbox
region_markers_checkbox.toggled.connect(on_region_markers_toggled)
# Initialize visibility based on checkbox state
on_region_markers_toggled(region_markers_checkbox.isChecked())

def on_view_range_changed():
    """Update region bounds when view range changes (zoom/pan), if markers are visible."""
    if region_markers_checkbox.isChecked():
        x_range = plot.viewRange()[0]
        view_x_min, view_x_max = x_range
        # Update bounds to current view
        region.setBounds((view_x_min, view_x_max))

        # Clamp region to view if it extends outside
        current_region = region.getRegion()
        current_start, current_end = current_region

        region_updated = False
        if current_start < view_x_min:
            current_start = view_x_min
            region_updated = True
        if current_end > view_x_max:
            current_end = view_x_max
            region_updated = True
        # If region is completely outside view, center it
        if current_start > view_x_max or current_end < view_x_min:
            view_span = view_x_max - view_x_min
            current_start = view_x_min + view_span * 0.25
            current_end = view_x_min + view_span * 0.75
            region_updated = True

        if region_updated:
            region.setRegion((current_start, current_end))

# Connect view range changes to keep region within visible bounds
plot.getViewBox().sigRangeChanged.connect(on_view_range_changed)

# Create a Qt timer for regular plot updates
timer = QtCore.QTimer()
timer.timeout.connect(update_plot)
refresh_interval_ms = int(1000 / REFRESH_FPS)  # Convert FPS to milliseconds
timer.start(refresh_interval_ms)

print(f"Plot update timer started at {REFRESH_FPS} FPS ({refresh_interval_ms}ms)")


# ============================================================================
# MAIN EXECUTION AND CLEANUP
# ============================================================================

def cleanup():
    """Clean shutdown of all resources"""
    global stop_streaming, streaming_stopped

    print("\nShutting down...")

    # Signal streaming thread to stop
    stop_streaming = True

    # Stop Qt timers
    timer.stop()

    # Stop hardware streaming and close connection
    try:
        # Only stop hardware if not already stopped by user
        if not streaming_stopped:
            stop_hardware_streaming(scope)
        else:
            print("[OK] Hardware already stopped by user")

        scope.close_unit()
        print("[OK] PicoScope disconnected")
    except Exception as e:
        print(f"[WARNING] Error closing PicoScope: {e}")

    # Close Qt application
    app.quit()
    print("[OK] Application closed")

try:
    print("\n" + "="*60)
    print("STARTING STREAMING - DOWNSAMPLED MODES ONLY")
    print("="*60)
    print(f"• Hardware: {scope.get_unit_serial()}")
    print(f"• Hardware ADC sample rate: {hardware_adc_sample_rate:.2f} Hz")
    print(f"• Downsampled rate: {hardware_adc_sample_rate/DOWNSAMPLING_RATIO:.2f} Hz ({DOWNSAMPLING_RATIO}:1 {DOWNSAMPLING_MODE})")
    print(f"• Software polling rate: {1/POLLING_INTERVAL:.1f} Hz ({POLLING_INTERVAL*1000:.0f} ms)")
    print(f"• Display refresh rate: {REFRESH_FPS} FPS ({int(1000/REFRESH_FPS)}ms)")
    print(f"• OpenGL: {'Enabled' if USE_OPENGL else 'Disabled'}")
    print(f"• Buffer size: {SAMPLES_PER_BUFFER} samples")
    print(f"• Display window: {PYTHON_RING_BUFFER} samples")
    print(f"• Mode: Downsampled ({DOWNSAMPLING_MODE})")
    print("\nPress Ctrl+C or close window to stop...")
    print("="*60)

    # Start the data acquisition thread
    stream_thread = threading.Thread(target=streaming_thread, args=(hardware_adc_sample_rate,), daemon=True)
    stream_thread.start()
    print("[OK] Data acquisition thread started")

    # Handle window close events
    main_window.closeEvent = lambda event: cleanup()

    # Start the Qt application event loop
    print("[OK] Starting Qt event loop...")

    # Handle Qt version compatibility (PyQt5 vs PyQt6)
    try:
        # PyQt6 and newer PyQt5 versions use exec()
        sys.exit(app.exec())
    except AttributeError:
        # Older PyQt5 versions use exec_()
        sys.exit(app.exec_())

except KeyboardInterrupt:
    print("\nKeyboard interrupt received")
    cleanup()

except Exception as e:
    print(f"\nUnexpected error: {e}")
    cleanup()
    raise
