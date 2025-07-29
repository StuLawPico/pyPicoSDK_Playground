"""Pulse width trigger example.

This script demonstrates configuring a pulse width qualifier to
trigger when a high pulse on Channel A exceeds a user-defined width.
The width is specified using :class:`pypicosdk.TIME_UNIT` in the same
way as sample rates use :class:`pypicosdk.SAMPLE_RATE`.
"""

import pypicosdk as psdk
from matplotlib import pyplot as plt

# Capture configuration
SAMPLES = 100_000
SAMPLE_RATE = 50  # in MS/s
PULSE_WIDTH = 500  # pulse width threshold
PULSE_WIDTH_UNIT = psdk.TIME_UNIT.US

# Initialize PicoScope 6000
scope = psdk.ps6000a()
scope.open_unit()

# Generate a square wave and loopback to Channel A
scope.set_siggen(frequency=1_000, pk2pk=2.0, wave_type=psdk.WAVEFORM.SQUARE)

# Enable Channel A and simple trigger
scope.set_channel(channel=psdk.CHANNEL.A, range=psdk.RANGE.V2)
scope.set_simple_trigger(channel=psdk.CHANNEL.A, threshold_mv=0,
                         direction=psdk.TRIGGER_DIR.FALLING)

# Convert desired sample rate to timebase
TIMEBASE = scope.sample_rate_to_timebase(SAMPLE_RATE, psdk.SAMPLE_RATE.MSPS)

# Determine actual sample interval from the selected timebase
interval_ns = scope.get_timebase(TIMEBASE, SAMPLES)["Interval(ns)"]
sample_interval_s = interval_ns / 1e9

# Convert pulse width threshold to samples
pulse_width_s = PULSE_WIDTH / PULSE_WIDTH_UNIT
pulse_width_samples = int(pulse_width_s / sample_interval_s)

# Configure pulse width qualifier
scope.set_pulse_width_qualifier_properties(
    lower=pulse_width_samples,
    upper=0xFFFFFFFF,
    pw_type=psdk.PICO_PULSE_WIDTH_TYPE.PICO_PW_TYPE_GREATER_THAN,
)
scope.set_pulse_width_qualifier_conditions(
    source=psdk.CHANNEL.A,
    state=psdk.PICO_TRIGGER_STATE.TRUE,
)
scope.set_pulse_width_qualifier_directions(
    channel=psdk.CHANNEL.A,
    direction=psdk.PICO_THRESHOLD_DIRECTION.PICO_RISING,
    threshold_mode=psdk.PICO_THRESHOLD_MODE.PICO_LEVEL,
)

# Run capture and retrieve data
channel_buffer, time_axis = scope.run_simple_block_capture(TIMEBASE, SAMPLES)

# Close PicoScope connection
scope.close_unit()

# Plot captured waveform
plt.plot(time_axis, channel_buffer[psdk.CHANNEL.A])
plt.xlabel("Time (ns)")
plt.ylabel("Amplitude (mV)")
plt.grid(True)
plt.show()
