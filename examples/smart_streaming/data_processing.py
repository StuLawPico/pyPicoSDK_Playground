"""
Data Processing Helper Functions for PicoScope Streaming Application

This module contains all data processing, plotting, and streaming thread functions
for handling real-time data acquisition and visualization.
"""

import time
import threading
import numpy as np
from collections import deque
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore
import pypicosdk as psdk

# Numba for JIT compilation of pure computation functions
try:
    from numba import njit
    NUMBA_AVAILABLE = True
except ImportError:
    NUMBA_AVAILABLE = False
    # Fallback decorator that does nothing
    def njit(*args, **kwargs):
        def decorator(func):
            return func
        return decorator


# ============================================================================
# CUSTOM TIME AXIS ITEM
# ============================================================================

class TimeAxisItem(pg.AxisItem):
    """
    Custom axis item that displays sample indices as time values.
    
    Internally, all x-values are stored as integer sample indices (in raw ADC sample space).
    This axis converts those indices to time for display, keeping the data layer clean
    and avoiding floating-point precision issues.
    
    Auto-scales to appropriate time units (s, ms, µs, ns) with clean values.
    The axis label is updated dynamically to show the current unit.
    
    Usage:
        axis = TimeAxisItem(orientation='bottom')
        axis.set_sample_rate(625e6)  # 625 MSPS
        plot = win.addPlot(axisItems={'bottom': axis})
    """
    
    def __init__(self, orientation='bottom', **kwargs):
        super().__init__(orientation, **kwargs)
        self._sample_rate = 1.0  # Default: 1 sample per second
        self._current_unit = 's'  # Track current unit for label updates
        # Disable PyQtGraph's SI prefix - we handle scaling ourselves
        self.enableAutoSIPrefix(False)
    
    def set_sample_rate(self, sample_rate):
        """
        Set the hardware ADC sample rate for time conversion.
        
        Args:
            sample_rate: Sample rate in Hz (e.g., 625e6 for 625 MSPS)
        """
        if sample_rate > 0:
            self._sample_rate = float(sample_rate)
        else:
            self._sample_rate = 1.0
        # Force axis to redraw with new scale
        self.picture = None
        self.update()
    
    def _get_time_unit(self, max_time_seconds):
        """
        Determine the appropriate time unit based on the maximum time value.
        
        Args:
            max_time_seconds: Maximum time value in seconds
            
        Returns:
            tuple: (unit_name, scale_factor) e.g., ('ms', 1000)
        """
        if max_time_seconds == 0:
            return ('s', 1)
        elif max_time_seconds < 1e-6:   # Less than 1 µs → nanoseconds
            return ('ns', 1e9)
        elif max_time_seconds < 1e-3:   # Less than 1 ms → microseconds
            return ('µs', 1e6)
        elif max_time_seconds < 1:      # Less than 1 s → milliseconds
            return ('ms', 1e3)
        else:                           # 1 second or more → seconds
            return ('s', 1)
    
    def tickStrings(self, values, scale, spacing):
        """
        Convert sample index values to time strings with auto-scaled units.
        
        Args:
            values: List of sample index values at tick positions
            scale: Scale factor (usually 1.0)
            spacing: Spacing between ticks
            
        Returns:
            List of formatted time strings in the appropriate unit
        """
        if not values:
            return []
        
        # Convert sample indices to time (seconds)
        time_values = [v / self._sample_rate for v in values]
        
        # Determine appropriate time unit based on the range
        max_time = max(abs(t) for t in time_values) if time_values else 0
        unit_name, scale_factor = self._get_time_unit(max_time)
        
        # Update axis label if unit changed
        if unit_name != self._current_unit:
            self._current_unit = unit_name
            # Update the label - this is thread-safe via Qt's signal mechanism
            self.setLabel('Time', units=unit_name)
        
        # Convert to the selected unit and format
        scaled_values = [t * scale_factor for t in time_values]
        
        # Use appropriate decimal places based on the scaled values
        max_scaled = max(abs(v) for v in scaled_values) if scaled_values else 0
        
        if max_scaled == 0:
            return ['0'] * len(values)
        elif max_scaled < 0.1:
            return [f'{v:.4f}' for v in scaled_values]
        elif max_scaled < 1:
            return [f'{v:.3f}' for v in scaled_values]
        elif max_scaled < 10:
            return [f'{v:.2f}' for v in scaled_values]
        elif max_scaled < 100:
            return [f'{v:.1f}' for v in scaled_values]
        else:
            return [f'{v:.0f}' for v in scaled_values]


def samples_to_time(sample_index, sample_rate):
    """
    Convert sample index to time in seconds.
    
    Args:
        sample_index: Sample index (integer or array)
        sample_rate: Hardware ADC sample rate in Hz
        
    Returns:
        Time in seconds (float or array)
    """
    return sample_index / sample_rate if sample_rate > 0 else sample_index


def time_window_to_samples(time_window, sample_rate, downsampling_ratio):
    """
    Convert a time window (seconds) to number of samples.
    
    Args:
        time_window: Time window in seconds
        sample_rate: Hardware ADC sample rate in Hz
        downsampling_ratio: Downsampling ratio
        
    Returns:
        Number of raw ADC samples corresponding to the time window
    """
    return int(time_window * sample_rate)



def update_plot(curve, data_array, ring_head, ring_filled, python_ring_buffer, 
                downsampling_ratio, data_lock, data_updated):
    """
    Update the PyQtGraph plot with latest streaming data.
    
    X-axis values are integer sample indices (in raw ADC sample space).
    The TimeAxisItem handles conversion to time for display.
    
    Args:
        curve: PyQtGraph plot curve object
        data_array: Circular buffer array
        ring_head: Current head position in ring buffer
        ring_filled: Number of filled samples
        python_ring_buffer: Total ring buffer size
        downsampling_ratio: Downsampling ratio for x-axis scaling
        data_lock: Threading lock for data access
        data_updated: Flag indicating if new data is available
        
    Returns:
        bool: True if plot was updated, False if no new data
    """
    # Only update plot if new data is available
    with data_lock:
        if not data_updated:
            return False
        
        # Update plot from ring buffer in logical order 0..N-1
        if ring_filled < python_ring_buffer:
            # Not full yet: show 0..ring_filled-1
            y_vals = data_array[:ring_filled]
            # X-axis: integer sample indices in raw ADC sample space
            # Each downsampled point represents 'downsampling_ratio' raw samples
            x_vals = np.arange(ring_filled, dtype=np.int64) * downsampling_ratio
        else:
            # Full: logical order is [ring_head..end) then [0..ring_head)
            y_vals = np.concatenate((data_array[ring_head:], data_array[:ring_head]))
            # X-axis: integer sample indices in raw ADC sample space
            x_vals = np.arange(python_ring_buffer, dtype=np.int64) * downsampling_ratio

        # Ensure x and y arrays have matching lengths
        min_len = min(len(x_vals), len(y_vals))
        if min_len == 0:
            # No data to plot
            data_updated = False
            return False
        
        x_vals = x_vals[:min_len]
        y_vals = y_vals[:min_len]

        # Update scatter plot (individual points, no connecting lines)
        # If array sizes don't match existing plot data, clear first to avoid broadcast errors
        try:
            curve.setData(x_vals, y_vals)
        except ValueError as e:
            # If there's a shape mismatch (e.g., buffer size changed), clear and reset
            if "could not broadcast" in str(e) or "shape" in str(e).lower():
                print(f"[WARNING] Plot buffer size mismatch detected, resetting plot: {e}")
                curve.clear()  # Clear existing plot data
                curve.setData(x_vals, y_vals)  # Set new data with correct size
            else:
                raise  # Re-raise if it's a different ValueError
        
        # Reset the data update flag
        data_updated = False
        return True


@njit
def _calculate_efficiency_stats_numba(efficiency_array):
    """
    Numba-optimized function to calculate efficiency statistics from array.
    
    Args:
        efficiency_array: NumPy array of efficiency measurements
        
    Returns:
        tuple: (efficiency_avg, efficiency_jitter)
    """
    n = len(efficiency_array)
    if n == 0:
        return 0.0, 0.0
    
    # Calculate mean
    efficiency_avg = np.mean(efficiency_array)
    
    # Calculate standard deviation (jitter)
    if n > 1:
        variance = np.var(efficiency_array)
        efficiency_jitter = np.sqrt(variance)
    else:
        efficiency_jitter = 0.0
    
    return efficiency_avg, efficiency_jitter


def calculate_efficiency_status(efficiency_history):
    """
    Calculate efficiency status based on history.
    
    Args:
        efficiency_history: Deque of efficiency measurements
        
    Returns:
        tuple: (efficiency_avg, efficiency_jitter, status)
    """
    if len(efficiency_history) >= 10:  # Need at least 10 samples for meaningful stats
        # Convert deque to NumPy array for Numba optimization
        if NUMBA_AVAILABLE:
            efficiency_array = np.array(list(efficiency_history), dtype=np.float64)
            efficiency_avg, efficiency_jitter = _calculate_efficiency_stats_numba(efficiency_array)
        else:
            # Fallback to NumPy if Numba not available
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
        efficiency_avg = efficiency_history[-1] if efficiency_history else 0.0
        efficiency_jitter = 0.0
        status = "initializing"
    
    return efficiency_avg, efficiency_jitter, status


def update_performance_tracking(perf_samples_window, perf_window_secs, n_samples):
    """
    Update performance tracking with new sample count.
    
    Args:
        perf_samples_window: Deque for performance tracking
        perf_window_secs: Time window for performance calculation
        n_samples: Number of samples in current batch
        
    Returns:
        float: Current script ingest rate in samples per second
    """
    now_ts = time.perf_counter()
    perf_samples_window.append((now_ts, int(n_samples)))
    window_start = now_ts - perf_window_secs
    
    # Remove old samples outside the window
    while perf_samples_window and perf_samples_window[0][0] < window_start:
        perf_samples_window.popleft()
    
    # Calculate rate
    if perf_samples_window and (perf_samples_window[-1][0] - perf_samples_window[0][0]) > 0:
        window_duration = perf_samples_window[-1][0] - perf_samples_window[0][0]
        samples_in_window = sum(s for _, s in perf_samples_window)
        perf_script_hz = samples_in_window / window_duration
    else:
        perf_script_hz = 0.0
    
    return perf_script_hz


# Timing constants for buffer draining
DRAIN_BUFFER_TIMEOUT_SEC = 2.0       # Maximum time to spend draining buffers after stop
DRAIN_BUFFER_SLEEP_SEC = 0.05         # Sleep interval between drain attempts


def drain_remaining_buffers(scope, buffer_0, buffer_1, data_array, ring_head, ring_filled, 
                          python_ring_buffer, data_lock, plot_signal, downsampling_mode, 
                          adc_data_type, drain_timeout=DRAIN_BUFFER_TIMEOUT_SEC):
    """
    Drain any remaining data from hardware buffers after streaming stops.
    
    Args:
        scope: PicoScope device instance
        buffer_0: First hardware buffer
        buffer_1: Second hardware buffer
        data_array: Circular buffer array (modified in place)
        ring_head: Current head position in ring buffer (will be updated)
        ring_filled: Number of filled samples (will be updated)
        python_ring_buffer: Total ring buffer size
        data_lock: Threading lock for data access
        plot_signal: Signal object for thread-safe communication
        downsampling_mode: Downsampling mode
        adc_data_type: ADC data type
        drain_timeout: Maximum time to spend draining (seconds)
        
    Returns:
        tuple: (total_drained, updated_ring_head, updated_ring_filled)
    """
    print("Hardware stopped - draining remaining buffer data...")
    plot_signal.title_updated.emit("Hardware Stopped - Draining Buffers...")
    
    total_drained = 0
    drain_start = time.perf_counter()
    current_ring_head = ring_head
    current_ring_filled = ring_filled
    
    while time.perf_counter() - drain_start < drain_timeout:
        try:
            # Try to get any remaining data
            info = scope.get_streaming_latest_values(
                channel=psdk.CHANNEL.A,
                ratio_mode=downsampling_mode,
                data_type=adc_data_type
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
                        data_array[current_ring_head] = sample
                        current_ring_head = (current_ring_head + 1) % python_ring_buffer
                        if current_ring_filled < python_ring_buffer:
                            current_ring_filled += 1
                    plot_signal.buffer_status_updated.emit(current_ring_filled, python_ring_buffer)
                
                print(f"  Drained {n_samples} samples from buffer...")
            else:
                # No more data, buffers empty
                break
                
        except Exception as e:
            print(f"  Error draining buffers: {e}")
            break
        
        time.sleep(DRAIN_BUFFER_SLEEP_SEC)  # Short sleep between drain attempts
    
    if total_drained > 0:
        print(f"[OK] Buffer drain complete - retrieved {total_drained} samples")
    else:
        print("[OK] No additional data in buffers")
    
    plot_signal.title_updated.emit(f"Stopped - {total_drained} samples drained")
    return total_drained, current_ring_head, current_ring_filled


def create_plot_curve(plot, antialias=False):
    """
    Create an optimized plot curve for downsampled data visualization.
    
    Args:
        plot: PyQtGraph plot widget
        antialias: Whether to enable antialiasing
        
    Returns:
        PyQtGraph plot curve object
    """
    # Create plot curve with performance settings (points only, no connecting line)
    curve = plot.plot(
        pen=None,                                          # No line connecting points
        symbol='o',                                        # Circle symbol for each point
        symbolSize=3,                                      # Size of each point
        symbolBrush='cyan',                                # Fill color of points
        symbolPen=pg.mkPen(color='cyan', width=1),         # Border color of points
        antialias=antialias,                               # Antialiasing setting
        clipToView=True,                                   # Only render visible data
        autoDownsample=False,                              # Manual downsampling control
        name='HW downsampled data'                         # Legend name
    )
    
    return curve


def create_raw_data_curve(plot, antialias=False, downsample_mode='subsample'):
    """
    Create a plot curve for raw (non-downsampled) data overlay.
    
    Args:
        plot: PyQtGraph plot widget
        antialias: Whether to enable antialiasing
        downsample_mode: Downsampling mode ('subsample', 'mean', or 'peak')
        
    Returns:
        PyQtGraph plot curve object (initialized with empty data)
    """
    # Create raw data overlay curve (initially empty, will be populated when raw samples are pulled)
    # Note: downsampleMethod may need to be set via opts if available
    plot_opts = {
        'pen': pg.mkPen(color='red', width=1, style=QtCore.Qt.PenStyle.DotLine),  # Red dotted line
        'symbol': 'x',                                     # X symbol for raw data points
        'symbolSize': 4,                                   # Larger size for better visibility
        'symbolBrush': 'red',                              # Red color for raw data
        'symbolPen': pg.mkPen(color='red', width=1),       # Red border
        'antialias': antialias,                            # Antialiasing setting
        'clipToView': True,                                # Only render visible data
        'autoDownsample': False,                           # Manual downsampling control
        'name': 'SW D/S pre-trig'                          # Legend name
    }
    
    # Try to add downsampleMethod if supported by PyQtGraph version
    try:
        plot_opts['downsampleMethod'] = downsample_mode
    except:
        pass  # Not available in this version
    
    raw_curve = plot.plot(**plot_opts)
    raw_curve.setData([], [])  # Initialize with empty data
    return raw_curve


def setup_plot_optimizations(plot, max_sample_index, scope=None, datatype=None):
    """
    Configure plot optimizations for real-time streaming.
    
    X-axis is in sample index space (raw ADC samples). The TimeAxisItem
    handles conversion to time for display.
    
    Args:
        plot: PyQtGraph plot widget
        max_sample_index: Maximum sample index for x-range (in raw ADC sample space)
        scope: Optional PicoScope object to get ADC limits from. If provided,
               y-axis will be constrained to ADC limits.
        datatype: Optional DATA_TYPE enum (e.g., psdk.DATA_TYPE.INT8_T).
                  If None, uses the last datatype set on the scope.
    """
    # Lock Y interactions; allow X-only mouse pan/zoom via ViewBox
    vb = plot.getViewBox()
    vb.setMouseEnabled(x=True, y=False)
    
    # Disable auto-range for both axes initially
    plot.enableAutoRange(x=False, y=False)
    
    # Set x-range based on sample count (TimeAxisItem converts to time for display)
    plot.setXRange(0, max_sample_index, padding=0)
    
    # Set y-axis range based on ADC limits if scope is provided
    if scope is not None:
        update_y_axis_from_adc_limits(plot, scope, datatype=datatype)
    else:
        # Fallback to default range if scope not provided
        plot.setYRange(-150, 150, padding=0)
        vb.setLimits(yMin=-150, yMax=150)
    
    # Add legend
    plot.addLegend()
    
    # Note: autoRange() is called separately after this function to allow x-axis adjustment
    # Y-axis constraints are locked via setLimits() above


def update_y_axis_from_adc_limits(plot, scope, datatype=None):
    """
    Update y-axis range to fixed ADC limits from the scope.
    
    Uses scope.get_adc_limits() to get the actual ADC limits based on the device
    resolution and data type. Adds a small margin for visibility.
    
    Args:
        plot: PyQtGraph plot widget
        scope: PicoScope object to get ADC limits from
        datatype: Optional DATA_TYPE enum (e.g., psdk.DATA_TYPE.INT8_T). 
                  If None, uses the last datatype set on the scope.
    """
    # Get ADC limits from scope
    min_adc, max_adc = scope.get_adc_limits(datatype=datatype)
    
    # Add small margin for visibility (2 counts on each side)
    margin = 2.0
    y_min = float(min_adc) - margin
    y_max = float(max_adc) + margin
    
    print(f"[PLOT] ADC limits from scope: {min_adc} to {max_adc} (datatype: {datatype})")
    print(f"[PLOT] Y-axis set to: {y_min} to {y_max} ADC counts (with {margin} count margin)")
    
    vb = plot.getViewBox()
    
    # Disable auto-range for Y-axis (critical for maintaining fixed range)
    plot.enableAutoRange(x=False, y=False)
    
    # Lock y-axis limits first to prevent auto-range from interfering
    vb.setLimits(yMin=y_min, yMax=y_max)
    
    # Set y-axis range with no padding (padding=0 ensures exact range)
    plot.setYRange(y_min, y_max, padding=0)
    
    # Force the viewbox to update its range immediately
    vb.enableAutoRange(enable=False)


def enforce_y_axis_adc_limits(plot, scope, buffer_percent=0.05, datatype=None):
    """
    Enforce y-axis constraints based on ADC limits from scope.
    Call this after any autoRange() operations to maintain y-axis constraints.
    
    Note: This function now uses exact ADC limits (no buffer) to match the main behavior.
    
    Args:
        plot: PyQtGraph plot widget
        scope: PicoScope object to get ADC limits from
        buffer_percent: Deprecated - kept for compatibility but not used (exact limits used instead)
        datatype: Optional DATA_TYPE enum (e.g., psdk.DATA_TYPE.INT8_T).
                  If None, uses the last datatype set on the scope.
    """
    # Use the same function as setup to ensure consistency
    update_y_axis_from_adc_limits(plot, scope, datatype=datatype)


@njit
def _calculate_raw_data_time_alignment_numba(ring_filled, downsampling_ratio, 
                                             trigger_at_sample, n_raw_samples):
    """
    Numba-optimized core calculation for raw data time alignment.
    
    Args:
        ring_filled: Number of filled samples in ring buffer
        downsampling_ratio: Downsampling ratio
        trigger_at_sample: Trigger position in downsampled space
        n_raw_samples: Number of raw samples retrieved
        
    Returns:
        tuple: (raw_start_pos, raw_end_pos)
    """
    # Calculate where the downsampled trace ends (in original sample space)
    if ring_filled > 0:
        # Last point in downsampled data is at (ring_filled - 1) * DOWNSAMPLING_RATIO
        downsampled_end_pos = (ring_filled - 1) * downsampling_ratio
    else:
        # Fallback: use trigger position if no downsampled data
        downsampled_end_pos = trigger_at_sample * downsampling_ratio
    
    # The raw trace should end at the same position as the downsampled trace
    raw_end_pos = downsampled_end_pos
    
    # The raw trace should extend backwards by the number of raw samples we retrieved
    # Each raw sample is one original ADC sample, so we work backwards from the end
    raw_start_pos = raw_end_pos - (n_raw_samples - 1)  # -1 because we include both start and end points
    
    return raw_start_pos, raw_end_pos


def calculate_raw_data_time_alignment(ring_filled, downsampling_ratio, trigger_at_sample, 
                                      n_raw_samples):
    """
    Calculate sample index alignment for raw data overlay on downsampled plot.
    The raw trace should end where the downsampled trace ends and work backwards.
    
    Returns integer sample indices (in raw ADC sample space). The TimeAxisItem
    handles conversion to time for display.
    
    Args:
        ring_filled: Number of filled samples in ring buffer
        downsampling_ratio: Downsampling ratio
        trigger_at_sample: Trigger position in downsampled space
        n_raw_samples: Number of raw samples retrieved
        
    Returns:
        tuple: (raw_x_indices, raw_end_pos, raw_start_pos) where raw_x_indices is 
               an int64 array of sample indices in raw ADC sample space
    """
    # Use Numba-optimized calculation if available
    if NUMBA_AVAILABLE:
        raw_start_pos, raw_end_pos = _calculate_raw_data_time_alignment_numba(
            ring_filled, downsampling_ratio, trigger_at_sample, n_raw_samples
        )
    else:
        # Fallback to original calculation
        if ring_filled > 0:
            downsampled_end_pos = (ring_filled - 1) * downsampling_ratio
        else:
            downsampled_end_pos = trigger_at_sample * downsampling_ratio
        raw_end_pos = downsampled_end_pos
        raw_start_pos = raw_end_pos - (n_raw_samples - 1)
    
    # Create x-axis for raw data as integer sample indices
    # Each raw sample corresponds to one original ADC sample
    # The raw data should span from raw_start_pos to raw_end_pos
    # Raw samples are consecutive: [raw_start_pos, raw_start_pos+1, ..., raw_end_pos]
    raw_x_indices = np.arange(n_raw_samples, dtype=np.int64) + int(raw_start_pos)
    
    return raw_x_indices, raw_end_pos, raw_start_pos


def format_memory_size(bytes_value):
    """
    Format memory size in bytes to human-readable format.
    
    Args:
        bytes_value: Memory size in bytes
        
    Returns:
        str: Formatted string (e.g., "1.5 GB", "512 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} PB"
