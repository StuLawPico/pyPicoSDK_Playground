"""Simple frequency measurement using FFT on a block capture.

This script performs a block capture and estimates the dominant frequency
by finding the highest peak in the magnitude spectrum.
"""

import numpy as np
import pypicosdk as psdk
from matplotlib import pyplot as plt
from scipy.fft import rfft, rfftfreq
from scipy.signal import windows

# Capture configuration
SAMPLES = 5_000
SAMPLE_RATE = 500  # in MS/s
CHANNEL = psdk.CHANNEL.A
RANGE = psdk.RANGE.V1
THRESHOLD = 0


def measure_frequency_fft(data: np.ndarray, sample_rate: float) -> float:
    """Return the dominant frequency of ``data`` using FFT.

    Args:
        data: Waveform array in mV.
        sample_rate: Sample rate in samples per second.

    Returns:
        Estimated frequency in Hz.
    """
    window = windows.hann(len(data))
    windowed = data * window

    amplitudes = np.abs(rfft(windowed))
    freqs = rfftfreq(len(windowed), 1 / sample_rate)

    peak_index = np.argmax(amplitudes[1:]) + 1  # ignore DC component
    return float(freqs[peak_index])


# Initialize PicoScope 6000
scope = psdk.ps6000a()
scope.open_unit()

# Setup channel and trigger
scope.set_channel(channel=CHANNEL, range=RANGE)
scope.set_simple_trigger(channel=CHANNEL, threshold_mv=THRESHOLD)

scope.set_siggen(1E6, 1.0, psdk.WAVEFORM.SINE)

# Convert sample rate to timebase
TIMEBASE = scope.sample_rate_to_timebase(SAMPLE_RATE, psdk.SAMPLE_RATE.MSPS)

# Run block capture
channels_buffer, time_axis = scope.run_simple_block_capture(TIMEBASE, SAMPLES)

# Close connection to PicoScope
scope.close_unit()

# Extract waveform and measure frequency
waveform = channels_buffer[CHANNEL]

freq_value = measure_frequency_fft(waveform, SAMPLE_RATE * 1e6)

print(f"Measured frequency: {freq_value/1e6:.2f} MHz")

# Display waveform
plt.plot(time_axis, waveform)
plt.xlabel("Time (ns)")
plt.ylabel("Amplitude (mV)")
plt.grid(True)
plt.title("Captured Waveform")
plt.show()
