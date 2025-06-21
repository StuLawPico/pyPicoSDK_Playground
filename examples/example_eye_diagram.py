import pypicosdk as psdk
from matplotlib import pyplot as plt
import numpy as np

# Configuration
# Assume a 10:1 probe on an I²C bus that switches between 0 and 5 V.  With the
# probe attenuation the scope sees a 0–0.5 V signal, so a ±500 mV range is
# suitable.
SAMPLE_RATE_MSPS = 40  # ADC sample rate in mega-samples per second
BIT_RATE_MBPS = 0.4   # Serial bit rate (400 kbps)
SAMPLES = 1000        # Samples captured in each block
CAPTURES = 20         # Blocks overlaid in the eye diagram
CHANNEL = psdk.CHANNEL.A
RANGE = psdk.RANGE.mV500

# Derived value: number of ADC samples representing one bit/symbol.  With the
# default values above this is 100 samples per I²C bit.
SAMPLES_PER_SYMBOL = int(SAMPLE_RATE_MSPS / BIT_RATE_MBPS)

# Initialise device
scope = psdk.ps6000a()
scope.open_unit()

# Configure channels before calculating the timebase. The SDK requires at least
# one channel to be enabled for ``sample_rate_to_timebase`` to succeed.
scope.set_channel(channel=psdk.CHANNEL.A, coupling=psdk.COUPLING.DC, range=RANGE)
scope.set_channel(channel=psdk.CHANNEL.B, enabled=0, range=RANGE)
scope.set_channel(channel=psdk.CHANNEL.C, enabled=0, range=RANGE)
scope.set_channel(channel=psdk.CHANNEL.D, enabled=0, range=RANGE)

# Convert the desired sample rate into a driver-specific timebase value.
TIMEBASE = scope.sample_rate_to_timebase(SAMPLE_RATE_MSPS, psdk.SAMPLE_RATE.MSPS)

# Setup trigger.  250 mV at the scope corresponds to a mid-level threshold on a
# 0–5 V I²C bus when using a 10:1 probe.
scope.set_simple_trigger(
    channel=CHANNEL,
    threshold_mv=250,
    direction=psdk.TRIGGER_DIR.RISING_OR_FALLING,
    auto_trigger_ms=0,
)

# Collect multiple captures
captures = []
for _ in range(CAPTURES):
    # Re-enable the channel in case the driver resets its state between
    # captures. This avoids "no channels or ports enabled" errors on some
    # firmware versions.
    scope.set_channel(channel=CHANNEL, coupling=psdk.COUPLING.DC, range=RANGE)
    buffers, time_axis = scope.run_simple_block_capture(
        timebase=TIMEBASE,
        samples=SAMPLES,
    )
    captures.append(buffers[CHANNEL])

scope.close_unit()

# Split each capture into symbol-sized segments for the eye diagram. Each
# segment spans one bit and contains ``SAMPLES_PER_SYMBOL`` ADC samples.
segments = []
for buf in captures:
    for idx in range(0, len(buf) - SAMPLES_PER_SYMBOL + 1, SAMPLES_PER_SYMBOL):
        segments.append(buf[idx:idx + SAMPLES_PER_SYMBOL])

# Time axis corresponding to the samples in a single symbol.
segment_time = np.array(time_axis[:SAMPLES_PER_SYMBOL])
segments_np = np.array(segments)

# Flatten arrays for 2D histogram
times = np.tile(segment_time, len(segments_np))
values = segments_np.flatten()

hist, x_edges, y_edges = np.histogram2d(
    times,
    values,
    bins=[SAMPLES_PER_SYMBOL, 200],
)

extent = [x_edges[0], x_edges[-1], y_edges[0], y_edges[-1]]

plt.imshow(
    hist.T,
    extent=extent,
    origin="lower",
    aspect="auto",
    cmap="inferno",
)
plt.xlabel("Time (ns)")
plt.ylabel("Amplitude (mV)")
plt.title("Eye Diagram")
plt.colorbar(label="Count")
plt.show()
