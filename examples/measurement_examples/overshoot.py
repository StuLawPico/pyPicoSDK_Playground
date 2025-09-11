"""
Overshoot measurement example for a PicoScope 6000E device

Description:
  Uses histogram-based top and base functions to calculate positive and
  negative overshoot of a waveform.

Requirements:
- PicoScope 6000E
- Python packages:
  (pip install) matplotlib pypicosdk

Setup:
  - Connect Channel A to the AWG output
"""
from measurements import positive_overshoot_filtered, negative_overshoot_filtered

from matplotlib import pyplot as plt
import pypicosdk as psdk


# Capture configuration
SAMPLES = 5_000
SAMPLE_RATE = 500  # in MS/s
CHANNEL = psdk.CHANNEL.A
RANGE = psdk.RANGE.V1
BINS = 32
THRESHOLD = 0

# Initialize PicoScope 6000
scope = psdk.ps6000a()
scope.open_unit()

# Setup channel and trigger
scope.set_channel(channel=CHANNEL, range=RANGE)
scope.set_simple_trigger(channel=CHANNEL, threshold_mv=THRESHOLD)

scope.set_siggen(1E6, 1.6, psdk.WAVEFORM.SQUARE)

# Convert sample rate to timebase
TIMEBASE = scope.sample_rate_to_timebase(SAMPLE_RATE, psdk.SAMPLE_RATE.MSPS)

# Run block capture
channels_buffer, time_axis = scope.run_simple_block_capture(TIMEBASE, SAMPLES)

# Close connection to PicoScope
scope.close_unit()

# Extract waveform and measure amplitude
waveform = channels_buffer[CHANNEL]

pos_over = positive_overshoot_filtered(waveform)
neg_over = negative_overshoot_filtered(waveform)

print(f"Positive overshoot: {pos_over:.2f} %")
print(f"Negative overshoot: {neg_over:.2f} %")

# Display waveform
plt.plot(time_axis, waveform)
plt.xlabel("Time (ns)")
plt.ylabel("Amplitude (mV)")
plt.grid(True)
plt.title("Captured Waveform")
plt.show()
