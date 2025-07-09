import time
import pypicosdk as psdk
from matplotlib import pyplot as plt

# Pico examples use inline argument values for clarity

# Streaming configuration
SAMPLES = 10_000
INTERVAL_NS = 100

# Initialise PicoScope 6000
scope = psdk.ps6000a()
scope.open_unit()

# Setup signal generator
scope.set_siggen(frequency=1_000_000, pk2pk=0.8, wave_type=psdk.WAVEFORM.SINE)

# Setup channel and trigger (inline arguments)
scope.set_channel(channel=psdk.CHANNEL.A, range=psdk.RANGE.V1)
scope.set_simple_trigger(channel=psdk.CHANNEL.A, threshold_mv=0)

# Allocate streaming buffers for enabled channels
channel_buffer = scope.set_data_buffer_for_enabled_channels(samples=SAMPLES)

# Start streaming capture
actual_interval = scope.run_streaming(
    sample_interval=INTERVAL_NS,
    time_units=psdk.PICO_TIME_UNIT.NS,
    max_pre_trigger_samples=0,
    max_post_trigger_samples=SAMPLES,
    auto_stop=1,
    ratio=1,
    ratio_mode=psdk.RATIO_MODE.RAW,
)

# Template describing the streaming buffers
info_template = [
    psdk.PICO_STREAMING_DATA_INFO(
        channel_=ch,
        mode_=psdk.RATIO_MODE.RAW,
        type_=psdk.DATA_TYPE.INT16_T,
        noOfSamples_=0,
        bufferIndex_=0,
        startIndex_=0,
        overflow_=0,
    )
    for ch in channel_buffer
]

auto_stop = False
while not auto_stop:
    info, trigger = scope.get_streaming_latest_values(info_template)
    auto_stop = bool(trigger.autoStop_)
    time.sleep(0.01)

# Convert ADC values to millivolts
waveform_adc = scope.buffer_ctypes_to_list(channel_buffer[psdk.CHANNEL.A])
waveform_mv = scope.buffer_adc_to_mv(waveform_adc, psdk.CHANNEL.A)

# Create time axis from the actual interval
interval_s = actual_interval / psdk.TIME_UNIT.NS
time_axis = [i * interval_s for i in range(len(waveform_mv))]

# Finish with PicoScope
scope.stop()
scope.close_unit()

# Plot data to pyplot
plt.plot(time_axis, waveform_mv)
plt.xlabel("Time (s)")
plt.ylabel("Amplitude (mV)")
plt.grid(True)
plt.show()
