"""Live streaming plot example for a PicoScope 6000A.

This script streams data directly from the scope into a NumPy buffer and
continuously updates a matplotlib plot.  The configuration values below show
how the requested buffer size interacts with the number of points on screen and
the sampling interval.  ``BUFFER_SIZE`` determines how many samples the driver
can write in one transfer, ``PLOT_POINTS`` limits how many of those samples are
displayed at once, and ``SAMPLE_INTERVAL_US`` controls the requested time step
between samples.  Keeping ``BUFFER_SIZE`` reasonably large while limiting
``PLOT_POINTS`` ensures new samples reach the plot quickly without building up
excess history.
"""

import ctypes
from collections import deque

import numpy as np
from matplotlib import pyplot as plt
from matplotlib.animation import FuncAnimation

import pypicosdk as psdk

# Pico examples use inline argument values for clarity.

# Configuration of sampling and plotting behaviour.  ``SAMPLE_INTERVAL_US`` is
# the desired period between ADC samples in microseconds.  ``BUFFER_SIZE`` is
# the number of samples the driver will write into ``stream_buffer`` each time
# ``get_streaming_latest_values`` is called.  ``PLOT_POINTS`` restricts how many
# samples remain on screen so plotting stays responsive even when the capture
# runs for a long time.
SAMPLE_INTERVAL_US = 1
BUFFER_SIZE = 4096
PLOT_POINTS = 1000
# ``VERIFY_BUFFER`` enables sanity checks that compare the number of samples
# returned by the driver with the length of the slices taken from
# ``stream_buffer``.  Leave disabled for normal operation.
VERIFY_BUFFER = False

# Instantiate the PicoScope driver wrapper and open a connection to the device.
# All subsequent calls operate on this ``scope`` object.
scope = psdk.ps6000a()
scope.open_unit()

# Configure channel A for a 1 V range and enable a simple auto trigger so the
# scope begins streaming immediately.
scope.set_channel(channel=psdk.CHANNEL.A, range=psdk.RANGE.V1)
scope.set_simple_trigger(channel=psdk.CHANNEL.A, threshold_mv=0)

# ``stream_buffer`` will store raw ADC values received from the driver.  Its
# size matches ``BUFFER_SIZE`` so a full buffer worth of data can be fetched in
# one call without reallocating memory.
stream_buffer = np.zeros(BUFFER_SIZE, dtype=np.int16)
# ``SetDataBuffer`` tells the driver where to place new samples as they arrive.
# ``ACTION.CLEAR_ALL`` removes any old buffers and ``ACTION.ADD`` registers this
# one for ongoing use.  The buffer is treated as circular; once full the driver
# wraps around to the beginning.
scope._call_attr_function(
    "SetDataBuffer",
    scope.handle,
    psdk.CHANNEL.A,
    stream_buffer.ctypes.data_as(ctypes.POINTER(ctypes.c_int16)),
    BUFFER_SIZE,
    psdk.DATA_TYPE.INT16_T,
    0,
    psdk.RATIO_MODE.RAW,
    psdk.ACTION.CLEAR_ALL | psdk.ACTION.ADD,
)

# Begin the streaming capture.  The buffer size specified here mirrors the size
# provided to ``SetDataBuffer`` above.  ``run_streaming`` returns the actual
# sampling interval used by the device which we store in ``actual_interval`` for
# accurate time axis generation.
actual_interval = scope.run_streaming(
    sample_interval=SAMPLE_INTERVAL_US,
    time_units=psdk.PICO_TIME_UNIT.US,
    max_pre_trigger_samples=0,
    max_post_trigger_samples=BUFFER_SIZE,
    auto_stop=0,
    ratio=0,
    ratio_mode=psdk.RATIO_MODE.RAW,
)
# Choose appropriate time units for the x-axis based on the actual sampling
# interval returned by the driver. The label updates automatically if the
# interval changes.
time_scale = 1.0
x_unit_label = "\u03bcs"
if actual_interval >= 1_000_000:
    time_scale = 1e-6
    x_unit_label = "s"
elif actual_interval >= 1_000:
    time_scale = 1e-3
    x_unit_label = "ms"
elif actual_interval < 1:
    time_scale = 1e3
    x_unit_label = "ns"

# Determine the channel's dynamic range in millivolts so we can scale samples
# to physical units and constrain the y-axis accordingly.  ``scope.range``
# stores the driver enum used during ``set_channel``.
current_range = scope.range[psdk.CHANNEL.A]
range_mv = (
    psdk.RANGE_LIST[current_range] * scope.probe_scale.get(psdk.CHANNEL.A, 1)
)

# Choose display units based on the selected range.  Ranges of 1 V and above are
# shown in volts, otherwise millivolts.
unit_scale = 1.0
unit_label = "mV"
if range_mv >= 1000:
    unit_scale = 0.001
    unit_label = "V"

# ``scale`` converts raw ADC counts directly to the chosen display units.
scale = range_mv / scope.max_adc_value * unit_scale

# ``deque`` containers automatically discard old samples once ``maxlen`` is
# reached.  This gives us a constantly moving window of ``PLOT_POINTS`` samples
# for plotting without manually trimming the arrays.
x_vals = deque(maxlen=PLOT_POINTS)
y_vals = deque(maxlen=PLOT_POINTS)

# Set up the matplotlib figure. ``line`` represents the waveform trace and will
# be updated with each call to ``update``.
fig, ax = plt.subplots()
(line,) = ax.plot([], [], lw=1)
ax.set_xlabel(f"Time ({x_unit_label})")
ax.set_ylabel(f"Amplitude ({unit_label})")
ax.set_ylim(-range_mv * unit_scale, range_mv * unit_scale)
ax.grid(True)  # show gridlines for easier viewing

sample_index = 0
# Structure describing the buffer we want ``get_streaming_latest_values`` to
# fill.  ``noOfSamples_`` is updated before each call to request an entire
# buffer's worth of data.
info = psdk.PICO_STREAMING_DATA_INFO()
info.channel_ = psdk.CHANNEL.A
info.mode_ = psdk.RATIO_MODE.RAW
info.type_ = psdk.DATA_TYPE.INT16_T
info.noOfSamples_ = BUFFER_SIZE

def update(_):
    """Fetch new samples from the driver and extend the plot."""
    global sample_index, current_range, range_mv, unit_scale, unit_label, scale

    # Refresh scaling if the channel range has been changed on the device.
    if scope.range[psdk.CHANNEL.A] != current_range:
        current_range = scope.range[psdk.CHANNEL.A]
        range_mv = (
            psdk.RANGE_LIST[current_range]
            * scope.probe_scale.get(psdk.CHANNEL.A, 1)
        )
        unit_scale = 1.0
        unit_label = "mV"
        if range_mv >= 1000:
            unit_scale = 0.001
            unit_label = "V"
        scale = range_mv / scope.max_adc_value * unit_scale
        ax.set_ylabel(f"Amplitude ({unit_label})")
        ax.set_ylim(-range_mv * unit_scale, range_mv * unit_scale)
    # Ensure the x-axis label matches the selected time units.
    ax.set_xlabel(f"Time ({x_unit_label})")

    # Request another block of samples. ``get_streaming_latest_values`` fills
    # ``stream_buffer`` starting at ``startIndex_`` and reports how many samples
    # were written.
    info.noOfSamples_ = BUFFER_SIZE
    data_info, _ = scope.get_streaming_latest_values([info])
    current = data_info[0]
    if VERIFY_BUFFER:
        print(
            f"startIndex={current.startIndex_} samples={current.noOfSamples_}"
        )

    if current.noOfSamples_:
        start = current.startIndex_
        end = start + current.noOfSamples_
        if end <= BUFFER_SIZE:
            adc_slice = stream_buffer[start:end]
        else:
            end_wrap = end - BUFFER_SIZE
            adc_slice = np.concatenate((stream_buffer[start:], stream_buffer[:end_wrap]))
        if VERIFY_BUFFER and len(adc_slice) != current.noOfSamples_:
            print(
                f"Warning: driver reported {current.noOfSamples_} samples "
                f"but slice length is {len(adc_slice)}"
            )

        # Convert raw ADC counts directly into the display units (V or mV).
        y_slice = adc_slice.astype(np.float64) * scale

        # Generate time values using the ongoing ``sample_index`` counter and
        # the actual sampling interval reported by the driver.
        times = (
            np.arange(sample_index, sample_index + current.noOfSamples_)
            * actual_interval
            * time_scale
        )
        sample_index += current.noOfSamples_

        # Append the new samples to the rolling deques.  Old samples are
        # automatically discarded once ``PLOT_POINTS`` is exceeded.
        x_vals.extend(times)
        y_vals.extend(y_slice)

        # Update the plotted line with the latest window of data.
        line.set_data(x_vals, y_vals)

        # Keep the x-axis focused on the newest samples.
        start_time = max(0, times[-1] - PLOT_POINTS * actual_interval * time_scale)
        # The x-axis shows only ``PLOT_POINTS`` worth of history for
        # responsiveness; older data scrolls off the left.
        ax.set_xlim(start_time, times[-1])



        # Re-queue the buffer so the driver continues to fill it with data for
        # the next call.
        scope._call_attr_function(
            "SetDataBuffer",
            scope.handle,
            psdk.CHANNEL.A,
            stream_buffer.ctypes.data_as(ctypes.POINTER(ctypes.c_int16)),
            BUFFER_SIZE,
            psdk.DATA_TYPE.INT16_T,
            0,
            psdk.RATIO_MODE.RAW,
            psdk.ACTION.ADD,
        )

    return line,

ani = FuncAnimation(fig, update, interval=20, cache_frame_data=False)
plt.show()

# Stop streaming and release the hardware once the plot window is closed.
scope.stop()
scope.close_unit()
