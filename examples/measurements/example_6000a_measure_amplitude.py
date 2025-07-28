"""Simple amplitude measurement using a block capture.

Uses histogram-based top and base functions to provide a robust amplitude
measurement. The script can also calculate RMS amplitude.
"""

from __future__ import annotations

import numpy as np
import pypicosdk as psdk
from matplotlib import pyplot as plt


# Capture configuration
SAMPLES = 5_000
SAMPLE_RATE = 500  # in MS/s
CHANNEL = psdk.CHANNEL.A
RANGE = psdk.RANGE.V1
MEASURE_METHOD = "pk2pk"  # "pk2pk" or "rms"
BINS = 32
THRESHOLD = 0


def top(data: np.ndarray, bins: int = BINS) -> float:
    """Return the average of the upper mode of ``data``."""

    data = np.sort(data)
    data = data[int(len(data) * 0.6) :]

    counts, bin_edges = np.histogram(data, bins=bins)
    mode_bin_index = np.argmax(counts)

    lbe = bin_edges[mode_bin_index]
    upe = bin_edges[mode_bin_index + 1]

    filtered = data[(data >= lbe) & (data <= upe)]
    return float(filtered.mean())


def base(data: np.ndarray, bins: int = BINS) -> float:
    """Return the average of the lower mode of ``data``."""

    data = np.sort(data)
    data = data[: int(len(data) * 0.4)]

    counts, bin_edges = np.histogram(data, bins=bins)
    mode_bin_index = np.argmax(counts)

    lbe = bin_edges[mode_bin_index]
    upe = bin_edges[mode_bin_index + 1]

    filtered = data[(data >= lbe) & (data <= upe)]
    return float(filtered.mean())


def measure_amplitude(
    waveform: np.ndarray, method: str = "pk2pk", bins: int = BINS
) -> float:
    """Calculate amplitude from waveform data.

    Args:
        waveform: Captured signal in millivolts.
        method: ``"pk2pk"`` for histogram-based measurement or ``"rms"`` for RMS.
        bins: Number of histogram bins for the ``"pk2pk"`` method.

    Returns:
        Calculated amplitude in millivolts.
    """
    if method == "pk2pk":
        return float(top(waveform, bins) - base(waveform, bins)) / 2
    if method == "rms":
        return float(np.sqrt(np.mean(np.square(waveform - waveform.mean()))))
    raise ValueError(f"Unknown method: {method}")


# Initialize PicoScope 6000
scope = psdk.ps6000a()
scope.open_unit()

# Setup channel and trigger
scope.set_channel(channel=CHANNEL, range=RANGE)
scope.set_simple_trigger(channel=CHANNEL, threshold_mv=THRESHOLD)

# Convert sample rate to timebase
TIMEBASE = scope.sample_rate_to_timebase(SAMPLE_RATE, psdk.SAMPLE_RATE.MSPS)

# Run block capture
buffers, time_axis = scope.run_simple_block_capture(TIMEBASE, SAMPLES)

# Close connection to PicoScope
scope.close_unit()

# Extract waveform and measure amplitude
waveform = np.array(buffers[CHANNEL])
measured_amplitude = measure_amplitude(waveform, MEASURE_METHOD)
print(f"Measured amplitude: {measured_amplitude:.2f} mV")

# Display waveform
plt.plot(time_axis, waveform)
plt.xlabel("Time (ns)")
plt.ylabel("Amplitude (mV)")
plt.grid(True)
plt.title("Captured Waveform")
plt.show()
