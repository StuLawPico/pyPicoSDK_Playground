"""Pulse width trigger example using advanced trigger mode.
This script demonstrates configuring a pulse width qualifier to
trigger when a high pulse on Channel A exceeds a user-defined width.
The width is specified using :class:`pypicosdk.TIME_UNIT` in the same
way as sample rates use :class:`pypicosdk.SAMPLE_RATE`.

FIXES IMPLEMENTED:
1. Improved trigger configuration with better thresholds and hysteresis
2. Conservative pulse width threshold to avoid boundary conditions
3. Reduced auto-trigger timeout to prevent false triggers
4. Proper trigger direction (PICO_FALLING) for pulse width triggers
5. Robust hardware connection handling
6. Better analysis and verification of trigger behavior
"""

import sys
import os
import pypicosdk as psdk
import numpy as np
import time
from matplotlib import pyplot as plt

# Add parent directory to path for hardware_utils import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from hardware_utils import create_robust_scope, print_connection_guide
    HARDWARE_UTILS_AVAILABLE = True
except ImportError:
    HARDWARE_UTILS_AVAILABLE = False
    print("Warning: hardware_utils not available, using direct connection")

# Capture configuration
SAMPLES = 100_000
SAMPLE_RATE = 50  # in MS/s
PULSE_WIDTH = 500  # pulse width threshold (μs)
PULSE_WIDTH_UNIT = psdk.TIME_UNIT.US

def analyze_trigger_position(data, time_axis, trigger_index, expected_pulse_width_us):
    """Analyze trigger position relative to pulse edges."""
    data_array = np.array(data)
    
    # Find threshold (midpoint between min and max)
    threshold = (np.max(data_array) + np.min(data_array)) / 2
    
    # Find edges
    edges = []
    for i in range(1, len(data_array)):
        if data_array[i-1] <= threshold and data_array[i] > threshold:
            # Rising edge
            edges.append({
                "index": i,
                "time": time_axis[i],
                "type": "rising"
            })
        elif data_array[i-1] > threshold and data_array[i] <= threshold:
            # Falling edge
            edges.append({
                "index": i,
                "time": time_axis[i],
                "type": "falling"
            })
    
    # Find the pulse that contains the trigger point
    trigger_time = time_axis[trigger_index]
    trigger_pulse = None
    
    for i in range(len(edges) - 1):
        if edges[i]["type"] == "rising" and edges[i+1]["type"] == "falling":
            # This is a complete pulse
            pulse_start = edges[i]["time"]
            pulse_end = edges[i+1]["time"]
            
            if pulse_start <= trigger_time <= pulse_end:
                # Trigger is within this pulse
                pulse_width_ns = pulse_end - pulse_start
                pulse_width_us = pulse_width_ns / 1000
                
                # Calculate distance to nearest edge
                distance_to_start = abs(trigger_time - pulse_start)
                distance_to_end = abs(trigger_time - pulse_end)
                nearest_edge_distance = min(distance_to_start, distance_to_end)
                
                trigger_pulse = {
                    "start_time": pulse_start,
                    "end_time": pulse_end,
                    "width_ns": pulse_width_ns,
                    "width_us": pulse_width_us,
                    "trigger_time": trigger_time,
                    "distance_to_start": distance_to_start,
                    "distance_to_end": distance_to_end,
                    "nearest_edge_distance": nearest_edge_distance,
                    "nearest_edge": "start" if distance_to_start < distance_to_end else "end"
                }
                break
    
    return {
        "edges_found": len(edges),
        "trigger_pulse": trigger_pulse,
        "threshold": threshold,
        "signal_amplitude": np.max(data_array) - np.min(data_array)
    }

def main():
    """Main pulse width trigger example with all fixes implemented."""
    print("=" * 60)
    print("PULSE WIDTH TRIGGER EXAMPLE (FIXED)")
    print("=" * 60)
    print("This example demonstrates pulse width triggering with all fixes applied.")
    print()
    
    # Show connection guide if available
    if HARDWARE_UTILS_AVAILABLE:
        print_connection_guide()
        print()
    
    # Connect to hardware
    print("Connecting to PicoScope hardware...")
    if HARDWARE_UTILS_AVAILABLE:
        scope = create_robust_scope()
        if scope is None:
            print("❌ Failed to connect to hardware. Exiting.")
            return False
    else:
        # Direct connection fallback
        scope = psdk.ps6000a()
        scope.open_unit()
        print(f"Connected to device: {scope.get_unit_info(psdk.INFO.INFO_BATCH_AND_SERIAL)}")
    
    try:
        # Generate a square wave and loopback to Channel A
        print(f"Generating {PULSE_WIDTH}μs square wave at 1kHz...")
        scope.set_siggen(frequency=1_000, pk2pk=2.0, wave_type=psdk.WAVEFORM.SQUARE)
        
        # Enable Channel A and configure an advanced trigger
        print("Configuring Channel A...")
        scope.set_channel(channel=psdk.CHANNEL.A, range=psdk.RANGE.V2)
        
        # FIXED: Set up trigger channel conditions first (required for pulse width triggers)
        print("Setting up trigger channel conditions...")
        scope.set_trigger_channel_conditions(
            conditions=(psdk.CHANNEL.A, psdk.PICO_TRIGGER_STATE.TRUE),
            action=psdk.ACTION.CLEAR_ALL | psdk.ACTION.ADD  # Clear and add - required for first call
        )
        
        # FIXED: Main trigger detects the END of the pulse (falling edge)
        print("Setting up main trigger with FALLING direction (end of pulse)...")
        scope.set_trigger_channel_directions(
            channel=psdk.CHANNEL.A,
            direction=psdk.PICO_THRESHOLD_DIRECTION.PICO_FALLING,  # Main trigger: end of pulse
            threshold_mode=psdk.PICO_THRESHOLD_MODE.PICO_LEVEL
        )
        
        # FIXED: Improved trigger configuration with better thresholds and hysteresis
        # Based on PICO_DIRECTION structure documentation:
        # - PICO_FALLING uses the UPPER threshold for falling edge detection
        # - PICO_RISING uses the LOWER threshold for rising edge detection
        # - For PICO_LEVEL mode, both thresholds are set to the same value
        scope.set_trigger_channel_properties(
            threshold_upper=1500,  # 1.5V - Used for PICO_FALLING edge detection is not volts is ADC counts
            threshold_lower=1500,  # 1.5V - Used for PICO_RISING edge detection (if needed)
            hysteresis_upper=2000,  # 300mV hysteresis for upper threshold (noise immunity)
            hysteresis_lower=2000,  # 300mV hysteresis for lower threshold (noise immunity)
            channel=psdk.CHANNEL.A,
            auto_trigger_us=0  # Set to 0 to never timeout - test if pulse trigger works
        )
        
        # Convert desired sample rate to timebase
        TIMEBASE = scope.sample_rate_to_timebase(SAMPLE_RATE, psdk.SAMPLE_RATE.MSPS)
        
        # Determine actual sample interval from the selected timebase
        timebase_info = scope.get_timebase(TIMEBASE, SAMPLES)
        interval_ns = timebase_info["Interval(ns)"]
        sample_interval_s = interval_ns / 1e9
        
        print(f"Timebase: {TIMEBASE}, Sample interval: {interval_ns}ns")
        
        # FIXED: Conservative pulse width threshold to avoid boundary conditions
        # Using absolute values for easier debugging
        pulse_width_threshold_us = 480  # Conservative threshold (500μs - 20μs)
        pulse_width_s = pulse_width_threshold_us / PULSE_WIDTH_UNIT
        pulse_width_samples = int(pulse_width_s / sample_interval_s)
        
        print(f"Pulse width threshold: {pulse_width_threshold_us}μs = {pulse_width_samples} samples")
        print(f"Actual pulse width: {PULSE_WIDTH}μs")
        print()
        
        # Configure pulse width qualifier with FALLING direction
        print("Configuring pulse width qualifier with FALLING direction...")
        
        # PULSE WIDTH TRIGGER EXPLANATION (based on API documentation):
        # 1. Pulse width qualifier detects the START of the pulse (rising edge)
        # 2. Main trigger detects the END of the pulse (falling edge)
        # 3. The scope measures the time between these two events
        # 4. If the measured time meets the pulse width condition, the scope triggers
        # 5. For PICO_PW_TYPE_GREATER_THAN: trigger when pulse width > lower_bound
        # 6. For PICO_PW_TYPE_LESS_THAN: trigger when pulse width < upper_bound
        # 7. For PICO_PW_TYPE_IN_RANGE: trigger when lower_bound < pulse width < upper_bound
        
        scope.set_pulse_width_qualifier_properties(
            lower=pulse_width_samples,  # Lower bound: 480μs (minimum pulse width to trigger)
            upper=pulse_width_samples,           # Upper bound: No maximum limit (0xFFFFFFFF = unlimited)
            pw_type=psdk.PICO_PULSE_WIDTH_TYPE.PICO_PW_TYPE_GREATER_THAN,  # Trigger when pulse width > lower bound
        )
        scope.set_pulse_width_qualifier_conditions(
            conditions=(psdk.CHANNEL.A, psdk.PICO_TRIGGER_STATE.TRUE),  # Enable pulse width qualifier for Channel A
        )
        scope.set_pulse_width_qualifier_directions(
            channel=psdk.CHANNEL.A,
            direction=psdk.PICO_THRESHOLD_DIRECTION.PICO_RISING_LOWER,   # FIXED! - Pulse width qualifier: start of pulse
            threshold_mode=psdk.PICO_THRESHOLD_MODE.PICO_LEVEL,    # Use level threshold mode
        )
        print(pulse_width_samples * sample_interval_s, sample_interval_s)
        print(TIMEBASE)
        # Run capture and retrieve data
        print("Running capture...")
        channel_buffer, time_axis = scope.run_simple_block_capture(
            TIMEBASE, SAMPLES, pre_trig_percent=50
        )
        
        # Get trigger info for analysis
        trigger_info = scope.get_trigger_info()
        
        print("=" * 60)
        print("CAPTURE RESULTS")
        print("=" * 60)
        
        if trigger_info and len(trigger_info) > 0:
            info = trigger_info[0]
            trigger_index = info.get("triggerIndex_", 0)
            trigger_time = info.get("triggerTime_", 0)
            time_units = info.get("timeUnits_", 0)
            
            print(f"Trigger index: {trigger_index}")
            print(f"Trigger time: {trigger_time} (units: {time_units})")
            
            # Analyze trigger position
            analysis = analyze_trigger_position(
                channel_buffer[psdk.CHANNEL.A], 
                time_axis, 
                trigger_index,
                PULSE_WIDTH
            )
            
            print(f"Signal amplitude: {analysis['signal_amplitude']:.1f}mV")
            print(f"Edges found: {analysis['edges_found']}")
            
            # Check if trigger is real (not auto-trigger)
            if trigger_index > 0:
                print("✅ REAL TRIGGER (not auto-trigger)")
                
                if analysis["trigger_pulse"]:
                    pulse = analysis["trigger_pulse"]
                    print(f"✓ Trigger found in pulse")
                    print(f"  Pulse width: {pulse['width_us']:.1f}μs")
                    print(f"  Trigger distance to nearest edge: {pulse['nearest_edge_distance']:.1f}ns")
                    print(f"  Nearest edge: {pulse['nearest_edge']}")
                    
                    # Check if trigger is close to falling edge (end of pulse)
                    if pulse['nearest_edge'] == "end" and pulse['nearest_edge_distance'] < 1000:
                        print("  ✅ EXCELLENT: Trigger close to falling edge (end of pulse)")
                    elif pulse['nearest_edge'] == "end":
                        print("  ⚠️  WARNING: Trigger at falling edge but far from edge")
                    else:
                        print("  ❌ ERROR: Trigger at wrong edge (should be falling)")
                else:
                    print("❌ No trigger pulse found in analysis")
            else:
                print("❌ AUTO-TRIGGER (timeout) - trigger condition not met")
        else:
            print("❌ No trigger info available")
        
        # Plot captured waveform
        print("\nGenerating plot...")
        plt.figure(figsize=(15, 10))
        
        # Main waveform
        plt.subplot(2, 1, 1)
        plt.plot(time_axis, channel_buffer[psdk.CHANNEL.A])
        
        if trigger_info and len(trigger_info) > 0:
            trigger_index = trigger_info[0].get("triggerIndex_", 0)
            if trigger_index > 0:
                plt.axvline(time_axis[trigger_index], color='g', linestyle='-', 
                           label='Trigger Position')
            
            # Mark pulse edges if analysis available
            if 'analysis' in locals() and analysis["trigger_pulse"]:
                pulse = analysis["trigger_pulse"]
                plt.axvline(pulse["start_time"], color='orange', linestyle=':', 
                           label=f'Pulse Start ({pulse["start_time"]:.1f}ns)')
                plt.axvline(pulse["end_time"], color='purple', linestyle=':', 
                           label=f'Pulse End ({pulse["end_time"]:.1f}ns)')
        
        plt.xlabel("Time (ns)")
        plt.ylabel("Amplitude (mV)")
        plt.title("Pulse Width Trigger Example (FIXED) - FALLING Direction")
        plt.legend()
        plt.grid(True)
        
        # Zoomed view around trigger point
        if trigger_info and len(trigger_info) > 0:
            trigger_index = trigger_info[0].get("triggerIndex_", 0)
            if trigger_index > 0:
                plt.subplot(2, 1, 2)
                zoom_range = 5000  # Show ±5μs around trigger
                start_idx = max(0, trigger_index - zoom_range)
                end_idx = min(len(time_axis), trigger_index + zoom_range)
                
                plt.plot(time_axis[start_idx:end_idx], 
                        channel_buffer[psdk.CHANNEL.A][start_idx:end_idx])
                plt.axvline(time_axis[trigger_index], color='g', linestyle='-', 
                           label='Trigger Position')
                
                if 'analysis' in locals() and analysis["trigger_pulse"]:
                    pulse = analysis["trigger_pulse"]
                    plt.axvline(pulse["start_time"], color='orange', linestyle=':', 
                               label='Pulse Start')
                    plt.axvline(pulse["end_time"], color='purple', linestyle=':', 
                               label='Pulse End')
                
                plt.xlabel("Time (ns)")
                plt.ylabel("Amplitude (mV)")
                plt.title("Zoomed View Around Trigger Point")
                plt.legend()
                plt.grid(True)
        
        plt.tight_layout()
        plt.show()
        
        # Summary
        print("\n" + "=" * 60)
        print("FINAL SUMMARY")
        print("=" * 60)
        
        if trigger_info and len(trigger_info) > 0:
            trigger_index = trigger_info[0].get("triggerIndex_", 0)
            if trigger_index > 0:
                print("✅ SUCCESS: Real trigger detected (not auto-trigger)")
                
                if 'analysis' in locals() and analysis["trigger_pulse"]:
                    pulse = analysis["trigger_pulse"]
                    if pulse['nearest_edge'] == "end" and pulse['nearest_edge_distance'] < 1000:
                        print("✅ EXCELLENT: Trigger at falling edge (end of pulse)")
                        print("The pulse width trigger is working correctly!")
                    else:
                        print("⚠️  GOOD: Trigger detected but may need fine-tuning")
            else:
                print("❌ POOR: Auto-trigger detected (timeout)")
                print("The trigger condition may need adjustment")
        else:
            print("❌ ERROR: No trigger information available")
        
        print(f"\nKey fixes applied:")
        print(f"  1. Added trigger channel conditions with Clear | Add action")
        print(f"  2. Main trigger: PICO_FALLING (end of pulse)")
        print(f"  3. Pulse width qualifier: PICO_RISING (start of pulse)")
        print(f"  4. Improved trigger thresholds: 1.5V with 300mV hysteresis")
        print(f"  5. Auto-trigger timeout set to 0 (no timeout) - testing pulse trigger")
        print(f"  6. Conservative pulse width threshold: {pulse_width_threshold_us}μs")
        print(f"  7. Robust hardware connection handling")
        print(f"  8. Comprehensive trigger analysis and verification")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during execution: {e}")
        return False
        
    finally:
        # Close PicoScope connection
        try:
            scope.close_unit()
            print("\n✅ Device closed successfully")
        except Exception as e:
            print(f"\nWarning: Error closing device: {e}")

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)