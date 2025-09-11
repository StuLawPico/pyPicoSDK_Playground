"""
Arbitrary waveform example for a PicoScope 6000E device

Description:
  Generates a custom waveform using the arbitrary waveform generator (AWG)
  and captures the resulting signal.

Requirements:
- PicoScope 6000E
- Python packages:
  (pip install) matplotlib numpy pypicosdk

Setup:
  - Connect the AWG output to Channel A

Notes:
  - The maximum ADC limits of the AWG are -32767 and +32767 (signed int16)
"""

import pypicosdk as psdk
from matplotlib import pyplot as plt
import numpy as np

# Open PicoScope
scope = psdk.ps6000a()
scope.open_unit()
scope.set_channel(channel=psdk.CHANNEL.A, range=psdk.RANGE.V1)
scope.set_simple_trigger(channel=psdk.CHANNEL.A)


# Create sine wave at maximum ADC limits (int16 / 2 = 32767)
# Rounded the array as data is in ADC counts, not floats
x = np.linspace(0, 2 * np.pi, 1000)
numpy_sine_wave = np.round(np.sin(x) * (32767)).astype(int)

# Create sweeping sine waveform
scope.set_siggen_awg(
    frequency=1000, # 1000 Hz
    pk2pk=0.8,  # 0.8 Vpk2pk
    buffer=numpy_sine_wave 
)

# Get timebase from sample rate
TIMEBASE = scope.sample_rate_to_timebase(sample_rate=20, unit=psdk.SAMPLE_RATE.MSPS)

# Run the block capture
channel_buffer, time_axis = scope.run_simple_block_capture(TIMEBASE, 50_000)

# Close Device
scope.close_unit()

# Plot data to pyplot
plt.plot(time_axis, channel_buffer[psdk.CHANNEL.A])
# Add labels to pyplot
plt.xlabel("Time (ns)")     
plt.ylabel("Amplitude (mV)")
plt.grid(True)
plt.show()
