"""
Hardware Management Helper Functions for PicoScope Streaming Application

This module contains all hardware-related helper functions for managing
PicoScope device operations, buffer management, and hardware configuration.
"""

import time
import numpy as np
import pypicosdk as psdk

# Timing constants
BUFFER_CLEAR_DELAY_SEC = 0.1         # Delay after clearing hardware buffers
TRIGGER_CONFIG_DELAY_SEC = 0.1       # Delay after configuring trigger
STREAMING_STOP_DELAY_SEC = 0.5       # Delay after stopping streaming before clearing buffers
MIN_HARDWARE_BUFFER_SAMPLES = 1000   # Minimum hardware buffer size
TEST_TRIGGER_THRESHOLD_MV = 100      # Test threshold in mV for zero crossing trigger

# Ring buffer constants
MIN_RING_BUFFER_SAMPLES = 100        # Minimum ring buffer size for smooth plotting


# ============================================================================
# TIME UNIT CONVERSION CONSTANTS
# ============================================================================

# Conversion from time unit to multiplier for Hz calculation (1/interval)
TIME_UNIT_TO_HZ_MULTIPLIER = {
    psdk.TIME_UNIT.NS: 1e9,
    psdk.TIME_UNIT.US: 1e6,
    psdk.TIME_UNIT.MS: 1e3,
    psdk.TIME_UNIT.S: 1.0,
    psdk.TIME_UNIT.PS: 1e12
}

# Conversion from time unit to seconds (for time-to-samples conversion)
TIME_UNIT_TO_SECONDS = {
    psdk.TIME_UNIT.NS: 1e-9,
    psdk.TIME_UNIT.US: 1e-6,
    psdk.TIME_UNIT.MS: 1e-3,
    psdk.TIME_UNIT.S: 1.0,
    psdk.TIME_UNIT.PS: 1e-12
}

# Time unit display names for logging
TIME_UNIT_NAMES = {
    psdk.TIME_UNIT.NS: 'ns',
    psdk.TIME_UNIT.US: 'μs',
    psdk.TIME_UNIT.MS: 'ms',
    psdk.TIME_UNIT.S: 's',
    psdk.TIME_UNIT.PS: 'ps'
}

# Trigger direction display names for logging
TRIGGER_DIRECTION_NAMES = {
    psdk.TRIGGER_DIR.RISING: 'Rising',
    psdk.TRIGGER_DIR.FALLING: 'Falling',
    psdk.TRIGGER_DIR.RISING_OR_FALLING: 'Rising or Falling',
    psdk.TRIGGER_DIR.ABOVE: 'Above',
    psdk.TRIGGER_DIR.BELOW: 'Below'
}


# ============================================================================
# HARDWARE OPERATION FUNCTIONS
# ============================================================================

def calculate_sample_rate(interval, time_unit):
    """
    Convert sample interval and time unit to sample rate in Hz.
    
    Args:
        interval: Sample interval value
        time_unit: Time unit enum (psdk.TIME_UNIT.NS, US, MS, S, or PS)
    
    Returns:
        float: Sample rate in Hz
    """
    multiplier = TIME_UNIT_TO_HZ_MULTIPLIER.get(time_unit, 1.0)
    return multiplier / interval


def time_to_samples(time_value, time_unit, sample_rate_hz):
    """
    Convert time value and unit to number of samples based on sample rate.
    
    Args:
        time_value: Time value
        time_unit: Time unit enum (psdk.TIME_UNIT.NS, US, MS, S, or PS)
        sample_rate_hz: Sample rate in Hz
    
    Returns:
        int: Number of samples (rounded)
    """
    # Convert time to seconds first
    time_seconds = time_value * TIME_UNIT_TO_SECONDS.get(time_unit, 1.0)
    # Convert to samples
    samples = time_seconds * sample_rate_hz
    return int(round(samples))


def get_datatype_for_mode(downsampling_mode):
    """
    Get the correct ADC data type for a given downsampling mode.
    
    Args:
        downsampling_mode: Downsampling mode (psdk.RATIO_MODE.DECIMATE or psdk.RATIO_MODE.AVERAGE)
    
    Returns:
        tuple: (data_type, numpy_dtype) where:
            - data_type: psdk.DATA_TYPE constant (INT8_T or INT16_T)
            - numpy_dtype: numpy dtype (np.int8 or np.int16)
    
    Note:
        - DECIMATE mode supports INT8_T (faster, less memory)
        - AVERAGE mode requires INT16_T (hardware limitation)
    """
    if downsampling_mode == psdk.RATIO_MODE.AVERAGE:
        return psdk.DATA_TYPE.INT16_T, np.int16
    else:
        # DECIMATE and other modes can use INT8_T
        return psdk.DATA_TYPE.INT8_T, np.int8


def register_double_buffers(scope, buffer_0, buffer_1, samples_per_buffer, adc_data_type, downsampling_mode):
    """
    Register both hardware buffers (buffer_0 and buffer_1) with the scope.
    
    Args:
        scope: PicoScope device instance
        buffer_0: First hardware buffer
        buffer_1: Second hardware buffer
        samples_per_buffer: Number of samples per buffer
        adc_data_type: ADC data type (e.g., psdk.DATA_TYPE.INT8_T)
        downsampling_mode: Downsampling mode (e.g., psdk.RATIO_MODE.DECIMATE)
    """
    for buffer in [buffer_0, buffer_1]:
        scope.set_data_buffer(
            psdk.CHANNEL.A, samples_per_buffer, buffer=buffer,
            action=psdk.ACTION.ADD, datatype=adc_data_type,
            ratio_mode=downsampling_mode
        )


def start_streaming(scope, sample_interval, time_units, max_pre_trigger, 
                    max_post_trigger, trigger_enabled, ratio, ratio_mode):
    """
    Start hardware streaming with the given configuration.
    
    Consolidates the run_streaming() call pattern used throughout the codebase
    into a single function for consistency and maintainability.
    
    Args:
        scope: PicoScope device instance
        sample_interval: Sample interval value
        time_units: Time unit (e.g., psdk.TIME_UNIT.NS)
        max_pre_trigger: Maximum pre-trigger samples
        max_post_trigger: Maximum post-trigger samples
        trigger_enabled: Whether trigger is enabled (bool)
        ratio: Downsampling ratio
        ratio_mode: Downsampling mode (e.g., psdk.RATIO_MODE.DECIMATE)
        
    Returns:
        tuple: (actual_interval, sample_rate_hz)
            - actual_interval: The actual sample interval returned by hardware
            - sample_rate_hz: Calculated sample rate in Hz
    """
    actual_interval = scope.run_streaming(
        sample_interval=sample_interval,
        time_units=time_units,
        max_pre_trigger_samples=max_pre_trigger,
        max_post_trigger_samples=max_post_trigger,
        auto_stop=1 if trigger_enabled else 0,
        ratio=ratio,
        ratio_mode=ratio_mode
    )
    sample_rate = calculate_sample_rate(actual_interval, time_units)
    return actual_interval, sample_rate


def stop_hardware_streaming(scope):
    """
    Centralized hardware stopping with error handling.
    
    Args:
        scope: PicoScope device instance
        
    Returns:
        bool: True if successful, False if error occurred
    """
    try:
        scope.stop()
        print("[OK] Hardware streaming stopped")
        return True
    except Exception as e:
        print(f"[WARNING] Error stopping hardware: {e}")
        return False


def clear_hardware_buffers(scope):
    """
    Centralized buffer clearing with error handling.
    
    Args:
        scope: PicoScope device instance
        
    Returns:
        bool: True if successful, False if error occurred
    """
    try:
        scope.set_data_buffer(psdk.CHANNEL.A, 0, action=psdk.ACTION.CLEAR_ALL)
        time.sleep(BUFFER_CLEAR_DELAY_SEC)
        return True
    except Exception as e:
        print(f"[WARNING] Error clearing buffers: {e}")
        return False


def scale_adc_threshold_to_hardware(threshold_adc, is_int8_mode):
    """
    Scale user ADC threshold to hardware 16-bit ADC value.
    
    The hardware trigger always uses 16-bit ADC values internally.
    When displaying/entering values in 8-bit mode, we need to scale.
    
    Args:
        threshold_adc: User's threshold value (in display units)
        is_int8_mode: True if current mode uses INT8 display (-128 to +127),
                      False if using INT16 display (-32768 to +32767)
    
    Returns:
        int: Threshold in 16-bit ADC counts for hardware
    
    Example:
        - INT8 mode: user enters 50 → hardware gets 50 * 256 = 12,800
        - INT16 mode: user enters 12,800 → hardware gets 12,800
    """
    if is_int8_mode:
        # Scale 8-bit value to 16-bit: multiply by 256
        return int(threshold_adc * 256)
    else:
        # Already in 16-bit range, use directly
        return int(threshold_adc)


def _get_trigger_direction_name(trigger_direction):
    """
    Get human-readable name for trigger direction.
    
    Args:
        trigger_direction: TRIGGER_DIR enum value
    
    Returns:
        str: Human-readable direction name
    """
    return TRIGGER_DIRECTION_NAMES.get(trigger_direction, 'Unknown')


def _configure_trigger_enabled(scope, trigger_threshold_adc, trigger_direction, is_int8_mode=True):
    """
    Internal helper to configure enabled trigger.
    
    Args:
        scope: PicoScope device instance
        trigger_threshold_adc: Trigger threshold in user display units
                              (INT8: -128 to +127, INT16: -32768 to +32767)
        trigger_direction: Trigger direction enum
        is_int8_mode: True if current mode uses INT8 display values
    
    Returns:
        tuple: (success, hardware_threshold_adc)
    """
    direction_name = _get_trigger_direction_name(trigger_direction)
    
    # Scale threshold to 16-bit hardware ADC value
    hardware_threshold = scale_adc_threshold_to_hardware(trigger_threshold_adc, is_int8_mode)
    
    mode_str = "INT8" if is_int8_mode else "INT16"
    print(f"[CONFIG] Configuring trigger: channel=A, threshold={trigger_threshold_adc} ({mode_str}) → {hardware_threshold} (16-bit ADC), direction={direction_name}")
    
    try:
        scope.set_simple_trigger(
            channel=psdk.CHANNEL.A,
            threshold=hardware_threshold,
            threshold_unit='adc',  # Use ADC counts directly
            enable=True,
            direction=trigger_direction,
            auto_trigger=0
        )
        print(f"[OK] Trigger enabled: threshold={hardware_threshold} ADC (16-bit), direction={direction_name}")
        return True, hardware_threshold
    except Exception as e:
        print(f"[WARNING] Error configuring trigger: {e}")
        return False, hardware_threshold


def _configure_trigger_disabled(scope):
    """
    Internal helper to disable trigger.
    
    Args:
        scope: PicoScope device instance
    
    Returns:
        bool: True if successful
    """
    try:
        scope.set_simple_trigger(
            channel=psdk.CHANNEL.A,
            threshold=0,
            threshold_unit='adc',
            enable=False
        )
        print("[OK] Trigger disabled - continuous streaming mode")
        return True
    except Exception as e:
        print(f"[WARNING] Error disabling trigger: {e}")
        return False


def configure_default_trigger(scope, trigger_enabled=True, trigger_threshold_adc=0, trigger_direction=None, is_int8_mode=True):
    """
    Configure default trigger settings for the scope.
    
    Args:
        scope: PicoScope device instance
        trigger_enabled: Whether to enable trigger
        trigger_threshold_adc: Trigger threshold in user display units
        trigger_direction: Trigger direction (TRIGGER_DIR enum), defaults to RISING_OR_FALLING
        is_int8_mode: True if current mode uses INT8 display values (DECIMATE),
                      False for INT16 (AVERAGE)
        
    Returns:
        bool: True if successful, False if error occurred
    """
    if trigger_direction is None:
        trigger_direction = psdk.TRIGGER_DIR.RISING_OR_FALLING
    
    try:
        if trigger_enabled:
            success, hardware_threshold = _configure_trigger_enabled(scope, trigger_threshold_adc, trigger_direction, is_int8_mode)
            if success:
                direction_name = _get_trigger_direction_name(trigger_direction)
                mode_str = "INT8" if is_int8_mode else "INT16"
                print(f"[OK] Default trigger configured: {trigger_threshold_adc} ({mode_str}) → {hardware_threshold} ADC (16-bit), direction={direction_name}")
        else:
            success = _configure_trigger_disabled(scope)
        
        # Small delay to ensure hardware processes trigger configuration
        time.sleep(TRIGGER_CONFIG_DELAY_SEC)
        return success
        
    except Exception as e:
        print(f"[WARNING] Error configuring trigger: {e}")
        return False


def apply_trigger_configuration(scope, trigger_enabled, trigger_threshold_adc, trigger_direction=None, is_int8_mode=True):
    """
    Apply trigger configuration based on settings.
    
    Args:
        scope: PicoScope device instance
        trigger_enabled: Whether trigger is enabled
        trigger_threshold_adc: Trigger threshold in user display units
        trigger_direction: Trigger direction (TRIGGER_DIR enum), defaults to RISING_OR_FALLING
        is_int8_mode: True if current mode uses INT8 display values (DECIMATE),
                      False for INT16 (AVERAGE)
        
    Returns:
        bool: True if successful, False if error occurred
    """
    if trigger_direction is None:
        trigger_direction = psdk.TRIGGER_DIR.RISING_OR_FALLING
    
    try:
        if trigger_enabled:
            success, _ = _configure_trigger_enabled(scope, trigger_threshold_adc, trigger_direction, is_int8_mode)
            return success
        else:
            return _configure_trigger_disabled(scope)
    except Exception as e:
        print(f"[WARNING] Error applying trigger configuration: {e}")
        return False


def calculate_optimal_buffer_size(max_available_memory, downsampling_ratio, safety_margin=0.95):
    """
    Calculate optimal buffer size based on available memory and downsampling ratio.
    
    Args:
        max_available_memory: Maximum available device memory in samples
        downsampling_ratio: Downsampling ratio
        safety_margin: Safety margin as fraction (default 0.95 = 95%)
        
    Returns:
        int: Optimal buffer size in samples
    """
    # Calculate optimal buffer size with safety margin
    optimal_buffer_size = int((max_available_memory * safety_margin) / downsampling_ratio)
    optimal_buffer_size = max(MIN_HARDWARE_BUFFER_SAMPLES, optimal_buffer_size)
    
    print(f"\n[INFO] Auto-calculating optimal buffer size for ratio {downsampling_ratio}:1")
    print(f"  Max device memory: {max_available_memory:,} samples")
    print(f"  Optimal buffer: {optimal_buffer_size:,} samples ({safety_margin*100:.0f}% of max / ratio)")
    print(f"  Memory usage: {optimal_buffer_size * downsampling_ratio:,} / {max_available_memory:,} ({(optimal_buffer_size * downsampling_ratio) / max_available_memory * 100:.1f}%)")
    
    return optimal_buffer_size


def validate_buffer_size(buffer_size, downsampling_ratio, max_available_memory):
    """
    Validate that buffer size doesn't exceed device memory limits.
    
    Args:
        buffer_size: Proposed buffer size
        downsampling_ratio: Downsampling ratio
        max_available_memory: Maximum available device memory
        
    Returns:
        tuple: (is_valid, memory_required, memory_percentage)
    """
    memory_required = buffer_size * downsampling_ratio
    memory_percentage = (memory_required / max_available_memory) * 100
    
    is_valid = memory_required <= max_available_memory
    
    if is_valid:
        print(f"[OK] Memory check passed: {memory_required:,} / {max_available_memory:,} samples ({memory_percentage:.1f}%)")
    else:
        print(f"[WARNING] ERROR: Buffer size too large!")
        print(f"  Required: {memory_required:,} samples")
        print(f"  Available: {max_available_memory:,} samples")
    
    return is_valid, memory_required, memory_percentage


def calculate_pre_trigger_samples_for_raw_pull(user_pre_trigger_time, user_pre_trigger_units, 
                                               hardware_adc_sample_rate, max_post_trigger_samples,
                                               max_available_memory):
    """
    Calculate pre-trigger samples for raw data pull.
    Uses user settings if provided, otherwise auto-calculates from available memory.
    
    Args:
        user_pre_trigger_time: Pre-trigger time value from UI
        user_pre_trigger_units: Pre-trigger time units from UI
        hardware_adc_sample_rate: Hardware ADC sample rate (Hz)
        max_post_trigger_samples: Maximum post-trigger samples
        max_available_memory: Maximum available device memory
        
    Returns:
        int: Calculated pre-trigger samples
    """
    if user_pre_trigger_time > 0:
        # User has set a pre-trigger time - convert to samples
        pre_trigger_samples = time_to_samples(user_pre_trigger_time, user_pre_trigger_units, hardware_adc_sample_rate)
        print(f"[RAW SAMPLES] Using user-set pre-trigger time: {user_pre_trigger_time} {user_pre_trigger_units} = {pre_trigger_samples:,} samples")
        
        # Cap pre-trigger samples to available memory AND SDK buffer limit
        # SDK wrapper now uses c_uint64, using 4 billion as conservative limit
        MAX_SDK_BUFFER_SAMPLES = 4_000_000_000
        max_pre_trigger_memory = max_available_memory - max_post_trigger_samples
        max_pre_trigger_sdk = MAX_SDK_BUFFER_SAMPLES - max_post_trigger_samples
        max_pre_trigger = min(max_pre_trigger_memory, max_pre_trigger_sdk)
        
        if pre_trigger_samples > max_pre_trigger:
            print(f"[WARNING] Calculated pre-trigger samples ({pre_trigger_samples:,}) exceeds limits")
            if pre_trigger_samples > max_pre_trigger_memory:
                print(f"[WARNING]   Exceeds available memory limit: {max_pre_trigger_memory:,} (total: {max_available_memory:,} - post: {max_post_trigger_samples:,})")
            if pre_trigger_samples > max_pre_trigger_sdk:
                print(f"[WARNING]   Exceeds SDK buffer limit: {max_pre_trigger_sdk:,} (SDK max: {MAX_SDK_BUFFER_SAMPLES:,} - post: {max_post_trigger_samples:,})")
            pre_trigger_samples = max(0, max_pre_trigger)
            print(f"[RAW SAMPLES] Capped pre-trigger samples to {pre_trigger_samples:,}")
    else:
        # Auto-calculate: max_available_memory - MAX_POST_TRIGGER_SAMPLES
        calculated_pre_trigger = max_available_memory - max_post_trigger_samples
        pre_trigger_samples = max(0, calculated_pre_trigger)  # Ensure non-negative
        print(f"[RAW SAMPLES] Auto-calculated pre-trigger samples: {pre_trigger_samples:,}")
        print(f"[RAW SAMPLES]   (max_available: {max_available_memory:,} - post_trigger: {max_post_trigger_samples:,})")
    
    return pre_trigger_samples


def pull_raw_samples_from_device(scope, total_raw_samples, adc_data_type):
    """
    Pull raw (non-downsampled) samples from device memory after trigger event.
    
    Args:
        scope: PicoScope device instance
        total_raw_samples: Total number of raw samples to read
        adc_data_type: ADC data type (e.g., psdk.DATA_TYPE.INT8_T)
        
    Returns:
        tuple: (raw_buffer, n_raw_samples) where raw_buffer is the data array and n_raw_samples is actual count
    """
    # Validate total_raw_samples before proceeding
    if total_raw_samples <= 0:
        error_msg = f"[ERROR] Invalid total_raw_samples: {total_raw_samples:,}. Must be > 0."
        print(error_msg)
        return None, 0
    
    # Additional safety check - SDK wrapper now uses c_uint64, but we'll keep a reasonable limit
    # Maximum value for unsigned 32-bit int is 4,294,967,295 (2^32 - 1)
    # Using 4 billion as a conservative limit (actual SDK may support uint64 = 18 quintillion)
    MAX_SDK_BUFFER_SAMPLES = 4_000_000_000  # Conservative limit (4 billion samples)
    if total_raw_samples > MAX_SDK_BUFFER_SAMPLES:
        error_msg = f"[ERROR] total_raw_samples ({total_raw_samples:,}) exceeds buffer limit ({MAX_SDK_BUFFER_SAMPLES:,})."
        print(error_msg)
        print(f"[ERROR] This is likely due to incorrect time settings. Please reduce pre/post trigger times.")
        return None, 0
    
    # Stop scope and enable trigger within pre-trigger samples
    scope.stop()
    
    # Create buffer for raw data with correct datatype
    # Determine numpy dtype from PicoSDK datatype
    if adc_data_type == psdk.DATA_TYPE.INT16_T:
        numpy_dtype = np.int16
    else:  # Default to INT8_T
        numpy_dtype = np.int8
    
    try:
        raw_buffer = np.zeros(total_raw_samples, dtype=numpy_dtype)
    except (MemoryError, ValueError) as e:
        error_msg = f"[ERROR] Failed to allocate buffer for {total_raw_samples:,} samples: {e}"
        print(error_msg)
        print(f"[ERROR] Sample count is too large. Please reduce pre/post trigger times.")
        return None, 0
    
    # Register buffer with RAW mode (no downsampling)
    print(f"[RAW SAMPLES] Registering raw data buffer ({total_raw_samples:,} samples)...")
    try:
        scope.set_data_buffer(
            psdk.CHANNEL.A,
            total_raw_samples,
            buffer=raw_buffer,
            action=psdk.ACTION.ADD,
            datatype=adc_data_type,
            ratio_mode=psdk.RATIO_MODE.RAW  # RAW mode - no downsampling
        )
    except Exception as e:
        error_msg = f"[ERROR] Failed to register data buffer: {e}"
        print(error_msg)
        print(f"[ERROR] Buffer size: {total_raw_samples:,} samples")
        print(f"[ERROR] This may indicate the sample count exceeds device capabilities.")
        print(f"[ERROR] Please reduce pre/post trigger times and try again.")
        return None, 0
    
    # Read raw data from device memory using get_values
    print(f"[RAW SAMPLES] Reading raw data from device using get_values (RAW mode)...")
    n_raw_samples = scope.get_values(
        samples=total_raw_samples,
        start_index=0,
        segment=0,
        ratio=0,  # No downsampling for raw data
        ratio_mode=psdk.RATIO_MODE.RAW  # RAW mode - no downsampling
    )
    
    if n_raw_samples == 0:
        print(f"[WARNING] No raw samples retrieved - device may have already cleared buffers")
        return None, 0
    
    print(f"[RAW SAMPLES] Retrieved {n_raw_samples:,} raw samples (requested {total_raw_samples:,})")
    
    if n_raw_samples < total_raw_samples:
        print(f"[WARNING] Only got {n_raw_samples:,} samples but requested {total_raw_samples:,}")
        print(f"[INFO] This suggests the device may have limited data available")
    
    # Extract raw data from buffer (get_values fills the buffer we registered)
    # Convert to float32 for plotting (preserves the actual ADC count values)
    raw_data = raw_buffer[:n_raw_samples].astype(np.float32)
    
    return raw_data, n_raw_samples


def get_trigger_position_from_device(scope, trigger_at_sample, downsampling_ratio):
    """
    Get trigger position in raw sample space from device.
    
    Args:
        scope: PicoScope device instance
        trigger_at_sample: Trigger position in downsampled space (fallback)
        downsampling_ratio: Downsampling ratio for fallback calculation
        
    Returns:
        int: Trigger position in raw sample space
    """
    try:
        # get_trigger_info returns a list of dictionaries, one per segment
        trigger_info_list = scope.get_trigger_info(first_segment_index=0, segment_count=1)
        if trigger_info_list and len(trigger_info_list) > 0:
            trigger_info = trigger_info_list[0]  # Get first (and only) segment
            # The trigger_info is a PICO_TRIGGER_INFO structure with triggerIndex_ field
            triggered_at_raw = trigger_info.get('triggerIndex_', 0)  # Trigger in raw sample space
            print(f"[RAW SAMPLES] Trigger info from device: {trigger_info}")
            print(f"[RAW SAMPLES] Trigger at raw sample: {triggered_at_raw:,} (from get_trigger_info)")
            return triggered_at_raw
        else:
            raise ValueError("No trigger info returned from device")
    except Exception as e:
        print(f"[WARNING] Could not get trigger info: {e}")
        # Fallback: use the trigger_at_sample from streaming (but convert to raw space)
        print(f"[RAW SAMPLES] Using fallback: trigger_at_sample from streaming")
        triggered_at_raw = trigger_at_sample * downsampling_ratio
        print(f"[RAW SAMPLES] Fallback trigger at raw sample: {triggered_at_raw:,} (calculated from downsampled)")
        return triggered_at_raw
