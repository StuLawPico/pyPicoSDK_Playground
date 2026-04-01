import numpy as np
import pypicosdk as psdk

# Streaming settings
buffer_size = 10_000
interval_ms = 1E-3

# Open the scope
scope = psdk.ps6000a()
scope.open_unit()

# Setup the SigGen, Channel and Trigger
scope.set_siggen(frequency=10_000_000, pk2pk=0.8, wave_type=psdk.WAVEFORM.SQUARE)
scope.set_channel(channel=psdk.CHANNEL.A, range=psdk.RANGE.V1, coupling=psdk.COUPLING.DC)
scope.set_simple_trigger(channel=psdk.CHANNEL.A, threshold=0, auto_trigger=0)

# Setup the buffer
buffer = np.empty(buffer_size)
scope.set_data_buffer(channel=psdk.CHANNEL.A, samples=buffer_size, buffer=buffer)

# Run the streaming
actual_interval = scope.run_streaming(
    sample_interval=interval_ms,
    time_units=psdk.TIME_UNIT.MS,
    max_pre_trigger_samples=250,
    max_post_trigger_samples=250,
    auto_stop=0,
    ratio=0,
    ratio_mode=psdk.RATIO_MODE.RAW
)

# Main loop
while True:
    try:
        # Get the latest values
        info = scope.get_streaming_latest_values(channel=psdk.CHANNEL.A, ratio_mode=psdk.RATIO_MODE.RAW, data_type=psdk.DATA_TYPE.INT16_T)

        # If there are samples, print the data
        if info['no of samples'] > 0 and info['triggered?']:
            print(info)

        # If the buffer is full, append it again
        if info['status'] == 407:
            scope.set_data_buffer(channel=psdk.CHANNEL.A, samples=buffer_size, buffer=buffer, action=psdk.ACTION.ADD)

    # If the user interrupts, stop the streaming and close the scope
    except KeyboardInterrupt:
        scope.stop()
        scope.close_unit()
        break