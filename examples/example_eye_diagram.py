import pypicosdk as psdk
from matplotlib import pyplot as plt
import numpy as np

# Configuration
SAMPLE_RATE_MSPS = 250  # Desired sample rate in MS/s
SAMPLES = 1000
CAPTURES = 20
CHANNEL = psdk.CHANNEL.A
RANGE = psdk.RANGE.V1
SAMPLES_PER_SYMBOL = 50

# Initialise device
scope = psdk.ps6000a()
scope.open_unit()
TIMEBASE = scope.sample_rate_to_timebase(SAMPLE_RATE_MSPS, psdk.SAMPLE_RATE.MSPS)

# Setup channel and trigger
scope.set_channel(channel=CHANNEL, range=RANGE)
scope.set_simple_trigger(channel=CHANNEL, threshold_mv=0)

# Collect multiple captures
captures = []
for _ in range(CAPTURES):
    # Re-enable the channel in case the driver resets its state between
    # captures. This avoids "no channels or ports enabled" errors on some
    # firmware versions.
    scope.set_channel(channel=CHANNEL, range=RANGE)
    buffers, time_axis = scope.run_simple_block_capture(
        timebase=TIMEBASE,
        samples=SAMPLES,
    )
    captures.append(buffers[CHANNEL])

scope.close_unit()

# Split each capture into segments for the eye diagram
segments = []
for buf in captures:
    for idx in range(0, len(buf) - SAMPLES_PER_SYMBOL + 1, SAMPLES_PER_SYMBOL):
        segments.append(buf[idx:idx + SAMPLES_PER_SYMBOL])

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
