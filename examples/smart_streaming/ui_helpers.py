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
    validate_buffer_size, apply_trigger_configuration, time_to_samples, TIME_UNIT_TO_SECONDS,
    get_datatype_for_mode
)
import data_processing

# Import Qt for deferred plot updates
try:
    from pyqtgraph.Qt import QtCore
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False


def apply_channel_siggen_settings(settings, scope):
    """
    Apply channel and signal generator settings to hardware.
    
    Args:
        settings: Dictionary containing channel and sig gen settings
        scope: PicoScope device instance
    
    Returns:
        bool: True if settings were applied successfully, False otherwise
    """
    try:
        # Apply channel settings if provided
        if 'new_channel_range' in settings or 'new_channel_coupling' in settings or 'new_channel_probe_scale' in settings:
            channel_range = settings.get('new_channel_range', psdk.RANGE.mV500)
            channel_coupling = settings.get('new_channel_coupling', psdk.COUPLING.AC)
            channel_probe_scale = settings.get('new_channel_probe_scale', 1.0)
            
            print(f"[CHANNEL] Applying channel settings: range={channel_range}, coupling={channel_coupling}, probe_scale={channel_probe_scale}")
            scope.set_channel(
                channel=psdk.CHANNEL.A,
                range=channel_range,
                coupling=channel_coupling,
                probe_scale=channel_probe_scale
            )
            print("[CHANNEL] Channel settings applied successfully")
        
        # Apply signal generator settings if provided
        if 'new_siggen_frequency' in settings or 'new_siggen_pk2pk' in settings or 'new_siggen_wave_type' in settings:
            siggen_freq = settings.get('new_siggen_frequency', 1.0)
            siggen_pk2pk = settings.get('new_siggen_pk2pk', 0.95)
            siggen_wave_type = settings.get('new_siggen_wave_type', psdk.WAVEFORM.SINE)
            
            print(f"[SIGGEN] Applying signal generator settings: frequency={siggen_freq} Hz, pk2pk={siggen_pk2pk} V, wave_type={siggen_wave_type}")
            scope.set_siggen(
                frequency=siggen_freq,
                pk2pk=siggen_pk2pk,
                wave_type=siggen_wave_type
            )
            print("[SIGGEN] Signal generator settings applied successfully")
        
        return True
    except Exception as e:
        print(f"[ERROR] Failed to apply channel/siggen settings: {e}")
        import traceback
        traceback.print_exc()
        return False


def collect_ui_settings(ratio_spinbox, mode_combo, interval_spinbox, units_combo,
                      hw_buffer_spinbox, refresh_spinbox, poll_spinbox,
                      time_window_spinbox, pre_trigger_time_spinbox, trigger_units_combo,
                      post_trigger_time_spinbox, trigger_units_combo_dup,
                      trigger_enable_checkbox, trigger_threshold_spinbox, trigger_direction_combo,
                      periodic_log_enable_checkbox=None, periodic_log_file_edit=None, periodic_log_rate_spinbox=None,
                      channel_range_combo=None, channel_coupling_combo=None, channel_probe_combo=None,
                      siggen_freq_spinbox=None, siggen_pk2pk_spinbox=None, siggen_wave_combo=None):
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
        time_window_spinbox: Time window spinbox
        max_pre_trigger_spinbox: Max pre trigger spinbox
        max_post_trigger_spinbox: Max post trigger spinbox
        trigger_enable_checkbox: Trigger enable checkbox
        trigger_threshold_spinbox: Trigger threshold spinbox
        trigger_direction_combo: Trigger direction combobox
        periodic_log_file_edit: Periodic log file path line edit (optional)
        periodic_log_rate_spinbox: Periodic log rate spinbox (optional)
    
    Returns:
        dict: Dictionary containing all current UI values
    """
    settings = {
        'new_ratio': ratio_spinbox.value(),
        'new_mode': mode_combo.currentData(),
        'new_interval': interval_spinbox.value(),
        'new_units': units_combo.currentData(),
        'new_buffer_size': hw_buffer_spinbox.value(),
        'new_refresh_fps': refresh_spinbox.value(),
        'new_poll_interval': poll_spinbox.value() / 1000.0,  # Convert ms to seconds
        'new_time_window': float(time_window_spinbox.value()),
        'new_pre_trigger_time': pre_trigger_time_spinbox.value(),
        'new_pre_trigger_units': trigger_units_combo.currentData(),
        'new_post_trigger_time': post_trigger_time_spinbox.value(),
        'new_post_trigger_units': trigger_units_combo.currentData(),  # Same shared units combo
        'new_trigger_enabled': trigger_enable_checkbox.isChecked(),
        'new_trigger_threshold': trigger_threshold_spinbox.value(),
        'new_trigger_direction': trigger_direction_combo.currentData()  # Get direction value from combo
    }
    
    # Add periodic logging settings if widgets are provided
    if periodic_log_enable_checkbox is not None:
        settings['new_periodic_log_enabled'] = periodic_log_enable_checkbox.isChecked()
    if periodic_log_file_edit is not None:
        settings['new_periodic_log_file'] = periodic_log_file_edit.text().strip()
    if periodic_log_rate_spinbox is not None:
        settings['new_periodic_log_rate'] = periodic_log_rate_spinbox.value()
    
    # Add channel and sig gen settings if widgets are provided
    if channel_range_combo is not None:
        settings['new_channel_range'] = channel_range_combo.currentData()
    if channel_coupling_combo is not None:
        settings['new_channel_coupling'] = channel_coupling_combo.currentData()
    if channel_probe_combo is not None:
        settings['new_channel_probe_scale'] = channel_probe_combo.currentData()
    if siggen_freq_spinbox is not None:
        settings['new_siggen_frequency'] = siggen_freq_spinbox.value()
    if siggen_pk2pk_spinbox is not None:
        settings['new_siggen_pk2pk'] = siggen_pk2pk_spinbox.value()
    if siggen_wave_combo is not None:
        settings['new_siggen_wave_type'] = siggen_wave_combo.currentData()
    
    return settings


def calculate_what_changed(settings, current_settings):
    """
    Determine which settings have changed.
    
    Args:
        settings: Dictionary of new settings from UI
        current_settings: Dictionary of current settings
    
    Returns:
        tuple: (settings_changed, performance_changed, time_window_changed, trigger_changed, channel_changed, siggen_changed)
    """
    # Channel changes require restart (hardware limitation: half-duplex USB)
    channel_changed = False
    if 'new_channel_range' in settings:
        channel_changed = channel_changed or (
            settings['new_channel_range'] != current_settings.get('channel_range')
        )
    if 'new_channel_coupling' in settings:
        channel_changed = channel_changed or (
            settings['new_channel_coupling'] != current_settings.get('channel_coupling')
        )
    if 'new_channel_probe_scale' in settings:
        channel_changed = channel_changed or (
            settings['new_channel_probe_scale'] != current_settings.get('channel_probe_scale')
        )
    
    # Signal generator changes can be applied immediately (no restart needed)
    siggen_changed = False
    if 'new_siggen_frequency' in settings:
        siggen_changed = siggen_changed or (
            settings['new_siggen_frequency'] != current_settings.get('siggen_frequency')
        )
    if 'new_siggen_pk2pk' in settings:
        siggen_changed = siggen_changed or (
            settings['new_siggen_pk2pk'] != current_settings.get('siggen_pk2pk')
        )
    if 'new_siggen_wave_type' in settings:
        siggen_changed = siggen_changed or (
            settings['new_siggen_wave_type'] != current_settings.get('siggen_wave_type')
        )
    
    # Streaming settings that require restart
    settings_changed = (
        settings['new_ratio'] != current_settings['DOWNSAMPLING_RATIO'] or
        settings['new_mode'] != current_settings['DOWNSAMPLING_MODE'] or
        settings['new_interval'] != current_settings['sample_interval'] or
        settings['new_units'] != current_settings['time_units'] or
        settings['new_buffer_size'] != current_settings['SAMPLES_PER_BUFFER'] or
        settings['new_pre_trigger_time'] != current_settings.get('PRE_TRIGGER_TIME', 0.0) or
        settings['new_pre_trigger_units'] != current_settings.get('PRE_TRIGGER_TIME_UNITS', psdk.TIME_UNIT.MS) or
        settings['new_post_trigger_time'] != current_settings.get('POST_TRIGGER_TIME', 1.0) or
        settings['new_post_trigger_units'] != current_settings.get('POST_TRIGGER_TIME_UNITS', psdk.TIME_UNIT.MS) or
        channel_changed  # Channel changes require restart
    )
    
    performance_changed = (
        settings['new_refresh_fps'] != current_settings['REFRESH_FPS'] or
        settings['new_poll_interval'] != current_settings['POLLING_INTERVAL']
    )
    
    time_window_changed = (settings['new_time_window'] != current_settings['TARGET_TIME_WINDOW'])
    
    trigger_changed = (
        settings['new_trigger_enabled'] != current_settings['TRIGGER_ENABLED'] or
        settings['new_trigger_threshold'] != current_settings['TRIGGER_THRESHOLD_ADC'] or
        settings['new_trigger_direction'] != current_settings.get('TRIGGER_DIRECTION', psdk.TRIGGER_DIR.RISING_OR_FALLING)
    )
    
    return settings_changed, performance_changed, time_window_changed, trigger_changed, channel_changed, siggen_changed


def validate_and_optimize_settings(settings, cached_max_memory, hw_buffer_spinbox, hardware_adc_sample_rate, scope=None):
    """
    Validate settings and auto-calculate optimal buffer sizes.
    
    Args:
        settings: Dictionary of new settings from UI
        cached_max_memory: Cached maximum available memory
        hw_buffer_spinbox: Hardware buffer spinbox widget
        hardware_adc_sample_rate: Hardware ADC sample rate (Hz) for time-to-samples conversion
        scope: PicoScope device instance (optional, used to get actual interval from device)
    
    Returns:
        tuple: (is_valid, updated_settings)
    """
    new_ratio = settings['new_ratio']
    new_buffer_size = settings['new_buffer_size']
    ratio_changed = (new_ratio != settings.get('current_ratio', new_ratio))
    buffer_size_changed = (new_buffer_size != settings.get('current_buffer_size', new_buffer_size))
    
    # Auto-calculate optimal buffer size if ratio changed
    if ratio_changed and cached_max_memory is not None:
        optimal_buffer_size = calculate_optimal_buffer_size(cached_max_memory, new_ratio)
        print(f"[VALIDATION] Ratio changed: {settings.get('current_ratio', new_ratio)} -> {new_ratio}")
        print(f"[VALIDATION] Auto-calculating optimal buffer size: {optimal_buffer_size:,} samples")
        
        # Update buffer size to optimal value
        settings['new_buffer_size'] = optimal_buffer_size
        new_buffer_size = optimal_buffer_size
        buffer_size_changed = True
        
        # Update the UI spinbox if provided
        if hw_buffer_spinbox is not None:
            hw_buffer_spinbox.setValue(optimal_buffer_size)
            print(f"[VALIDATION] Updated buffer size spinbox to {optimal_buffer_size:,} samples")
    
    # Convert trigger times to samples for validation
    # Use ACTUAL sample rate from device if available, otherwise use expected rate
    # This ensures pre-trigger samples are calculated correctly using device-returned values
    if scope is not None:
        # Get actual interval that device will achieve using wrapper function
        # Convert requested interval to seconds for get_nearest_sampling_interval()
        unit_to_seconds = TIME_UNIT_TO_SECONDS.get(settings['new_units'], 1.0)
        requested_interval_s = settings['new_interval'] * unit_to_seconds
        nearest_interval_dict = scope.get_nearest_sampling_interval(requested_interval_s)
        actual_interval_s = nearest_interval_dict['actual_sample_interval']
        
        # Calculate actual sample rate from device-returned actual interval
        actual_new_rate = 1.0 / actual_interval_s  # Rate in Hz
        print(f"[VALIDATION] Device actual interval: {actual_interval_s*1e9:.2f} ns (requested: {settings['new_interval']} {settings['new_units']})")
        print(f"[VALIDATION] Device actual rate: {actual_new_rate/1e6:.3f} MSPS")
        
        rate_to_use = actual_new_rate
    else:
        # Fallback to expected rate if scope not available
        rate_to_use = calculate_sample_rate(settings['new_interval'], settings['new_units'])
        print(f"[VALIDATION] Using expected rate (scope not available): {rate_to_use/1e6:.3f} MSPS")
    
    new_pre_trigger_samples = time_to_samples(
        settings['new_pre_trigger_time'], 
        settings['new_pre_trigger_units'], 
        rate_to_use  # Use actual device rate if available, otherwise expected rate
    )
    new_post_trigger_samples = time_to_samples(
        settings['new_post_trigger_time'], 
        settings['new_post_trigger_units'], 
        rate_to_use  # Use actual device rate if available, otherwise expected rate
    )
    
    # Validate minimum pre-trigger based on poll interval
    # Minimum pre-trigger must be at least one poll interval worth of samples
    # This ensures we capture data from before the trigger even if trigger fires right after a poll
    poll_interval_seconds = settings.get('new_poll_interval', 0.001)  # Default to 1ms if not set
    min_pre_trigger_samples = int(poll_interval_seconds * rate_to_use)
    
    if new_pre_trigger_samples < min_pre_trigger_samples:
        print(f"[VALIDATION] Pre-trigger samples ({new_pre_trigger_samples:,}) is less than minimum required ({min_pre_trigger_samples:,})")
        print(f"[VALIDATION]   Minimum based on poll interval ({poll_interval_seconds*1000:.2f} ms) and sample rate ({rate_to_use/1e6:.3f} MSPS)")
        print(f"[VALIDATION]   Auto-adjusting pre-trigger to minimum: {min_pre_trigger_samples:,} samples")
        
        # Convert minimum samples back to time for user display
        min_pre_trigger_time_seconds = min_pre_trigger_samples / rate_to_use
        # Use the same units as user's current setting for consistency
        unit_to_seconds = TIME_UNIT_TO_SECONDS.get(settings['new_pre_trigger_units'], 1.0)
        min_pre_trigger_time = min_pre_trigger_time_seconds / unit_to_seconds
        
        print(f"[VALIDATION]   Minimum pre-trigger time: {min_pre_trigger_time:.6f} {settings['new_pre_trigger_units']}")
        
        # Update to minimum
        new_pre_trigger_samples = min_pre_trigger_samples
        settings['new_pre_trigger_time'] = min_pre_trigger_time
    else:
        print(f"[VALIDATION] Pre-trigger samples ({new_pre_trigger_samples:,}) meets minimum requirement ({min_pre_trigger_samples:,})")
    
    # Store sample values for use in hardware calls
    settings['new_max_pre_trigger'] = new_pre_trigger_samples
    settings['new_max_post_trigger'] = new_post_trigger_samples
    
    # Note: update_max_post_trigger_range is now called from main file after UI widgets are available
    
    # Validate memory requirements
    memory_required = settings['new_buffer_size'] * new_ratio
    if cached_max_memory is not None:
        is_valid, _, _ = validate_buffer_size(settings['new_buffer_size'], new_ratio, cached_max_memory)
        if not is_valid:
            print(f"[VALIDATION] Buffer size validation failed: buffer={settings['new_buffer_size']:,}, ratio={new_ratio}, memory_required={memory_required:,}, max_memory={cached_max_memory:,}")
            return False, settings
        else:
            print(f"[VALIDATION] Buffer size validation passed: buffer={settings['new_buffer_size']:,}, ratio={new_ratio}, memory_required={memory_required:,}")
    else:
        print(f"[WARNING] WARNING: Cannot verify memory safety (max memory unknown)")
        print(f"  Will attempt to use {memory_required:,} samples")
    
    # Validate max post trigger samples against device memory (not buffer size)
    # Post-trigger samples can be much larger than buffer size - they're used when
    # pulling raw data after trigger, limited only by device memory
    if cached_max_memory is not None:
        # Check if post-trigger + pre-trigger samples exceed device memory
        total_trigger_samples = new_pre_trigger_samples + new_post_trigger_samples
        if total_trigger_samples > cached_max_memory:
            print(f"[WARNING] Post-trigger time may exceed device memory:")
            print(f"  Pre-trigger: {new_pre_trigger_samples:,} samples")
            print(f"  Post-trigger: {new_post_trigger_samples:,} samples")
            print(f"  Total: {total_trigger_samples:,} samples")
            print(f"  Device max memory: {cached_max_memory:,} samples")
            print(f"  [INFO] Will attempt anyway - device may handle it")
        else:
            print(f"[VALIDATION] Post-trigger samples within device memory: {total_trigger_samples:,} / {cached_max_memory:,}")
    
    return True, settings


def update_max_post_trigger_range(buffer_size, post_trigger_time_spinbox, hardware_adc_sample_rate):
    """
    Update max post trigger time range based on buffer size.
    
    Args:
        buffer_size: New buffer size to set range based on
        post_trigger_time_spinbox: Post trigger time spinbox widget to update
        hardware_adc_sample_rate: Hardware ADC sample rate (Hz)
    """
    # Calculate max time in seconds: (buffer_size - 1) / sample_rate
    max_time_seconds = (buffer_size - 1) / hardware_adc_sample_rate if hardware_adc_sample_rate > 0 else 1e6
    post_trigger_time_spinbox.setRange(0.0, max_time_seconds)
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
                     plot, plot_signal, scope=None):
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
    # Minimum for smooth plotting: MIN_RING_BUFFER_SAMPLES or actual calculation, whichever is larger
    # This prevents tiny buffers while allowing high ratios to work correctly
    MIN_RING_BUFFER_SAMPLES = 100  # Minimum ring buffer size constant
    new_ring_buffer = max(MIN_RING_BUFFER_SAMPLES, calculated_buffer)
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
            # Update the plot x-range to match new time window
            # This adjusts the number of samples across the graph based on ADC rate
            # Y-axis remains fixed (ADC counts), selection window unaffected
            plot.setXRange(0, new_time_window * hardware_adc_sample_rate, padding=0)
            print(f"[SETTINGS] X-axis range updated: 0 to {new_time_window * hardware_adc_sample_rate:.0f} samples")
            # Note: Y-axis limits are set once during initialization and don't need to be updated
            # ADC limits are hardware-dependent and don't change during runtime
            # Update display window label
            plot_signal.buffer_status_updated.emit(0, python_ring_buffer)
        else:
            print(f"[OK] Time window setting updated (buffer size unchanged)")
        
        if not settings_changed and not performance_changed:
            return True, new_ring_buffer  # Early return
    
    return False, new_ring_buffer


def apply_streaming_restart(settings, scope, buffer_0, buffer_1, data_lock, 
                           python_ring_buffer, data_array, x_data, ring_head, ring_filled,
                           hardware_adc_sample_rate, settings_update_event, 
                           efficiency_history, perf_samples_window,
                           status_displays, plot_signal, mode_combo, cached_max_memory, plot=None):
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
        settings_update_event: Settings update event (used to signal completion)
        efficiency_history: Efficiency tracking deque
        perf_samples_window: Performance tracking deque
        status_displays: Status display widgets
        plot_signal: Signal object for thread-safe communication
        mode_combo: Mode combobox for display text
        cached_max_memory: Cached maximum memory
    
    Returns:
        tuple: (success, new_hardware_adc_sample_rate, new_ring_buffer_size, 
                new_data_array, new_x_data, new_ring_head, new_ring_filled,
                new_buffer_0, new_buffer_1)
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
    # Minimum for smooth plotting: MIN_RING_BUFFER_SAMPLES or actual calculation, whichever is larger
    # This prevents tiny buffers while allowing high ratios to work correctly
    MIN_RING_BUFFER_SAMPLES = 100  # Minimum ring buffer size constant
    new_ring_buffer = max(MIN_RING_BUFFER_SAMPLES, calculated_buffer)
    
    # Check if hardware buffer size changed
    old_buffer_size = settings.get('current_buffer_size', new_buffer_size)
    buffer_size_changed = (new_buffer_size != old_buffer_size)
    
    # Check if mode changed (may require different datatype)
    current_mode = settings.get('current_mode', new_mode)
    mode_changed = (new_mode != current_mode)
    
    # Note: settings_update_in_progress flag is set by caller before this function
    print("Starting streaming restart...")
    
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
        
        # Reallocate hardware buffers if size changed OR mode changed (mode may require different datatype)
        # Note: These are returned as part of the return tuple, caller must update globals
        new_buffer_0 = buffer_0
        new_buffer_1 = buffer_1
        if buffer_size_changed or mode_changed:
            # Get correct datatype for the new mode (AVERAGE requires INT16_T, DECIMATE can use INT8_T)
            _, numpy_dtype = get_datatype_for_mode(new_mode)
            new_buffer_0 = np.zeros(new_buffer_size, dtype=numpy_dtype)
            new_buffer_1 = np.zeros(new_buffer_size, dtype=numpy_dtype)
            dtype_name = "INT16" if numpy_dtype == np.int16 else "INT8"
            print(f"[OK] Hardware buffers reallocated: {new_buffer_size:,} samples (dtype: {dtype_name})")
        
        # Reallocate ring buffer if size changed OR if settings changed (to clear old data)
        # Always reset ring buffer when restarting to ensure clean state with new settings
        python_ring_buffer = new_ring_buffer
        data_array = np.zeros(python_ring_buffer, dtype=np.float32)
        x_data = np.arange(python_ring_buffer, dtype=np.float32)
        ring_head = 0
        ring_filled = 0  # CRITICAL: Reset to 0 to clear all old data when settings change
        print(f"[OK] Ring buffer reset and reallocated: {python_ring_buffer:,} samples (time window: {new_time_window:.1f}s)")
        print(f"[OK] All old data cleared - ring_filled reset to 0 for fresh start with new settings")
        
        # Apply channel settings if changed (requires restart due to hardware limitations)
        if 'new_channel_range' in settings or 'new_channel_coupling' in settings or 'new_channel_probe_scale' in settings:
            channel_range = settings.get('new_channel_range')
            channel_coupling = settings.get('new_channel_coupling')
            channel_probe_scale = settings.get('new_channel_probe_scale')
            # Use current values from settings if new values not provided
            if channel_range is None:
                channel_range = settings.get('current_channel_range', psdk.RANGE.mV500)
            if channel_coupling is None:
                channel_coupling = settings.get('current_channel_coupling', psdk.COUPLING.AC)
            if channel_probe_scale is None:
                channel_probe_scale = settings.get('current_channel_probe_scale', 1.0)
            
            print(f"[CHANNEL] Applying channel settings during restart: range={channel_range}, coupling={channel_coupling}, probe_scale={channel_probe_scale}")
            scope.set_channel(
                channel=psdk.CHANNEL.A,
                range=channel_range,
                coupling=channel_coupling,
                probe_scale=channel_probe_scale
            )
            print("[CHANNEL] Channel settings applied successfully")
        
        # Re-register buffers with new settings
        # Get correct datatype for the mode (AVERAGE requires INT16_T, DECIMATE can use INT8_T)
        adc_data_type, _ = get_datatype_for_mode(new_mode)
        dtype_name = "INT16_T" if adc_data_type == psdk.DATA_TYPE.INT16_T else "INT8_T"
        
        # Check if datatype changed (which would mean ADC limits changed)
        current_datatype, _ = get_datatype_for_mode(current_mode)
        datatype_changed = (adc_data_type != current_datatype)
        
        # Update ADC limits and Y-axis if datatype changed (ADC limits are datatype-dependent)
        if datatype_changed:
            # Update scope's ADC limits for the new datatype (updates internal state)
            print(f"[ADC LIMITS] Datatype changed: updating ADC limits for {dtype_name}")
            min_adc, max_adc = scope.get_adc_limits(datatype=adc_data_type)
            print(f"[ADC LIMITS] Hardware returned ADC limits: {min_adc} to {max_adc} (datatype: {dtype_name})")
            
            # Update plot Y-axis to match new ADC limits (only if plot is provided)
            # Use QTimer to defer the update slightly to ensure it happens after all operations
            if plot is not None:
                if QT_AVAILABLE:
                    # Defer the Y-axis update to ensure it happens after streaming restart
                    QtCore.QTimer.singleShot(100, lambda: data_processing.update_y_axis_from_adc_limits(plot, scope, datatype=adc_data_type))
                else:
                    # Fallback if Qt is not available (shouldn't happen, but just in case)
                    data_processing.update_y_axis_from_adc_limits(plot, scope, datatype=adc_data_type)
                print(f"[ADC LIMITS] Plot Y-axis update scheduled for {dtype_name} datatype")
            else:
                print(f"[WARNING] Plot not provided - Y-axis not updated (datatype: {dtype_name})")
        
        print(f"Re-registering buffers with ratio={new_ratio}, mode={new_mode}, datatype={dtype_name}")
        register_double_buffers(scope, new_buffer_0, new_buffer_1, new_buffer_size, 
                               adc_data_type, new_mode)
        
        # Apply trigger configuration before restarting streaming
        trigger_enabled = settings.get('new_trigger_enabled', settings.get('current_trigger_enabled', False))
        trigger_threshold = settings.get('new_trigger_threshold', 50)
        apply_trigger_configuration(scope, trigger_enabled, trigger_threshold, settings.get('new_trigger_direction'))
        
        # Short delay after all buffer operations and before restarting streaming
        # This ensures clean state transition and proper hardware synchronization
        time.sleep(0.9)  # 100ms delay for optimal state transition
        
        # Restart streaming with new parameters
        print("Restarting streaming with new parameters...")
        actual_interval = start_hardware_streaming(scope, new_interval, new_units, 
                                                 new_max_pre_trigger, new_max_post_trigger,
                                                 new_ratio, new_mode, trigger_enabled)
        
        print(f"[OK] Streaming restarted successfully")
        print(f"  New ratio: {new_ratio}:1")
        print(f"  New mode: {mode_combo.currentText()}")
        print(f"  Actual interval: {actual_interval} {new_units}")
        
        # Calculate ACTUAL sample rate from device-returned interval
        # Note: Pre-trigger/post-trigger samples were already calculated using actual rate
        # during validation (via get_nearest_sampling_interval), so no recalculation needed
        new_rate = calculate_sample_rate(actual_interval, new_units)
        
        # Verify the actual rate matches what we calculated during validation
        # (should be very close since we used get_nearest_sampling_interval)
        print(f"  Hardware ADC rate: {new_rate:.2f} Hz (actual from device)")
        print(f"  Pre-trigger samples: {new_max_pre_trigger:,} (calculated using device actual rate)")
        print(f"  Post-trigger samples: {new_max_post_trigger:,} (calculated using device actual rate)")
        
        # Update global hardware ADC sample rate
        updated_settings['hardware_adc_sample_rate'] = new_rate
        
        downsampled_rate = new_rate / new_ratio
        print(f"  Downsampled rate: {downsampled_rate:.2f} Hz")
        
        # Update rate displays
        adc_msps = new_rate / 1_000_000
        downsampled_msps = adc_msps / new_ratio
        downsampled_khz = downsampled_msps * 1000  # Convert MSPS to kHz
        status_displays['adc_rate'].setText(f"{adc_msps:.3f} MSPS")
        status_displays['downsampled_rate'].setText(f"{downsampled_khz:.3f} kHz")
        
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
        
        # Note: Y-axis limits are set once during initialization and don't need to be updated
        # ADC limits are hardware-dependent and don't change during runtime
        
        return True, new_rate, new_ring_buffer, data_array, x_data, ring_head, ring_filled, new_buffer_0, new_buffer_1
        
    except Exception as e:
        print(f"[WARNING] Error updating settings: {e}")
        print(f"  Attempting to restore previous settings...")
        # Try to restore previous settings
        try:
            stop_hardware_streaming(scope)
            time.sleep(0.5)
            clear_hardware_buffers(scope)
            # Get correct datatype for the previous mode being restored
            restore_mode = settings.get('current_mode', new_mode)
            restore_datatype, _ = get_datatype_for_mode(restore_mode)
            register_double_buffers(scope, new_buffer_0, new_buffer_1, old_buffer_size, 
                                   restore_datatype, restore_mode)
            # Use current trigger state for error recovery
            recovery_trigger_enabled = settings.get('current_trigger_enabled', settings.get('new_trigger_enabled', False))
            start_hardware_streaming(scope, settings.get('current_interval', new_interval), 
                                   settings.get('current_units', new_units),
                                   settings.get('current_max_pre_trigger', new_max_pre_trigger),
                                   settings.get('current_max_post_trigger', new_max_post_trigger),
                                   settings.get('current_ratio', new_ratio),
                                   settings.get('current_mode', new_mode),
                                   recovery_trigger_enabled)
            print("[OK] Restored to previous settings")
        except Exception as restore_error:
            print(f"[WARNING] Failed to restore settings: {restore_error}")
        
        plot_signal.title_updated.emit("Error updating settings - check console")
        return False, None, None, None, None, None, None, None, None
    
    finally:
        # Signal streaming thread to resume (caller will handle this, but set event here too)
        settings_update_event.set()
        print("Streaming restart complete")


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
    
    # Re-register hardware buffers with correct datatype for the mode
    adc_data_type, _ = get_datatype_for_mode(downsampling_mode)
    dtype_name = "INT16_T" if adc_data_type == psdk.DATA_TYPE.INT16_T else "INT8_T"
    print(f"Re-registering buffers with ratio={downsampling_ratio}, mode={downsampling_mode}, datatype={dtype_name}")
    register_double_buffers(scope, buffer_0, buffer_1, len(buffer_0), 
                           adc_data_type, downsampling_mode)
    
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


# ============================================================================
# UI STATUS DISPLAY UPDATE FUNCTIONS
# ============================================================================

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


