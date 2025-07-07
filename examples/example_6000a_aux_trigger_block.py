import pypicosdk as psdk
from matplotlib import pyplot as plt

# Pico examples use inline argument values for clarity

# Capture configuration
SAMPLES = 50_000

# Initialise PicoScope 6000
scope = psdk.ps6000a()
scope.open_unit()

# Configure AUX IO connector for triggering
scope.set_aux_io_mode(psdk.AUXIO_MODE.INPUT)

# Enable Channel A (inline arguments)
scope.set_channel(channel=psdk.CHANNEL.A, range=psdk.RANGE.V1)

# Trigger when AUX input is asserted using advanced trigger APIs
scope.set_trigger_channel_conditions(
    psdk.CHANNEL.TRIGGER_AUX, psdk.PICO_TRIGGER_STATE.TRUE
)
scope.set_trigger_channel_directions(
    channel=psdk.CHANNEL.TRIGGER_AUX,
    direction=psdk.PICO_THRESHOLD_DIRECTION.PICO_RISING,
    threshold_mode=psdk.PICO_THRESHOLD_MODE.PICO_LEVEL,
)
scope.set_trigger_channel_properties(0, 0, 0, 0, psdk.CHANNEL.TRIGGER_AUX)

# Preferred: convert sample rate to timebase
TIMEBASE = scope.sample_rate_to_timebase(50, psdk.SAMPLE_RATE.MSPS)
# TIMEBASE = 2  # direct driver timebase
# TIMEBASE = scope.interval_to_timebase(20E-9)

# Run the block capture
channel_buffer, time_axis = scope.run_simple_block_capture(TIMEBASE, SAMPLES)

# Finish with PicoScope
scope.close_unit()

# Plot data
plt.plot(time_axis, channel_buffer[psdk.CHANNEL.A], label="Channel A")
plt.xlabel("Time (ns)")
plt.ylabel("Amplitude (mV)")
plt.legend()
plt.grid(True)
plt.show()
