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


def update_plot(curve, data_array, ring_head, ring_filled, python_ring_buffer, 
                downsampling_ratio, data_lock, data_updated):
    """
    Update the PyQtGraph plot with latest streaming data.
    
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
            # Create x-axis with gaps for downsampled data
            x_vals = np.arange(ring_filled, dtype=np.float32) * downsampling_ratio
        else:
            # Full: logical order is [ring_head..end) then [0..ring_head)
            y_vals = np.concatenate((data_array[ring_head:], data_array[:ring_head]))
            # Create x-axis with gaps for downsampled data
            x_vals = np.arange(python_ring_buffer, dtype=np.float32) * downsampling_ratio

        # Update scatter plot (individual points, no connecting lines)
        curve.setData(x_vals, y_vals)
        
        # Reset the data update flag
        data_updated = False
        return True


def update_buffer_status(current, total, downsampling_ratio, hardware_adc_sample_rate, status_displays):
    """
    Update the display window time and sample count in top bar.
    
    Args:
        current: Current number of samples in buffer
        total: Total buffer size
        downsampling_ratio: Downsampling ratio
        hardware_adc_sample_rate: Hardware ADC sample rate
        status_displays: Dictionary of status display widgets
    """
    # Calculate time window based on current samples
    original_samples = current * downsampling_ratio
    time_seconds = original_samples / hardware_adc_sample_rate if hardware_adc_sample_rate > 0 else 0
    
    # Format time in appropriate units
    if time_seconds >= 60:
        time_str = f"{time_seconds/60:.1f} min"
    elif time_seconds >= 1:
        time_str = f"{time_seconds:.1f} s"
    else:
        time_str = f"{time_seconds*1000:.1f} ms"
    
    status_displays['display_window'].setText(f'{time_str} ({current:,} / {total:,})')


def update_efficiency_display(efficiency, jitter, status, status_displays):
    """
    Update the efficiency display with color coding based on both efficiency and jitter.
    
    Args:
        efficiency: Average efficiency percentage
        jitter: Standard deviation of efficiency (consistency metric)
        status: Overall status ('excellent', 'good', 'warning', 'critical', 'initializing')
        status_displays: Dictionary of status display widgets
    """
    # Choose color based on status
    if status == "excellent":
        color = "#90EE90"  # Light green
        bg_color = "#2d4a2d"
        border_color = "#4a6b4a"
        status_icon = "[ACTIVE]"  # Solid circle
        status_text = "Excellent"
    elif status == "good":
        color = "#90EE90"  # Light green
        bg_color = "#2d4a2d"
        border_color = "#4a6b4a"
        status_icon = "[ACTIVE]"
        status_text = "Good"
    elif status == "warning":
        color = "#FFD700"  # Gold/Yellow
        bg_color = "#4a4a2d"
        border_color = "#6b6b4a"
        status_icon = "◐"  # Half-filled circle
        status_text = "Warning"
    elif status == "critical":
        color = "#FF6B6B"  # Light red
        bg_color = "#4a2d2d"
        border_color = "#6b4a4a"
        status_icon = "[DISABLED]"  # Empty circle
        status_text = "Critical"
    else:  # initializing
        color = "#CCCCCC"  # Gray
        bg_color = "#3a3a3a"
        border_color = "#555555"
        status_icon = "◌"
        status_text = "Starting..."
    
    # Format display text with efficiency and jitter
    if jitter > 0:
        display_text = f"{status_icon} {efficiency:.1f}% (±{jitter:.1f}%)"
    else:
        display_text = f"{status_icon} {efficiency:.1f}%"
    
    status_displays['efficiency'].setText(display_text)
    status_displays['efficiency'].setStyleSheet(f"""
        QLabel {{
            background-color: {bg_color};
            color: {color};
            border: 1px solid {border_color};
            padding: 2px 8px;
            font-size: 11px;
            font-weight: bold;
            border-radius: 3px;
        }}
    """)
    
    # Update tooltip with detailed information - styled for readability
    tooltip_text = f"""
    <div style='background-color: #2b2b2b; color: #ffffff; padding: 8px; border: 1px solid #555555;'>
        <p style='margin: 2px; color: {color};'><b>System Performance: {status_text}</b></p>
        <p style='margin: 2px; color: #ffffff;'>Average Efficiency: <b>{efficiency:.2f}%</b></p>
        <p style='margin: 2px; color: #ffffff;'>Consistency (Jitter): <b>±{jitter:.2f}%</b></p>
        <hr style='border: 0; border-top: 1px solid #555555; margin: 6px 0;'>
        <p style='margin: 2px; color: #cccccc;'><b>Status Levels:</b></p>
        <p style='margin: 2px; color: #90EE90;'>[ACTIVE] <b>Excellent:</b> Avg≥95%, Jitter&lt;5%</p>
        <p style='margin: 2px; color: #90EE90;'>[ACTIVE] <b>Good:</b> Avg≥90%, Jitter&lt;10%</p>
        <p style='margin: 2px; color: #FFD700;'>◐ <b>Warning:</b> Avg≥80% or Jitter&lt;15%</p>
        <p style='margin: 2px; color: #FF6B6B;'>[DISABLED] <b>Critical:</b> System falling behind</p>
    </div>
    """
    status_displays['efficiency'].setToolTip(tooltip_text)


def calculate_efficiency_status(efficiency_history):
    """
    Calculate efficiency status based on history.
    
    Args:
        efficiency_history: Deque of efficiency measurements
        
    Returns:
        tuple: (efficiency_avg, efficiency_jitter, status)
    """
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


def drain_remaining_buffers(scope, buffer_0, buffer_1, data_array, ring_head, ring_filled, 
                          python_ring_buffer, data_lock, plot_signal, downsampling_mode, 
                          adc_data_type, drain_timeout=2.0):
    """
    Drain any remaining data from hardware buffers after streaming stops.
    
    Args:
        scope: PicoScope device instance
        buffer_0: First hardware buffer
        buffer_1: Second hardware buffer
        data_array: Circular buffer array
        ring_head: Current head position in ring buffer
        ring_filled: Number of filled samples
        python_ring_buffer: Total ring buffer size
        data_lock: Threading lock for data access
        plot_signal: Signal object for thread-safe communication
        downsampling_mode: Downsampling mode
        adc_data_type: ADC data type
        drain_timeout: Maximum time to spend draining (seconds)
        
    Returns:
        int: Total number of samples drained
    """
    print("Hardware stopped - draining remaining buffer data...")
    plot_signal.title_updated.emit("Hardware Stopped - Draining Buffers...")
    
    total_drained = 0
    drain_start = time.perf_counter()
    
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
                        data_array[ring_head] = sample
                        ring_head = (ring_head + 1) % python_ring_buffer
                        if ring_filled < python_ring_buffer:
                            ring_filled += 1
                    plot_signal.buffer_status_updated.emit(ring_filled, python_ring_buffer)
                
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
    return total_drained


def create_plot_curve(plot, antialias=False):
    """
    Create an optimized plot curve for downsampled data visualization.
    
    Args:
        plot: PyQtGraph plot widget
        antialias: Whether to enable antialiasing
        
    Returns:
        PyQtGraph plot curve object
    """
    # Create plot curve with performance settings (scatter plot for downsampled data)
    curve = plot.plot(
        pen=None,                                          # No line connecting points
        symbol='o',                                        # Circle symbol for each point
        symbolSize=3,                                      # Size of each point
        symbolBrush='cyan',                                # Fill color of points
        symbolPen=pg.mkPen(color='cyan', width=1),         # Border color of points
        antialias=antialias,                               # Antialiasing setting
        clipToView=True,                                   # Only render visible data
        autoDownsample=False,                              # Manual downsampling control
        name='Downsampled Data'                            # Legend name
    )
    
    return curve


def setup_plot_optimizations(plot, target_time_window, hardware_adc_sample_rate):
    """
    Configure plot optimizations for real-time streaming.
    
    Args:
        plot: PyQtGraph plot widget
        target_time_window: Target time window in seconds
        hardware_adc_sample_rate: Hardware ADC sample rate
    """
    # Lock Y interactions; allow X-only mouse pan/zoom via ViewBox
    vb = plot.getViewBox()
    vb.setMouseEnabled(x=True, y=False)
    
    # Keep y-axis fixed, let x-axis use default behavior
    plot.enableAutoRange(x=False, y=False)
    
    # Set plot range for ADC counts (8-bit ADC data)
    plot.setYRange(-150, 150)
    
    # Set x-range based on time window (time_window × ADC_rate = total samples)
    plot.setXRange(0, target_time_window * hardware_adc_sample_rate, padding=0)
    
    # Add legend
    plot.addLegend()
