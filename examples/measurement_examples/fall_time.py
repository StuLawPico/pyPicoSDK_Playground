"""
Fall time measurement example for a PicoScope 6000E device

Description:
  Captures PicoScope data, measures fall time, and plots the waveform.

Requirements:
- PicoScope 6000E
- Python packages:
  (pip install) matplotlib pypicosdk

Setup:
  - Connect Channel A to the AWG output
"""
from measurements import fall_time

from matplotlib import pyplot as plt
import pypicosdk as psdk

# Capture configuration
SAMPLES = 5_000

# Initialise PicoScope 6000
scope = psdk.ps6000a()
scope.open_unit()

# Setup siggen
scope.set_siggen(frequency=1_000_000, pk2pk=0.8, wave_type=psdk.WAVEFORM.SQUARE)

# Setup channels and trigger (inline arguments)
scope.set_channel(channel=psdk.CHANNEL.A, range=psdk.RANGE.V1)
scope.set_simple_trigger(channel=psdk.CHANNEL.A, threshold_mv=0)

# Preferred: convert sample rate to timebase
TIMEBASE = scope.sample_rate_to_timebase(sample_rate=500, unit=psdk.SAMPLE_RATE.MSPS)

# Run the block capture
channel_buffer, time_axis = scope.run_simple_block_capture(TIMEBASE, SAMPLES)

# Finish with PicoScope
scope.close_unit()

fall_time_value = fall_time(channel_buffer[psdk.CHANNEL.A], time_axis)
print(f'fall time(ns): {fall_time_value}')

# Plot data to pyplot
plt.plot(time_axis, channel_buffer[psdk.CHANNEL.A])

# Add labels to pyplot
plt.xlabel("Time (ns)")
plt.ylabel("Amplitude (mV)")
plt.grid(True)
plt.show()
