import pypicosdk as psdk
from matplotlib import pyplot as plt

# Configuration
TIMEBASE = 2
SAMPLES = 1000
CAPTURES = 20
CHANNEL = psdk.CHANNEL.A
RANGE = psdk.RANGE.V1
SAMPLES_PER_SYMBOL = 50

# Initialise device
scope = psdk.ps6000a()
scope.open_unit()

# Setup channel and trigger
scope.set_channel(channel=CHANNEL, range=RANGE)
scope.set_simple_trigger(channel=CHANNEL, threshold_mv=0)

# Collect multiple captures
captures = []
for _ in range(CAPTURES):
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

# Plot overlay of segments
segment_time = time_axis[:SAMPLES_PER_SYMBOL]
for seg in segments:
    plt.plot(segment_time, seg, color="C0", alpha=0.2)

plt.xlabel("Time (ns)")
plt.ylabel("Amplitude (mV)")
plt.title("Eye Diagram")
plt.grid(True)
plt.show()
