"""
UI Management Helper Functions for PicoScope Streaming Application

This module contains all UI management, coordination, and settings application
functions for handling user interface interactions and settings updates.
"""

import time
import numpy as np
import pypicosdk as psdk
from hardware_helpers import (
    calculate_sample_rate, register_double_buffers, start_hardware_streaming,
    stop_hardware_streaming, clear_hardware_buffers, calculate_optimal_buffer_size,
    validate_buffer_size, apply_trigger_configuration
)


def collect_ui_settings(ratio_spinbox, mode_combo, interval_spinbox, units_combo,
                      hw_buffer_spinbox, refresh_spinbox, poll_spinbox,
                      time_window_slider, max_pre_trigger_spinbox, max_post_trigger_spinbox,
                      trigger_enable_checkbox, trigger_threshold_spinbox):
    """
    Collect all settings from UI widgets.
    
    Args:
        ratio_spinbox: Downsampling ratio spinbox
        mode_combo: Downsampling mode combobox
        interval_spinbox: Sample interval spinbox
        units_combo: Time units combobox
        hw_buffer_spinbox: Hardware buffer size spinbox
        refresh_spinbox: Refresh rate spinbox
        poll_spinbox: Polling interval spinbox
        time_window_slider: Time window slider
        max_pre_trigger_spinbox: Max pre trigger spinbox
        max_post_trigger_spinbox: Max post trigger spinbox
        trigger_enable_checkbox: Trigger enable checkbox
        trigger_threshold_spinbox: Trigger threshold spinbox
    
    Returns:
        dict: Dictionary containing all current UI values
    """
    return {
        'new_ratio': ratio_spinbox.value(),
        'new_mode': mode_combo.currentData(),
        'new_interval': interval_spinbox.value(),
        'new_units': units_combo.currentData(),
        'new_buffer_size': hw_buffer_spinbox.value(),
        'new_refresh_fps': refresh_spinbox.value(),
        'new_poll_interval': poll_spinbox.value() / 1000.0,  # Convert ms to seconds
        'new_time_window': float(time_window_slider.value()),
        'new_max_pre_trigger': max_pre_trigger_spinbox.value(),
        'new_max_post_trigger': max_post_trigger_spinbox.value(),
        'new_trigger_enabled': trigger_enable_checkbox.isChecked(),
        'new_trigger_threshold': trigger_threshold_spinbox.value()
    }


def calculate_what_changed(settings, current_settings):
    """
    Determine which settings have changed.
    
    Args:
        settings: Dictionary of new settings from UI
        current_settings: Dictionary of current settings
    
    Returns:
        tuple: (settings_changed, performance_changed, time_window_changed, trigger_changed)
    """
    settings_changed = (
        settings['new_ratio'] != current_settings['DOWNSAMPLING_RATIO'] or
        settings['new_mode'] != current_settings['DOWNSAMPLING_MODE'] or
        settings['new_interval'] != current_settings['sample_interval'] or
        settings['new_units'] != current_settings['time_units'] or
        settings['new_buffer_size'] != current_settings['SAMPLES_PER_BUFFER'] or
        settings['new_max_pre_trigger'] != current_settings['MAX_PRE_TRIGGER_SAMPLES'] or
        settings['new_max_post_trigger'] != current_settings['MAX_POST_TRIGGER_SAMPLES']
    )
    
    performance_changed = (
        settings['new_refresh_fps'] != current_settings['REFRESH_FPS'] or
        settings['new_poll_interval'] != current_settings['POLLING_INTERVAL']
    )
    
    time_window_changed = (settings['new_time_window'] != current_settings['TARGET_TIME_WINDOW'])
    
    trigger_changed = (
        settings['new_trigger_enabled'] != current_settings['TRIGGER_ENABLED'] or
        settings['new_trigger_threshold'] != current_settings['TRIGGER_THRESHOLD_ADC']
    )
    
    return settings_changed, performance_changed, time_window_changed, trigger_changed


def validate_and_optimize_settings(settings, cached_max_memory, max_post_trigger_spinbox, hw_buffer_spinbox):
    """
    Validate settings and auto-calculate optimal buffer sizes.
    
    Args:
        settings: Dictionary of new settings from UI
        cached_max_memory: Cached maximum available memory
        max_post_trigger_spinbox: Max post trigger spinbox widget
        hw_buffer_spinbox: Hardware buffer spinbox widget
    
    Returns:
        tuple: (is_valid, updated_settings)
    """
    new_ratio = settings['new_ratio']
    new_buffer_size = settings['new_buffer_size']
    ratio_changed = (new_ratio != settings.get('current_ratio', new_ratio))
    buffer_size_changed = (new_buffer_size != settings.get('current_buffer_size', new_buffer_size))
    
    # Update max post trigger range if buffer size changed
    if buffer_size_changed:
        update_max_post_trigger_range(new_buffer_size, max_post_trigger_spinbox)
        print(f"[OK] Updated max post trigger range (buffer size changed)")
        
        # If current max post trigger is too large, auto-adjust it
        current_max_post = max_post_trigger_spinbox.value()
        if current_max_post >= new_buffer_size:
            safe_max_post = int(new_buffer_size * 0.9)
            max_post_trigger_spinbox.setValue(safe_max_post)
            settings['new_max_post_trigger'] = safe_max_post
            print(f"  [OK] Auto-adjusted max post trigger: {current_max_post:,} → {safe_max_post:,} samples")
    
    # Auto-calculate optimal buffer size if ratio changed
    if ratio_changed and cached_max_memory is not None:
        optimal_buffer_size = calculate_optimal_buffer_size(cached_max_memory, new_ratio)
        
        # Update buffer size to optimal value
        settings['new_buffer_size'] = optimal_buffer_size
        hw_buffer_spinbox.setValue(optimal_buffer_size)
        print(f"  [OK] Spinbox updated to {optimal_buffer_size:,} samples")
        
        # Update max post trigger spinbox range to match new buffer size
        update_max_post_trigger_range(optimal_buffer_size, max_post_trigger_spinbox)
    elif ratio_changed and cached_max_memory is None:
        print(f"[WARNING] WARNING: Cannot auto-calculate buffer size (max memory unknown)")
        print(f"  Using manual spinbox value: {new_buffer_size:,}")
        print(f"  This will require {new_buffer_size * new_ratio:,} samples of memory!")
        
        # Update max post trigger spinbox range to match new buffer size
        update_max_post_trigger_range(new_buffer_size, max_post_trigger_spinbox)
    
    # Validate memory requirements
    memory_required = settings['new_buffer_size'] * new_ratio
    if cached_max_memory is not None:
        is_valid, _, _ = validate_buffer_size(settings['new_buffer_size'], new_ratio, cached_max_memory)
        if not is_valid:
            return False, settings
    else:
        print(f"[WARNING] WARNING: Cannot verify memory safety (max memory unknown)")
        print(f"  Will attempt to use {memory_required:,} samples")
    
    # Validate max post trigger samples
    new_max_post_trigger = settings['new_max_post_trigger']
    if new_max_post_trigger >= new_buffer_size:
        print(f"[WARNING] ERROR: Max post trigger samples too large!")
        print(f"  Max post trigger: {new_max_post_trigger:,} samples")
        print(f"  Buffer size: {new_buffer_size:,} samples")
        print(f"  Max post trigger must be less than buffer size")
        
        # Auto-adjust to safe value (90% of buffer size)
        safe_max_post_trigger = int(new_buffer_size * 0.9)
        settings['new_max_post_trigger'] = safe_max_post_trigger
        
        # Update the UI spinbox to reflect the corrected value
        max_post_trigger_spinbox.setValue(safe_max_post_trigger)
        
        print(f"  [OK] Auto-adjusted max post trigger to: {safe_max_post_trigger:,} samples (90% of buffer size)")
    
    return True, settings


def update_max_post_trigger_range(buffer_size, max_post_trigger_spinbox):
    """
    Update max post trigger range based on buffer size.
    
    Args:
        buffer_size: New buffer size to set range based on
        max_post_trigger_spinbox: Spinbox widget to update
    """
    max_allowed = buffer_size - 1
    max_post_trigger_spinbox.setRange(100, max_allowed)
    print(f"[OK] Updated max post trigger range: 100 to {max_allowed:,} samples")


def apply_performance_settings(settings, timer):
    """
    Apply new performance settings (refresh rate and polling interval).
    Does not require streaming restart.
    
    Args:
        settings: Dictionary containing new settings
        timer: Qt timer object for plot updates
    
    Returns:
        tuple: (new_refresh_fps, new_polling_interval)
    """
    new_refresh_fps = settings['new_refresh_fps']
    new_polling_interval = settings['new_poll_interval']
    
    # Update timer
    refresh_interval_ms = int(1000 / new_refresh_fps)
    timer.setInterval(refresh_interval_ms)
    
    print(f"[OK] Performance settings updated: refresh={new_refresh_fps} FPS ({refresh_interval_ms}ms), poll={new_polling_interval*1000:.2f}ms")
    
    return new_refresh_fps, new_polling_interval


def apply_time_window(settings, settings_changed, performance_changed, 
                     data_lock, python_ring_buffer, data_array, x_data, 
                     ring_head, ring_filled, hardware_adc_sample_rate, 
                     plot, plot_signal):
    """
    Apply time window change (reallocate ring buffer without streaming restart).
    
    Args:
        settings: Dictionary containing new settings
        settings_changed: Whether streaming settings changed
        performance_changed: Whether performance settings changed
        data_lock: Threading lock for data access
        python_ring_buffer: Current ring buffer size (will be updated)
        data_array: Ring buffer data array (will be updated)
        x_data: X-axis data array (will be updated)
        ring_head: Ring buffer head position (will be updated)
        ring_filled: Ring buffer filled count (will be updated)
        hardware_adc_sample_rate: Hardware ADC sample rate
        plot: Plot widget for x-range update
        plot_signal: Signal object for thread-safe communication
    
    Returns:
        tuple: (should_return_early, new_ring_buffer_size)
    """
    new_time_window = settings['new_time_window']
    new_ratio = settings['new_ratio']
    
    # Calculate new ring buffer size
    if settings_changed:
        expected_adc_rate = calculate_sample_rate(settings['new_interval'], settings['new_units'])
        print(f"  Estimated ADC rate: {expected_adc_rate:.2f} Hz (will be refined after restart)")
    else:
        expected_adc_rate = hardware_adc_sample_rate
    
    old_ring_buffer = python_ring_buffer
    # Calculate desired buffer size for time window
    calculated_buffer = int((new_time_window * expected_adc_rate) / new_ratio)
    # Minimum for smooth plotting: 100 samples or actual calculation, whichever is larger
    # This prevents tiny buffers while allowing high ratios to work correctly
    new_ring_buffer = max(100, calculated_buffer)
    print(f"Ring buffer size: {old_ring_buffer:,} -> {new_ring_buffer:,} samples")
    print(f"  (Time window: {new_time_window:.1f}s, ADC rate: {expected_adc_rate:.2f} Hz, Ratio: {new_ratio}:1)")
    
    # Apply time window change if streaming not changing
    if new_time_window != settings.get('current_time_window', new_time_window) and not settings_changed:
        if new_ring_buffer != old_ring_buffer:
            # Pause briefly to avoid race condition
            with data_lock:
                python_ring_buffer = new_ring_buffer
                data_array = np.zeros(python_ring_buffer, dtype=np.float32)
                x_data = np.arange(python_ring_buffer, dtype=np.float32)
                ring_head = 0
                ring_filled = 0
            print(f"[OK] Display window updated: {new_time_window:.1f}s ({python_ring_buffer:,} samples)")
            # Update the plot x-range
            plot.setXRange(0, new_time_window * hardware_adc_sample_rate, padding=0)
            # Update display window label
            plot_signal.buffer_status_updated.emit(0, python_ring_buffer)
        else:
            print(f"[OK] Time window setting updated (buffer size unchanged)")
        
        if not settings_changed and not performance_changed:
            return True, new_ring_buffer  # Early return
    
    return False, new_ring_buffer


def apply_streaming_restart(settings, scope, buffer_0, buffer_1, data_lock, 
                           python_ring_buffer, data_array, x_data, ring_head, ring_filled,
                           hardware_adc_sample_rate, settings_update_in_progress, 
                           settings_update_event, efficiency_history, perf_samples_window,
                           status_displays, plot_signal, mode_combo, cached_max_memory):
    """
    Stop, reconfigure, and restart hardware streaming with new settings.
    
    Args:
        settings: Dictionary containing new settings
        scope: PicoScope device instance
        buffer_0: First hardware buffer
        buffer_1: Second hardware buffer
        data_lock: Threading lock for data access
        python_ring_buffer: Ring buffer size (will be updated)
        data_array: Ring buffer data array (will be updated)
        x_data: X-axis data array (will be updated)
        ring_head: Ring buffer head position (will be updated)
        ring_filled: Ring buffer filled count (will be updated)
        hardware_adc_sample_rate: Hardware ADC sample rate (will be updated)
        settings_update_in_progress: Settings update flag
        settings_update_event: Settings update event
        efficiency_history: Efficiency tracking deque
        perf_samples_window: Performance tracking deque
        status_displays: Status display widgets
        plot_signal: Signal object for thread-safe communication
        mode_combo: Mode combobox for display text
        cached_max_memory: Cached maximum memory
    
    Returns:
        tuple: (success, new_hardware_adc_sample_rate, new_ring_buffer_size)
    """
    new_ratio = settings['new_ratio']
    new_mode = settings['new_mode']
    new_interval = settings['new_interval']
    new_units = settings['new_units']
    new_buffer_size = settings['new_buffer_size']
    new_time_window = settings['new_time_window']
    new_max_pre_trigger = settings['new_max_pre_trigger']
    new_max_post_trigger = settings['new_max_post_trigger']
    
    # Calculate ring buffer requirements
    expected_adc_rate = calculate_sample_rate(new_interval, new_units)
    old_ring_buffer = python_ring_buffer
    # Calculate desired buffer size for time window
    calculated_buffer = int((new_time_window * expected_adc_rate) / new_ratio)
    # Minimum for smooth plotting: 100 samples or actual calculation, whichever is larger
    # This prevents tiny buffers while allowing high ratios to work correctly
    new_ring_buffer = max(100, calculated_buffer)
    
    # Check if hardware buffer size changed
    old_buffer_size = settings.get('current_buffer_size', new_buffer_size)
    buffer_size_changed = (new_buffer_size != old_buffer_size)
    
    # Signal streaming thread to pause
    settings_update_in_progress = True
    print("Signaling streaming thread to pause...")
    time.sleep(0.1)
    
    try:
        # Stop streaming
        print("Stopping current streaming...")
        stop_hardware_streaming(scope)
        time.sleep(0.5)
        
        # Clear all buffers
        print("Clearing buffers...")
        clear_hardware_buffers(scope)
        
        # Update global variables (these would be passed back to main)
        updated_settings = {
            'DOWNSAMPLING_RATIO': new_ratio,
            'DOWNSAMPLING_MODE': new_mode,
            'sample_interval': new_interval,
            'time_units': new_units,
            'SAMPLES_PER_BUFFER': new_buffer_size,
            'TARGET_TIME_WINDOW': new_time_window,
            'MAX_PRE_TRIGGER_SAMPLES': new_max_pre_trigger,
            'MAX_POST_TRIGGER_SAMPLES': new_max_post_trigger,
            'hardware_adc_sample_rate': expected_adc_rate
        }
        
        print(f"[OK] Updated hardware ADC rate: {expected_adc_rate:.2f} Hz")
        print(f"[OK] Updated trigger samples: pre={new_max_pre_trigger:,}, post={new_max_post_trigger:,}")
        
        # Clear efficiency history since calculation basis changed
        efficiency_history.clear()
        perf_samples_window.clear()  # Clear performance window too!
        print("[OK] Cleared efficiency and performance tracking for recalculation")
        
        # Reallocate hardware buffers if size changed
        if buffer_size_changed:
            buffer_0 = np.zeros(new_buffer_size, dtype=np.int8)  # Assuming INT8_T
            buffer_1 = np.zeros(new_buffer_size, dtype=np.int8)
            print(f"[OK] Hardware buffers reallocated: {new_buffer_size:,} samples")
        
        # Reallocate ring buffer if size changed
        if new_ring_buffer != old_ring_buffer:
            python_ring_buffer = new_ring_buffer
            data_array = np.zeros(python_ring_buffer, dtype=np.float32)
            x_data = np.arange(python_ring_buffer, dtype=np.float32)
            ring_head = 0
            ring_filled = 0
            print(f"[OK] Ring buffer reallocated: {python_ring_buffer:,} samples (time window: {new_time_window:.1f}s)")
        
        # Re-register buffers with new settings
        print(f"Re-registering buffers with ratio={new_ratio}, mode={new_mode}")
        register_double_buffers(scope, buffer_0, buffer_1, new_buffer_size, 
                               psdk.DATA_TYPE.INT8_T, new_mode)
        
        # Restart streaming with new parameters
        print("Restarting streaming with new parameters...")
        actual_interval = start_hardware_streaming(scope, new_interval, new_units, 
                                                 new_max_pre_trigger, new_max_post_trigger,
                                                 new_ratio, new_mode)
        
        print(f"[OK] Streaming restarted successfully")
        print(f"  New ratio: {new_ratio}:1")
        print(f"  New mode: {mode_combo.currentText()}")
        print(f"  Actual interval: {actual_interval} {new_units}")
        
        # Calculate new sample rate
        new_rate = calculate_sample_rate(actual_interval, new_units)
        
        # Update global hardware ADC sample rate
        updated_settings['hardware_adc_sample_rate'] = new_rate
        print(f"  Hardware ADC rate: {new_rate:.2f} Hz")
        
        downsampled_rate = new_rate / new_ratio
        print(f"  Downsampled rate: {downsampled_rate:.2f} Hz")
        
        # Update rate displays
        adc_msps = new_rate / 1_000_000
        downsampled_msps = adc_msps / new_ratio
        status_displays['adc_rate'].setText(f"{adc_msps:.3f} MSPS")
        status_displays['downsampled_rate'].setText(f"{downsampled_msps:.3f} MSPS")
        
        # Update min poll interval display
        try:
            down_rate_hz = new_rate / new_ratio
            if down_rate_hz > 0:
                min_poll_seconds = new_buffer_size / down_rate_hz
                min_poll_ms = min_poll_seconds * 1000.0
                status_displays['min_poll'].setText(f"{min_poll_ms:.2f} ms")
        except Exception:
            pass
        
        # Update memory requirement display
        memory_required = new_buffer_size * new_ratio
        status_displays['memory_req'].setText(f"{memory_required:,} samples")
        
        # Update display window
        status_displays['display_window'].setText(f'0.0 s (0 / {python_ring_buffer:,})')
        
        plot_signal.title_updated.emit(
            f"Real-time Streaming Data - {new_ratio}:1 {mode_combo.currentText()}"
        )
        
        return True, new_rate, new_ring_buffer
        
    except Exception as e:
        print(f"[WARNING] Error updating settings: {e}")
        print(f"  Attempting to restore previous settings...")
        # Try to restore previous settings
        try:
            stop_hardware_streaming(scope)
            time.sleep(0.5)
            clear_hardware_buffers(scope)
            register_double_buffers(scope, buffer_0, buffer_1, old_buffer_size, 
                                   psdk.DATA_TYPE.INT8_T, settings.get('current_mode', new_mode))
            start_hardware_streaming(scope, settings.get('current_interval', new_interval), 
                                   settings.get('current_units', new_units),
                                   settings.get('current_max_pre_trigger', new_max_pre_trigger),
                                   settings.get('current_max_post_trigger', new_max_post_trigger),
                                   settings.get('current_ratio', new_ratio),
                                   settings.get('current_mode', new_mode))
            print("[OK] Restored to previous settings")
        except Exception as restore_error:
            print(f"[WARNING] Failed to restore settings: {restore_error}")
        
        plot_signal.title_updated.emit("Error updating settings - check console")
        return False, None, None
    
    finally:
        # Signal streaming thread to resume
        settings_update_in_progress = False
        settings_update_event.set()
        print("Signaled streaming thread to resume")


def restart_streaming(scope, buffer_0, buffer_1, data_array, ring_head, ring_filled,
                     python_ring_buffer, downsampling_ratio, downsampling_mode,
                     hardware_adc_sample_rate, plot_signal, mode_combo):
    """
    Restart streaming after it was stopped.
    
    Args:
        scope: PicoScope device instance
        buffer_0: First hardware buffer
        buffer_1: Second hardware buffer
        data_array: Ring buffer data array
        ring_head: Ring buffer head position
        ring_filled: Ring buffer filled count
        python_ring_buffer: Ring buffer size
        downsampling_ratio: Downsampling ratio
        downsampling_mode: Downsampling mode
        hardware_adc_sample_rate: Hardware ADC sample rate
        plot_signal: Signal object for thread-safe communication
        mode_combo: Mode combobox for display text
    
    Returns:
        bool: True if successful, False if error occurred
    """
    print("Restarting streaming...")
    
    # Clear and reset buffers
    print("Clearing buffers...")
    scope.set_data_buffer(psdk.CHANNEL.A, 0, action=psdk.ACTION.CLEAR_ALL)
    time.sleep(0.1)
    
    # Reset ring buffer
    ring_head = 0
    ring_filled = 0
    data_array.fill(0)
    
    # Re-register hardware buffers
    print(f"Re-registering buffers with ratio={downsampling_ratio}, mode={downsampling_mode}")
    register_double_buffers(scope, buffer_0, buffer_1, len(buffer_0), 
                           psdk.DATA_TYPE.INT8_T, downsampling_mode)
    
    # Restart hardware streaming
    try:
        actual_interval = start_hardware_streaming(scope, 800, psdk.TIME_UNIT.PS, 
                                                 0, 10000, downsampling_ratio, downsampling_mode)
        print(f"[OK] Hardware streaming restarted (interval={actual_interval})")
    except Exception as e:
        print(f"[WARNING] Error restarting streaming: {e}")
        plot_signal.title_updated.emit("Error Restarting - Check Console")
        return False
    
    # Update UI
    plot_signal.title_updated.emit(f"Real-time Streaming Data - {downsampling_ratio}:1 {mode_combo.currentText()}")
    return True
