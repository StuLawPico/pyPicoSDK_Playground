import numpy as np
import pypicosdk as psdk
from matplotlib import pyplot as plt


def max_value(data: np.ndarray) -> float:
    """Return the maximum value in ``data``."""
    return np.max(data)


def min_value(data: np.ndarray) -> float:
    """Return the minimum value in ``data``."""
    return np.min(data)


def top(data: np.ndarray, bins: int = 32) -> float:
    """Return a filtered top value using a histogram mode bin.

    Args:
        data: Array of values in mV.
        bins: Number of histogram bins.

    Returns:
        Averaged value of the most populated upper bin.
    """
    data = np.sort(data)
    data = data[int(len(data) * 0.6) :]
    counts, bin_edges = np.histogram(data, bins=bins)
    mode_bin_index = np.argmax(counts)
    lbe = bin_edges[mode_bin_index]
    upe = bin_edges[mode_bin_index + 1]
    filtered = data[(data >= lbe) & (data <= upe)]
    return filtered.mean()


def base(data: np.ndarray, bins: int = 32) -> float:
    """Return a filtered base value using a histogram mode bin.

    Args:
        data: Array of values in mV.
        bins: Number of histogram bins.

    Returns:
        Averaged value of the most populated lower bin.
    """
    data = np.sort(data)
    data = data[: int(len(data) * 0.4)]
    counts, bin_edges = np.histogram(data, bins=bins)
    mode_bin_index = np.argmax(counts)
    lbe = bin_edges[mode_bin_index]
    upe = bin_edges[mode_bin_index + 1]
    filtered = data[(data >= lbe) & (data <= upe)]
    return filtered.mean()


def positive_overshoot_filtered(data: np.ndarray, bins: int = 32) -> float:
    """Return the positive overshoot of ``data``.

    Args:
        data: Array of values in mV.
        bins: Number of histogram bins.

    Returns:
        Difference between the maximum value and the filtered top level.
    """
    return max_value(data) - top(data, bins)


def negative_overshoot_filtered(data: np.ndarray, bins: int = 32) -> float:
    """Return the negative overshoot of ``data``.

    Args:
        data: Array of values in mV.
        bins: Number of histogram bins.

    Returns:
        Difference between the filtered base level and the minimum value.
    """
    return base(data, bins) - min_value(data)


# Example configuration
SAMPLES = 5_000
BINS = 32
SIGGEN_FREQUENCY = 1_000_000
SIGGEN_PK2PK = 0.8


scope = psdk.ps6000a()
scope.open_unit()

scope.set_siggen(
    frequency=SIGGEN_FREQUENCY,
    pk2pk=SIGGEN_PK2PK,
    wave_type=psdk.WAVEFORM.SQUARE,
)
scope.set_channel(channel=psdk.CHANNEL.A, range=psdk.RANGE.V1)
scope.set_simple_trigger(channel=psdk.CHANNEL.A, threshold_mv=0)

TIMEBASE = scope.sample_rate_to_timebase(sample_rate=500, unit=psdk.SAMPLE_RATE.MSPS)

channel_buffer, time_axis = scope.run_simple_block_capture(timebase=TIMEBASE, samples=SAMPLES)

scope.close_unit()

waveform = channel_buffer[psdk.CHANNEL.A]

pos_over = positive_overshoot_filtered(waveform, bins=BINS)
neg_over = negative_overshoot_filtered(waveform, bins=BINS)

print(f"Positive overshoot: {pos_over:.2f} mV")
print(f"Negative overshoot: {neg_over:.2f} mV")

plt.plot(time_axis, waveform)
plt.xlabel("Time (ns)")
plt.ylabel("Amplitude (mV)")
plt.grid(True)
plt.show()
