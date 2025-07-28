"""Measure rise time and fall time of a captured waveform.

This script performs a simple block capture and calculates the rise and
fall time between the 10% and 90% amplitude levels of the signal.
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


def top(data: np.ndarray) -> float:
    """Return the average of the upper mode of ``data``."""
    data = np.sort(data)
    data = data[int(len(data) * 0.6) :]

    counts, bin_edges = np.histogram(data, bins=BINS)
    mode_bin_index = np.argmax(counts)

    lbe = bin_edges[mode_bin_index]
    upe = bin_edges[mode_bin_index + 1]

    filtered = data[(data >= lbe) & (data <= upe)]
    return float(filtered.mean())


def base(data: np.ndarray) -> float:
    """Return the average of the lower mode of ``data``."""
    data = np.sort(data)
    data = data[: int(len(data) * 0.4)]

    counts, bin_edges = np.histogram(data, bins=BINS)
    mode_bin_index = np.argmax(counts)

    lbe = bin_edges[mode_bin_index]
    upe = bin_edges[mode_bin_index + 1]

    filtered = data[(data >= lbe) & (data <= upe)]
    return float(filtered.mean())


def rise_time(times: np.ndarray, data: np.ndarray) -> float:
    """Return rise time between 10% and 90% levels."""
    hi = top(data)
    lo = base(data)
    low_level = lo + 0.1 * (hi - lo)
    high_level = lo + 0.9 * (hi - lo)

    start = np.argmax(data > low_level)
    end_candidates = np.where(data >= high_level)[0]
    end_candidates = end_candidates[end_candidates >= start]
    end = end_candidates[0] if end_candidates.size > 0 else start
    return float(times[end] - times[start])


def fall_time(times: np.ndarray, data: np.ndarray) -> float:
    """Return fall time between 90% and 10% levels."""
    hi = top(data)
    lo = base(data)
    high_level = lo + 0.9 * (hi - lo)
    low_level = lo + 0.1 * (hi - lo)

    start = np.argmax(data < high_level)
    end_candidates = np.where(data <= low_level)[0]
    end_candidates = end_candidates[end_candidates >= start]
    end = end_candidates[0] if end_candidates.size > 0 else start
    return float(times[end] - times[start])


# Initialize PicoScope 6000
scope = psdk.ps6000a()
scope.open_unit()

# Setup channel and trigger
scope.set_channel(channel=CHANNEL, range=RANGE)
scope.set_simple_trigger(channel=CHANNEL, threshold_mv=THRESHOLD)

scope.set_siggen(1e6, 1.6, psdk.WAVEFORM.SQUARE, offset=0.0)

# Convert sample rate to timebase
TIMEBASE = scope.sample_rate_to_timebase(SAMPLE_RATE, psdk.SAMPLE_RATE.MSPS)

# Run block capture
channels_buffer, time_axis = scope.run_simple_block_capture(TIMEBASE, SAMPLES)

# Close connection to PicoScope
scope.close_unit()

# Extract waveform and measure rise/fall time
waveform = channels_buffer[CHANNEL]

rise = rise_time(time_axis, waveform)
fall = fall_time(time_axis, waveform)

print(f"Measured rise time: {rise:.2f} ns, fall time: {fall:.2f} ns")

# Display waveform
plt.plot(time_axis, waveform)
plt.xlabel("Time (ns)")
plt.ylabel("Amplitude (mV)")
plt.grid(True)
plt.title("Captured Waveform")
plt.show()
