"""
Hardware Management Helper Functions for PicoScope Streaming Application

This module contains all hardware-related helper functions for managing
PicoScope device operations, buffer management, and hardware configuration.
"""

import time
import numpy as np
import pypicosdk as psdk


def calculate_sample_rate(interval, time_unit):
    """
    Convert sample interval and time unit to sample rate in Hz.
    
    Args:
        interval: Sample interval value
        time_unit: Time unit enum (psdk.TIME_UNIT.NS, US, MS, S, or PS)
    
    Returns:
        float: Sample rate in Hz
    """
    unit_to_multiplier = {
        psdk.TIME_UNIT.NS: 1e9,
        psdk.TIME_UNIT.US: 1e6,
        psdk.TIME_UNIT.MS: 1e3,
        psdk.TIME_UNIT.S: 1.0,
        psdk.TIME_UNIT.PS: 1e12
    }
    return unit_to_multiplier.get(time_unit, 1.0) / interval


def compute_interval_from_msps(msps: float):
    """
    Convert a desired MSPS (mega samples per second) to (sample_interval, time_units)
    for scope.run_streaming(). Prefers integer intervals in ns/us/ms.
    
    Args:
        msps: Desired mega samples per second
        
    Returns:
        tuple: (sample_interval, time_unit)
        
    Raises:
        ValueError: If msps is not positive
    """
    if msps <= 0:
        raise ValueError("MSPS must be > 0")
    
    # Desired samples per second
    sps = msps * 1_000_000.0
    
    # Try nanoseconds first
    interval_ns = int(round(1_000_000_000.0 / sps))
    if interval_ns >= 1:
        return interval_ns, psdk.TIME_UNIT.NS
    
    # Then microseconds
    interval_us = int(round(1_000_000.0 / sps))
    if interval_us >= 1:
        return interval_us, psdk.TIME_UNIT.US
    
    # Fallback to milliseconds
    interval_ms = max(1, int(round(1_000.0 / sps)))
    return interval_ms, psdk.TIME_UNIT.MS


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


def start_hardware_streaming(scope, sample_interval, time_units, max_pre_trigger_samples, 
                           max_post_trigger_samples, downsampling_ratio, downsampling_mode, 
                           trigger_enabled=True):
    """
    Start hardware streaming with specified settings.
    
    Args:
        scope: PicoScope device instance
        sample_interval: Sample interval value
        time_units: Time unit enum
        max_pre_trigger_samples: Pre-trigger samples
        max_post_trigger_samples: Post-trigger samples
        downsampling_ratio: Downsampling ratio
        downsampling_mode: Downsampling mode
        trigger_enabled: Whether trigger is enabled
        
    Returns:
        Actual sample interval achieved by the hardware
    """
    print(f"[STREAMING] Starting with trigger={'enabled' if trigger_enabled else 'disabled'}")
    print(f"[STREAMING] Max post trigger samples: {max_post_trigger_samples:,}")
    print(f"[STREAMING] Auto-stop setting: 0 (continuous streaming)")
    
    return scope.run_streaming(
        sample_interval=sample_interval,
        time_units=time_units,
        max_pre_trigger_samples=max_pre_trigger_samples,
        max_post_trigger_samples=max_post_trigger_samples,
        auto_stop=1,  # Never auto-stop (continuous streaming)
        ratio=downsampling_ratio,
        ratio_mode=downsampling_mode
    )


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
        time.sleep(0.1)
        return True
    except Exception as e:
        print(f"[WARNING] Error clearing buffers: {e}")
        return False


def configure_default_trigger(scope, trigger_enabled=True, trigger_threshold_adc=50):
    """
    Configure default trigger settings for the scope.
    
    Args:
        scope: PicoScope device instance
        trigger_enabled: Whether to enable trigger
        trigger_threshold_adc: Trigger threshold in ADC counts
        
    Returns:
        bool: True if successful, False if error occurred
    """
    try:
        if trigger_enabled:
            # Convert ADC threshold to mV for more reliable trigger
            # For 500mV range with 8-bit ADC: 1 ADC count ≈ 3.9mV
            threshold_mv = (trigger_threshold_adc * 500.0) / 128.0
            
            print(f"[CONFIG] Configuring default trigger: channel=A, threshold={trigger_threshold_adc} ADC ({threshold_mv:.1f}mV)")
            
            scope.set_simple_trigger(
                channel=psdk.CHANNEL.A,
                threshold=int(threshold_mv),
                threshold_unit='mv',  # Use mV for better reliability
                enable=True,
                direction=psdk.TRIGGER_DIR.RISING_OR_FALLING,
                auto_trigger=0
            )
            
            print(f"[OK] Default trigger configured: {trigger_threshold_adc} ADC counts ({threshold_mv:.1f}mV)")
        else:
            # Disable trigger
            scope.set_simple_trigger(
                channel=psdk.CHANNEL.A,
                threshold=0,
                threshold_unit='adc',
                enable=False
            )
            print("[OK] Trigger disabled - continuous streaming mode")
        
        # Small delay to ensure hardware processes trigger configuration
        time.sleep(0.1)
        return True
        
    except Exception as e:
        print(f"[WARNING] Error configuring trigger: {e}")
        return False


def apply_trigger_configuration(scope, trigger_enabled, trigger_threshold_adc):
    """
    Apply trigger configuration based on settings.
    
    Args:
        scope: PicoScope device instance
        trigger_enabled: Whether trigger is enabled
        trigger_threshold_adc: Trigger threshold in ADC counts
        
    Returns:
        bool: True if successful, False if error occurred
    """
    if trigger_enabled:
        try:
            # Convert ADC threshold to mV for more reliable trigger
            threshold_mv = (trigger_threshold_adc / 127) * 500  # For 500mV range, 8-bit ADC
            
            # Try a different threshold if zero crossing isn't working
            if trigger_threshold_adc == 0:
                # Try +100mV threshold (should be crossed by your +120 ADC signal)
                test_threshold_mv = 100
                print(f"[CONFIG] Configuring trigger: channel=A, threshold={test_threshold_mv}mV (test threshold, was {trigger_threshold_adc} ADC), direction=rising or falling")
                actual_threshold = test_threshold_mv
            else:
                print(f"[CONFIG] Configuring trigger: channel=A, threshold={threshold_mv:.1f}mV (was {trigger_threshold_adc} ADC), direction=rising or falling")
                actual_threshold = int(threshold_mv)
            
            # Try with mV-based trigger on both rising and falling edges
            scope.set_simple_trigger(
                channel=psdk.CHANNEL.A,
                threshold=actual_threshold,
                threshold_unit='mv',  # Use mV instead of ADC counts
                enable=True,
                direction=psdk.TRIGGER_DIR.RISING_OR_FALLING,
                auto_trigger=0
            )
            print(f"[OK] Trigger enabled: threshold={actual_threshold}mV (both directions)")
            return True
            
        except Exception as e:
            print(f"[WARNING] Error configuring trigger: {e}")
            return False
    else:
        # Disable trigger (set enable=False)
        try:
            scope.set_simple_trigger(
                channel=psdk.CHANNEL.A,
                threshold=0,
                threshold_unit='adc',
                enable=False  # Disable trigger
            )
            print("[OK] Trigger disabled - continuous streaming mode")
            return True
            
        except Exception as e:
            print(f"[WARNING] Error disabling trigger: {e}")
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
    optimal_buffer_size = max(1000, optimal_buffer_size)  # Minimum 1000 samples
    
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
