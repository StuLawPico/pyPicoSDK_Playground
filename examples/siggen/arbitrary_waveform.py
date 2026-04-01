"""
Copyright (C) 2025-2025 Pico Technology Ltd. See LICENSE file for terms.

This example uses the Arbitrary Waveform Generator to output a custom waveform
loaded from a CSV file containing voltage samples (one value per line).

The CSV voltage data is normalised to the full AWG ADC range (-32767 to +32767)
and the pk2pk parameter is set to match the original voltage swing.

Setup:
1. Connect the AWG SigGen port on the scope to channel A.
2. Update CSV_PATH to point to your waveform CSV file.
3. Run the example.

Notes:
- The maximum ADC limits of the AWG are -32767 and +32767 (signed int 16)
- CSV should contain one voltage value per line (no header)
"""

import numpy as np
from matplotlib import pyplot as plt
import pypicosdk as psdk

# ── CSV Waveform Configuration ──────────────────────────────────────────────
CSV_PATH = r"C:\Users\stuart.law\Desktop\PS Data Files\Customer\ST\fast_ps7_pulse_5ns_rt.csv"
AWG_FREQUENCY = 1000       # Output repetition rate in Hz
SAMPLE_RATE = 20           # Capture sample rate in MSPS
NUM_SAMPLES = 50_000       # Number of samples to capture

# ── Load and convert CSV to AWG buffer ──────────────────────────────────────
csv_voltages = np.loadtxt(CSV_PATH)

v_min = csv_voltages.min()
v_max = csv_voltages.max()
pk2pk_volts = v_max - v_min
offset_volts = (v_max + v_min) / 2.0

# Normalise to full int16 ADC range: -32767 to +32767
awg_buffer = np.round(((csv_voltages - offset_volts) / (pk2pk_volts / 2.0)) * 32767).astype(np.int16)

print(f"Loaded {len(awg_buffer)} samples from CSV")
print(f"  Voltage range : {v_min:.4f} V  to  {v_max:.4f} V")
print(f"  Pk-Pk         : {pk2pk_volts:.4f} V")
print(f"  Offset        : {offset_volts:.4f} V")
print(f"  AWG buffer    : {awg_buffer.min()} to {awg_buffer.max()} ADC counts")

# Preview the AWG buffer before sending to hardware
fig_preview, (ax_orig, ax_adc) = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
sample_indices = np.arange(len(csv_voltages))

ax_orig.plot(sample_indices, csv_voltages, linewidth=0.5)
ax_orig.set_ylabel("Voltage (V)")
ax_orig.set_title("Original CSV Waveform")
ax_orig.grid(True)

ax_adc.plot(sample_indices, awg_buffer, linewidth=0.5, color="tab:orange")
ax_adc.set_ylabel("ADC Counts")
ax_adc.set_xlabel("Sample Index")
ax_adc.set_title("Normalised AWG Buffer (int16)")
ax_adc.grid(True)

fig_preview.tight_layout()
plt.show(block=False)
plt.pause(0.5)

# ── PicoScope Setup ─────────────────────────────────────────────────────────
scope = psdk.psospa()
scope.open_unit()
scope.set_channel(channel=psdk.CHANNEL.A, range=psdk.RANGE.V1)
scope.set_simple_trigger(channel=psdk.CHANNEL.A)

# Output the loaded waveform via the AWG
scope.set_siggen_awg(
    frequency=AWG_FREQUENCY,
    pk2pk=pk2pk_volts,
    offset=offset_volts,
    buffer=awg_buffer
)

# Get timebase from sample rate
TIMEBASE = scope.sample_rate_to_timebase(sample_rate=SAMPLE_RATE, unit=psdk.SAMPLE_RATE.MSPS)

# Run the block capture
channel_buffer, time_axis = scope.run_simple_block_capture(TIMEBASE, NUM_SAMPLES)

# Close Device
scope.close_unit()

# Plot captured data
plt.figure(figsize=(10, 4))
plt.plot(time_axis, channel_buffer[psdk.CHANNEL.A])
plt.xlabel("Time (ns)")
plt.ylabel("Amplitude (mV)")
plt.title("Captured AWG Output")
plt.grid(True)
plt.show()
