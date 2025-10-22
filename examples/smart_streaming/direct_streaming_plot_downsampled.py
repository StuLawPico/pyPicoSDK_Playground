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
import time
import threading
import sys
import numpy as np
from collections import deque

# PyQtGraph imports
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'pyPicoSDK_Playground'))
import pypicosdk as psdk

# Import UI components module
from ui_components import build_control_panel, STYLES, create_status_display_widget, create_separator, STATUS_COLOR_SCHEMES, create_status_bar

# Import helper modules
from hardware_helpers import (
    calculate_sample_rate, register_double_buffers, start_hardware_streaming,
    stop_hardware_streaming, clear_hardware_buffers,
    compute_interval_from_msps, configure_default_trigger, apply_trigger_configuration,
    calculate_optimal_buffer_size, validate_buffer_size
)
import data_processing
from ui_helpers import (
    collect_ui_settings, calculate_what_changed, validate_and_optimize_settings,
    apply_performance_settings, apply_time_window, apply_streaming_restart,
    restart_streaming, update_max_post_trigger_range
)

# Custom signal for thread-safe communication
class PlotUpdateSignal(QtCore.QObject):
    title_updated = QtCore.pyqtSignal(str)
    data_updated = QtCore.pyqtSignal(object, object)  # x_data, y_data
    buffer_status_updated = QtCore.pyqtSignal(int, int)  # current, total
    efficiency_updated = QtCore.pyqtSignal(float, float, str)  # efficiency %, jitter %, status
    

# Check Qt version for compatibility
try:
    # Try to determine Qt version for better error reporting
    qt_version = QtCore.QT_VERSION_STR if hasattr(QtCore, 'QT_VERSION_STR') else "Unknown"
    print(f"Using Qt version: {qt_version}")
except:
    print("Qt version detection failed, but continuing...")

# ============================================================================
# CONFIGURATION CONSTANTS
# ============================================================================

# Buffer and display configuration
SAMPLES_PER_BUFFER = 1000000    # Samples per hardware buffer
TARGET_TIME_WINDOW = 1.0        # Target time window in seconds (user-adjustable via slider)
PYTHON_RING_BUFFER = 100_000  # Initial Python circular buffer size (will be recalculated based on ratio and time window)
REFRESH_FPS = 30                # Plot refresh rate in frames per second

sample_interval = 800                   # Request sample interval in milliseconds
time_units = psdk.TIME_UNIT.PS

# Optional: configure target streaming rate in MSPS (mega-samples per second)
# Set to a float (e.g., 0.3 for 300 kS/s, 1.0 for 1 MS/s) or None to keep defaults
STREAM_RATE_MSPS = 1

# Downsampling configuration - only decimate and average modes
DOWNSAMPLING_RATIO = 640                  # Default downsampling ratio (640:1)
DOWNSAMPLING_MODE = psdk.RATIO_MODE.DECIMATE  # Default mode: DECIMATE or AVERAGE

# Trigger configuration
# MAX_POST_TRIGGER_SAMPLES will be set to SAMPLES_PER_BUFFER after auto-calculation
# This ensures trigger capture doesn't exceed hardware buffer capacity
MAX_PRE_TRIGGER_SAMPLES = 0  # Pre-trigger samples (data before trigger event)
MAX_POST_TRIGGER_SAMPLES = None  # Will be initialized after buffer calculation
TRIGGER_ENABLED = True  # Trigger enabled by default
TRIGGER_THRESHOLD_ADC = 50  # Trigger threshold in ADC counts (default: 50 ADC counts)
TRIGGER_EVENT_COUNT = 0  # Counter for trigger events

# ADC configuration for downsampled data
# INT8_T is valid for all downsampling modes when device is in 8-bit resolution
# Using smaller data type maximizes speed and minimizes memory usage
ADC_DATA_TYPE = psdk.DATA_TYPE.INT8_T  # 8-bit signed integer (-128 to +127)
ADC_NUMPY_TYPE = np.int8

# PyQtGraph settings
USE_OPENGL = False             # OpenGL acceleration disabled for simplicity
PLOT_PEN_WIDTH = 1             # Line width
ANTIALIAS = False              # Disable antialiasing for performance

POLLING_INTERVAL = 0.001        # Hardware polling interval in seconds (1ms)

# ============================================================================
# HARDWARE INITIALIZATION
# ============================================================================

# Initialize PicoScope hardware
print("Initializing PicoScope...")
scope = psdk.ps6000a()
scope.open_unit()
print(f"Connected to: {scope.get_unit_serial()}")

# If configured, override sample_interval/time_units from MSPS
if STREAM_RATE_MSPS is not None:
	try:
		computed_interval, computed_units = compute_interval_from_msps(STREAM_RATE_MSPS)
		sample_interval = computed_interval
		time_units = computed_units
		print(f"Configured streaming interval from {STREAM_RATE_MSPS} MSPS -> interval={sample_interval} units={time_units}")
	except Exception as e:
		print(f"[WARNING] Failed to set interval from MSPS ({STREAM_RATE_MSPS}): {e}. Using defaults.")

# Configure signal generator for test signal (1Hz sine wave)
scope.set_siggen(frequency=1, pk2pk=0.65, wave_type=psdk.WAVEFORM.SINE)

# Enable channel A with +/- 1V range (2V total dynamic range)
# This accommodates the 1.8Vpp signal without clipping
# Using DC coupling to capture the full signal including low frequencies
# Siggen expects 50Ohm termination, set channel coupleing to 50 ohm to match
scope.set_channel(channel=psdk.CHANNEL.A, range=psdk.RANGE.mV500, coupling=psdk.COUPLING.DC)

# ============================================================================
# DOUBLE BUFFER SETUP
# ============================================================================
# Double buffering prevents data loss during continuous acquisition

# Auto-calculate optimal buffer size for initial ratio
try:
    max_available_memory = scope.get_maximum_available_memory()
    # Calculate optimal buffer size with 95% safety margin
    optimal_initial_buffer = calculate_optimal_buffer_size(max_available_memory, DOWNSAMPLING_RATIO)
    
    print(f"  Memory usage: {optimal_initial_buffer * DOWNSAMPLING_RATIO:,} / {max_available_memory:,} ({(optimal_initial_buffer * DOWNSAMPLING_RATIO) / max_available_memory * 100:.1f}%)")
    
    # Update the global buffer size
    SAMPLES_PER_BUFFER = optimal_initial_buffer
    
except Exception as e:
    print(f"[WARNING] Could not auto-calculate initial buffer size: {e}")
    print(f"  Using default: {SAMPLES_PER_BUFFER:,} samples")

# Initialize MAX_POST_TRIGGER_SAMPLES to safe default (10,000 samples)
MAX_POST_TRIGGER_SAMPLES = 10000
print(f"  Max post-trigger samples: {MAX_POST_TRIGGER_SAMPLES:,}")

print("\nSetting up double buffers...")

# Clear any existing buffers
scope.set_data_buffer(psdk.CHANNEL.A, 0, action=psdk.ACTION.CLEAR_ALL)

# Create buffers
buffer_0 = np.zeros(SAMPLES_PER_BUFFER, dtype=ADC_NUMPY_TYPE)
buffer_1 = np.zeros(SAMPLES_PER_BUFFER, dtype=ADC_NUMPY_TYPE)

# Register buffers with hardware (downsampled mode)
print("Registering double buffers...")
register_double_buffers(scope, buffer_0, buffer_1, SAMPLES_PER_BUFFER, ADC_DATA_TYPE, DOWNSAMPLING_MODE)
print("[OK] Double buffer setup complete")

# ============================================================================
# CONFIGURE TRIGGER (after buffer setup)
# ============================================================================

# Configure simple trigger with default settings (after buffers are registered)
try:
    print(f"[CONFIG] Configuring default trigger: channel=A, threshold={TRIGGER_THRESHOLD_ADC} ADC")
    print(f"[CONFIG] Trigger enabled: {TRIGGER_ENABLED}, Max post trigger: {MAX_POST_TRIGGER_SAMPLES:,} samples")
    
    configure_default_trigger(scope, TRIGGER_ENABLED, TRIGGER_THRESHOLD_ADC)
    
except Exception as e:
    print(f"[WARNING] Error configuring default trigger: {e}")
    print(f"[INFO] Trigger will be disabled - can be enabled later via UI controls")

# ============================================================================
# START HARDWARE STREAMING
# ============================================================================

print("Starting hardware streaming...")
print(f"[STARTUP] Final configuration before streaming:")
print(f"  - Trigger enabled: {TRIGGER_ENABLED}")
print(f"  - Trigger threshold: {TRIGGER_THRESHOLD_ADC} ADC counts")
print(f"  - Max post trigger: {MAX_POST_TRIGGER_SAMPLES:,} samples")
print(f"  - Buffer size: {SAMPLES_PER_BUFFER:,} samples")

actual_interval = start_hardware_streaming(scope, sample_interval, time_units, 
                                          MAX_PRE_TRIGGER_SAMPLES, MAX_POST_TRIGGER_SAMPLES,
                                          DOWNSAMPLING_RATIO, DOWNSAMPLING_MODE, TRIGGER_ENABLED)

print(f"Actual sample interval: {actual_interval} {time_units}")
# Calculate sample rate based on the time units
sample_rate = calculate_sample_rate(actual_interval, time_units)
print(f"Actual sample rate: {sample_rate:.2f} Hz")

# Store hardware ADC sample rate for position tracking
hardware_adc_sample_rate = sample_rate
print(f"Stored hardware ADC sample rate for tracking: {hardware_adc_sample_rate:.2f} Hz")

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

# Create main window with buttons and plot
main_window = pg.QtWidgets.QMainWindow()
main_window.setWindowTitle('PicoScope Direct Streaming - PyQtGraph Downsampled Modes Only')
main_window.resize(1200, 700)

# Create central widget and layout
central_widget = pg.QtWidgets.QWidget()
main_window.setCentralWidget(central_widget)

# Main horizontal layout: plot on left, controls on right
main_layout = pg.QtWidgets.QHBoxLayout()
central_widget.setLayout(main_layout)

# Create control panel using UI components module
control_widgets = build_control_panel({
    'psdk': psdk,
    'DOWNSAMPLING_RATIO': DOWNSAMPLING_RATIO,
    'DOWNSAMPLING_MODE': DOWNSAMPLING_MODE,
    'sample_interval': sample_interval,
    'time_units': time_units,
    'SAMPLES_PER_BUFFER': SAMPLES_PER_BUFFER,
    'REFRESH_FPS': REFRESH_FPS,
    'POLLING_INTERVAL': POLLING_INTERVAL,
    'TARGET_TIME_WINDOW': TARGET_TIME_WINDOW,
    'MAX_POST_TRIGGER_SAMPLES': MAX_POST_TRIGGER_SAMPLES,
    'TRIGGER_ENABLED': TRIGGER_ENABLED,
    'TRIGGER_THRESHOLD_ADC': TRIGGER_THRESHOLD_ADC
})

# Extract widgets from returned dictionary
controls_panel = control_widgets['panel']
mode_combo = control_widgets['mode_combo']
ratio_spinbox = control_widgets['ratio_spinbox']
interval_spinbox = control_widgets['interval_spinbox']
units_combo = control_widgets['units_combo']
hw_buffer_spinbox = control_widgets['hw_buffer_spinbox']
refresh_spinbox = control_widgets['refresh_spinbox']
poll_spinbox = control_widgets['poll_spinbox']
time_window_slider = control_widgets['time_window_slider']
time_window_value_label = control_widgets['time_window_value_label']
trigger_enable_checkbox = control_widgets['trigger_enable_checkbox']
trigger_threshold_spinbox = control_widgets['trigger_threshold_spinbox']
max_pre_trigger_spinbox = control_widgets['max_pre_trigger_spinbox']
max_post_trigger_spinbox = control_widgets['max_post_trigger_spinbox']
apply_button = control_widgets['apply_button']
stop_button = control_widgets['stop_button']

# Note: All control panel widgets are now created via ui_components module
# ============================================================================

# ============= STATUS BAR (TOP OF PLOT AREA) =============
# Create container for plot area with status bar on top
plot_container = pg.QtWidgets.QWidget()
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

# Add widgets to main horizontal layout: plot area (with status bar) on left, controls on right
main_layout.addWidget(plot_container)
main_layout.addWidget(controls_panel)

# Show the main window
main_window.show()

# Update initial rate displays
status_displays['adc_rate'].setText(f"{initial_msps:.3f} MSPS")
initial_downsampled_msps = initial_msps / DOWNSAMPLING_RATIO
status_displays['downsampled_rate'].setText(f"{initial_downsampled_msps:.3f} MSPS")

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
        min_poll_display.setText(f"{min_poll_ms_init:.2f} ms")
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
    # Step 1: Collect all UI values
    settings = collect_ui_settings(ratio_spinbox, mode_combo, interval_spinbox, units_combo,
                                  hw_buffer_spinbox, refresh_spinbox, poll_spinbox,
                                  time_window_slider, max_pre_trigger_spinbox, max_post_trigger_spinbox,
                                  trigger_enable_checkbox, trigger_threshold_spinbox)
    
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
        'TRIGGER_ENABLED': TRIGGER_ENABLED,
        'TRIGGER_THRESHOLD_ADC': TRIGGER_THRESHOLD_ADC
    }
    
    settings_changed, performance_changed, time_window_changed, trigger_changed = calculate_what_changed(settings, current_settings)
    
    # Step 3: Early exit if nothing changed
    if not (settings_changed or performance_changed or time_window_changed or trigger_changed):
        print("No changes detected")
        return
    
    # Step 4: Print what's changing
    print(f"\n[UPDATE] Updating settings:")
    if settings_changed:
        print(f"  Streaming: ratio={settings['new_ratio']}, mode={settings['new_mode']}, "
              f"interval={settings['new_interval']}, units={settings['new_units']}, "
              f"hw_buffer={settings['new_buffer_size']}")
        print(f"  Trigger buffers: pre={settings['new_max_pre_trigger']:,}, post={settings['new_max_post_trigger']:,}")
    if performance_changed:
        print(f"  Performance: refresh={settings['new_refresh_fps']} FPS, "
              f"poll={settings['new_poll_interval']*1000:.2f}ms")
    if time_window_changed:
        print(f"  Time Window: {TARGET_TIME_WINDOW:.1f}s -> {settings['new_time_window']:.1f}s")
    if trigger_changed:
        print(f"  Trigger: enabled={settings['new_trigger_enabled']}, threshold={settings['new_trigger_threshold']} ADC")
    
    # Step 5: Validate and optimize settings
    is_valid, settings = validate_and_optimize_settings(settings, cached_max_memory, max_post_trigger_spinbox, hw_buffer_spinbox)
    if not is_valid:
        return  # Validation failed, error already printed
    
    # Step 6: Apply performance settings (no restart needed)
    if performance_changed:
        REFRESH_FPS, POLLING_INTERVAL = apply_performance_settings(settings, timer)
    
    # Step 7: Handle time window changes
    should_return, new_ring_buffer = apply_time_window(settings, settings_changed, performance_changed,
                                                      data_lock, PYTHON_RING_BUFFER, data_array, x_data,
                                                      ring_head, ring_filled, hardware_adc_sample_rate,
                                                      plot, plot_signal)
    if should_return:
        # Still apply trigger if that's what changed
        if trigger_changed:
            apply_trigger_configuration(scope, settings['new_trigger_enabled'], settings['new_trigger_threshold'])
        return
    
    # Step 8: Apply streaming restart if needed
    if settings_changed:
        success, new_rate, new_ring_buffer = apply_streaming_restart(settings, scope, buffer_0, buffer_1, data_lock,
                                                                     PYTHON_RING_BUFFER, data_array, x_data,
                                                                     ring_head, ring_filled, hardware_adc_sample_rate,
                                                                     settings_update_in_progress, settings_update_event,
                                                                     efficiency_history, perf_samples_window,
                                                                     status_displays, plot_signal, mode_combo, cached_max_memory)
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
            hardware_adc_sample_rate = new_rate
            PYTHON_RING_BUFFER = new_ring_buffer
    else:
        print("[OK] Settings applied (no streaming restart needed)")
    
    # Step 9: Apply trigger configuration (if changed or if streaming restarted)
    if trigger_changed or settings_changed:
        apply_trigger_configuration(scope, settings['new_trigger_enabled'], settings['new_trigger_threshold'])
        # Update global trigger variables
        TRIGGER_ENABLED = settings['new_trigger_enabled']
        TRIGGER_THRESHOLD_ADC = settings['new_trigger_threshold']
    
    # Step 10: Force streaming restart if ONLY trigger settings changed (no other streaming changes)
    if trigger_changed and not settings_changed:
        print("[INFO] Trigger settings changed - restarting streaming to apply trigger...")
        apply_streaming_restart(settings, scope, buffer_0, buffer_1, data_lock,
                               PYTHON_RING_BUFFER, data_array, x_data,
                               ring_head, ring_filled, hardware_adc_sample_rate,
                               settings_update_in_progress, settings_update_event,
                               efficiency_history, perf_samples_window,
                               status_displays, plot_signal, mode_combo, cached_max_memory)


def on_restart_streaming():
    """Restart streaming after it was stopped"""
    global stop_streaming, streaming_stopped, stream_thread, ring_head, ring_filled
    global data_array, x_data, PYTHON_RING_BUFFER
    
    print("Restarting streaming...")
    
    # Reset flags
    streaming_stopped = False
    stop_streaming = False
    
    # Use helper function to restart streaming
    success = restart_streaming(scope, buffer_0, buffer_1, data_array, ring_head, ring_filled,
                               PYTHON_RING_BUFFER, DOWNSAMPLING_RATIO, DOWNSAMPLING_MODE,
                               hardware_adc_sample_rate, plot_signal, mode_combo)
    
    if success:
        # Start new streaming thread
        stream_thread = threading.Thread(target=streaming_thread, args=(hardware_adc_sample_rate,), daemon=True)
        stream_thread.start()
        print("[OK] New streaming thread started")
        
        # Update UI
        stop_button.setText('Stop')
        plot_signal.title_updated.emit(f"Real-time Streaming Data - {DOWNSAMPLING_RATIO}:1 {mode_combo.currentText()}")
    else:
        print("[ERROR] Failed to restart streaming")

def on_stop_button_clicked():
    """Handle stop button click - stop hardware immediately, then drain buffers"""
    global stop_streaming, streaming_stopped
    
    if not streaming_stopped:
        print("\n🛑 User requested streaming stop - stopping hardware immediately...")
        streaming_stopped = True
        stop_streaming = True
        
        # Stop hardware immediately (Option A: Clean Stop)
        stop_hardware_streaming(scope)
        
        # Update UI
        stop_button.setText('Restart')
        stop_button.setEnabled(True)  # Keep enabled for restart
        plot_signal.title_updated.emit("Hardware Stopped - Draining Buffers...")
    else:
        # Restart streaming
        print("\n▶ User requested streaming restart...")
        on_restart_streaming()

# Connect button handlers
apply_button.clicked.connect(on_apply_button_clicked)
stop_button.clicked.connect(on_stop_button_clicked)

# Create plot item with performance optimizations
plot = win.addPlot(title=f"Real-time Streaming Data - {DOWNSAMPLING_RATIO}:1 {mode_combo.currentText()} - Initializing...")
plot.setLabel('left', 'Amplitude', units='ADC Counts')
plot.setLabel('bottom', 'Original Sample Index (with gaps)')
plot.showGrid(x=True, y=True, alpha=0.3)

# Setup plot optimizations using helper function
data_processing.setup_plot_optimizations(plot, TARGET_TIME_WINDOW, hardware_adc_sample_rate)

# Create plot curve using helper function
curve = data_processing.create_plot_curve(plot, ANTIALIAS)

# ============================================================================
# DATA STORAGE AND THREADING SETUP
# ============================================================================

print("Setting up data management...")

# Calculate initial ring buffer size based on time window
# Ring buffer size = (time_window × ADC_rate) / ratio
# Use minimum of 100 samples for smooth plotting (scatter plot doesn't need many points)
calculated_buffer = int((TARGET_TIME_WINDOW * hardware_adc_sample_rate) / DOWNSAMPLING_RATIO)
PYTHON_RING_BUFFER = max(100, calculated_buffer)
print(f"Initial ring buffer size: {PYTHON_RING_BUFFER:,} downsampled samples")
print(f"  Time window: {TARGET_TIME_WINDOW:.1f}s, ADC rate: {hardware_adc_sample_rate:.2f} Hz, Ratio: {DOWNSAMPLING_RATIO}:1")

# Pre-allocate arrays
x_data = np.arange(PYTHON_RING_BUFFER, dtype=np.float32)           # X-axis sample indices
data_array = np.zeros(PYTHON_RING_BUFFER, dtype=np.float32)       # Y-axis data circular buffer
# Ring buffer state
ring_head = 0                    # Next write index (0..PYTHON_RING_BUFFER-1)
ring_filled = 0                  # Number of valid samples in buffer (<= PYTHON_RING_BUFFER)

# Threading and synchronization variables
current_buffer_index = 0       # Active hardware buffer index
data_lock = threading.Lock()   # Thread-safe access
stop_streaming = False         # Stop streaming flag
data_updated = False           # New data available flag
streaming_stopped = False      # User stopped streaming flag
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

# Create signal object for thread-safe communication
plot_signal = PlotUpdateSignal()


# ============================================================================
# STREAMING DATA ACQUISITION THREAD
# ============================================================================

def streaming_thread(hardware_adc_rate):
    """
    Background thread for continuous data acquisition from PicoScope hardware.
    
    Args:
        hardware_adc_rate: The actual ADC sampling rate (Hz)
    """
    global current_buffer_index, stop_streaming, data_updated, streaming_stopped, ring_head, ring_filled, perf_script_hz
    global efficiency_history, efficiency_avg, efficiency_jitter, hardware_adc_sample_rate, DOWNSAMPLING_RATIO
    
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
            
            # Debug: Print trigger info periodically
            if n_samples > 0:  # Only when we have data
                streaming_thread.debug_counter = getattr(streaming_thread, 'debug_counter', 0) + 1
                if streaming_thread.debug_counter % 1000 == 0:  # Every 1000 iterations
                    print(f"[DEBUG] Trigger check: enabled={TRIGGER_ENABLED}, triggered={triggered}, threshold={TRIGGER_THRESHOLD_ADC}")
            # Track trigger events and stop on trigger if enabled, but only
            # when there are zero samples (hardware auto-stop has engaged).
            if TRIGGER_ENABLED and n_samples == 0 and triggered:
                global TRIGGER_EVENT_COUNT
                TRIGGER_EVENT_COUNT += 1
                # (Trigger indicator removed)
                print(f"[TRIGGER] Trigger event #{TRIGGER_EVENT_COUNT} detected @ sample {trigger_at}")
                # Cleanly exit the loop on trigger; hardware auto-stop will have engaged.
                streaming_stopped = True
                stop_streaming = True
                break
            
            if n_samples > 0:
                # Select the correct hardware buffer
                current_buffer = buffer_0 if buffer_index == 0 else buffer_1
                
                # Get new data from buffer (downsampled mode - continuous data)
                new_data = current_buffer[start_index:start_index + n_samples].astype(np.float32)
                
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
                
                # Update efficiency display with jitter info
                plot_signal.efficiency_updated.emit(efficiency_avg, efficiency_jitter, status)
                
                # Skip if no new samples
                if new_data.size == 0:
                    time.sleep(POLLING_INTERVAL)
                    continue
                
                # Process new data through circular buffer
                with data_lock:
                    # Write all new samples to circular buffer
                    for i, sample in enumerate(new_data):
                        data_array[ring_head] = sample
                        ring_head = (ring_head + 1) % PYTHON_RING_BUFFER
                        
                        # Update ring filled count (max PYTHON_RING_BUFFER)
                        if ring_filled < PYTHON_RING_BUFFER:
                            ring_filled += 1
                    
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
        print("Hardware stopped - draining remaining buffer data...")
        plot_signal.title_updated.emit("Hardware Stopped - Draining Buffers...")
        
        # Attempt to drain any remaining data from hardware buffers
        drain_timeout = 2.0  # Max 2 seconds to drain
        drain_start = time.perf_counter()
        total_drained = 0
        
        while time.perf_counter() - drain_start < drain_timeout:
            try:
                # Try to get any remaining data
                info = scope.get_streaming_latest_values(
                    channel=psdk.CHANNEL.A,
                    ratio_mode=DOWNSAMPLING_MODE,
                    data_type=ADC_DATA_TYPE
                )
                
                n_samples = info['no of samples']
                
                if n_samples > 0:
                    total_drained += n_samples
                    buffer_index = info['Buffer index'] % 2
                    start_index = info.get('start index', 0)
                    current_buffer = buffer_0 if buffer_index == 0 else buffer_1
                    new_data = current_buffer[start_index:start_index + n_samples].astype(np.float32)
                    
                    # Add drained data to ring buffer
                    with data_lock:
                        for sample in new_data:
                            data_array[ring_head] = sample
                            ring_head = (ring_head + 1) % PYTHON_RING_BUFFER
                            if ring_filled < PYTHON_RING_BUFFER:
                                ring_filled += 1
                        plot_signal.buffer_status_updated.emit(ring_filled, PYTHON_RING_BUFFER)
                        data_updated = True
                    
                    print(f"  Drained {n_samples} samples from buffer...")
                else:
                    # No more data, buffers empty
                    break
                    
            except Exception as e:
                print(f"  Error draining buffers: {e}")
                break
            
            time.sleep(0.05)  # Short sleep between drain attempts
        
        if total_drained > 0:
            print(f"[OK] Buffer drain complete - retrieved {total_drained} samples")
        else:
            print("[OK] No additional data in buffers")
        
        plot_signal.title_updated.emit(f"Stopped - {total_drained} samples drained")
    
    print("Data acquisition thread stopped")

# ============================================================================
# PYQTGRAPH PLOT UPDATE FUNCTION
# ============================================================================

def update_plot():
    """
    Update the PyQtGraph plot with latest streaming data.
    """
    global data_updated, perf_plot_last_time, perf_plot_fps
    
    # Use helper function to update plot
    plot_updated = data_processing.update_plot(curve, data_array, ring_head, ring_filled, PYTHON_RING_BUFFER,
                              DOWNSAMPLING_RATIO, data_lock, data_updated)
    
    if plot_updated:
        # Update plot FPS timing (overlay removed to reduce UI overhead)
        now = time.perf_counter()
        dt = now - perf_plot_last_time
        if dt > 0:
            perf_plot_fps = 1.0 / dt
        perf_plot_last_time = now

def update_buffer_status(current, total):
    """Update the display window time and sample count in top bar"""
    data_processing.update_buffer_status(current, total, DOWNSAMPLING_RATIO, hardware_adc_sample_rate, status_displays)

# ============================================================================
# QT TIMER FOR PLOT UPDATES
# ============================================================================

# Connect signals to slots for thread-safe communication
plot_signal.title_updated.connect(plot.setTitle)
plot_signal.buffer_status_updated.connect(lambda current, total: update_buffer_status(current, total))

def update_efficiency_display(efficiency, jitter, status):
    """
    Update the efficiency display with color coding based on both efficiency and jitter.
    
    Args:
        efficiency: Average efficiency percentage
        jitter: Standard deviation of efficiency (consistency metric)
        status: Overall status ('excellent', 'good', 'warning', 'critical', 'initializing')
    """
    data_processing.update_efficiency_display(efficiency, jitter, status, status_displays)

plot_signal.efficiency_updated.connect(update_efficiency_display)

# (Trigger indicator and handler removed)

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
    
    # Stop Qt timer
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
