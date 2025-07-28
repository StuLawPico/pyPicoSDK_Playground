"""Simple amplitude measurement using a block capture.
Uses histogram-based top and base functions to provide a robust amplitude
measurement. The script can also calculate RMS amplitude.
"""
import numpy as np
import pypicosdk as psdk
from matplotlib import pyplot as plt


# Capture configuration
SAMPLES = 5_000
SAMPLE_RATE = 500  # in MS/s
CHANNEL = psdk.CHANNEL.A
RANGE = psdk.RANGE.V1
BINS = 32
THRESHOLD = 0


def top(data):
    """Return the average of the upper mode of ``data``."""

    data = np.sort(data)
    data = data[int(len(data) * 0.6) :]

    counts, bin_edges = np.histogram(data, bins=BINS)
    mode_bin_index = np.argmax(counts)

    lbe = bin_edges[mode_bin_index]
    upe = bin_edges[mode_bin_index + 1]

    filtered = data[(data >= lbe) & (data <= upe)]
    return float(filtered.mean())

def base(data):
    """Return the average of the lower mode of ``data``."""

    data = np.sort(data)
    data = data[: int(len(data) * 0.4)]

    counts, bin_edges = np.histogram(data, bins=BINS)
    mode_bin_index = np.argmax(counts)

    lbe = bin_edges[mode_bin_index]
    upe = bin_edges[mode_bin_index + 1]

    filtered = data[(data >= lbe) & (data <= upe)]
    return float(filtered.mean())

def max_value(data):
    return np.max(data)

def min_value(data):
    return np.min(data)

def pk2pk(data):
    return float(max(waveform) - min(waveform))

def amplitude(data):
    return float(top(waveform) - base(waveform)) / 2

def rms(data):
    return float(np.sqrt(np.mean(np.square(waveform - waveform.mean()))))

# Initialize PicoScope 6000
scope = psdk.ps6000a()
scope.open_unit()

# Setup channel and trigger
scope.set_channel(channel=CHANNEL, range=RANGE)
scope.set_simple_trigger(channel=CHANNEL, threshold_mv=THRESHOLD)

scope.set_siggen(1E6, 1.6, psdk.WAVEFORM.SINE, offset=0.1)

# Convert sample rate to timebase
TIMEBASE = scope.sample_rate_to_timebase(SAMPLE_RATE, psdk.SAMPLE_RATE.MSPS)

# Run block capture
channels_buffer, time_axis = scope.run_simple_block_capture(TIMEBASE, SAMPLES)

# Close connection to PicoScope
scope.close_unit()

# Extract waveform and measure amplitude
waveform = (channels_buffer[CHANNEL])

amplitude_value = amplitude(waveform)
pk2pk_value = pk2pk(waveform)
rms_value = rms(waveform)

print(f"Measured amplitude: {amplitude_value:.2f} mV, pk2pk: {pk2pk_value:.2f} mV, RMS: {rms_value:.2f} mV")

# Display waveform
plt.plot(time_axis, waveform)
plt.xlabel("Time (ns)")
plt.ylabel("Amplitude (mV)")
plt.grid(True)
plt.title("Captured Waveform")
plt.show()
