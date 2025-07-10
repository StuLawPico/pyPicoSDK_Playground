"""Live streaming plot example for a PicoScope 6000A.

This script streams **raw ADC values** directly from the scope into a NumPy
buffer and continuously updates a matplotlib plot.  The configuration values
below show
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
# Key ``STOP_KEY`` stops the scope but leaves the plot running when pressed.
STOP_KEY = "s"
# ``SHOW_INDICATORS`` toggles vertical markers for the latest sample and the
# end of the circular buffer.
SHOW_INDICATORS = True

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

# This example plots raw ADC counts without converting to physical units.
unit_label = "ADC"

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
# Plot raw ADC counts so no range scaling is applied.
ax.grid(True)  # show gridlines for easier viewing

if SHOW_INDICATORS:
    end_line = ax.axvline(0, color="tab:red", ls="--", lw=0.8)
    buffer_line = ax.axvline(0, color="tab:blue", ls=":", lw=0.8)
else:
    end_line = buffer_line = None

scope_stopped = False

sample_index = 0
# Structure describing the buffer we want ``get_streaming_latest_values`` to
# fill.  ``noOfSamples_`` is updated before each call to request an entire
# buffer's worth of data.
info = psdk.PICO_STREAMING_DATA_INFO()
info.channel_ = psdk.CHANNEL.A
info.mode_ = psdk.RATIO_MODE.RAW
info.type_ = psdk.DATA_TYPE.INT16_T
info.noOfSamples_ = BUFFER_SIZE


def on_key(event):
    """Stop streaming when ``STOP_KEY`` is pressed."""
    global scope_stopped
    if event.key == STOP_KEY and not scope_stopped:
        scope.stop()
        scope_stopped = True
        print("Streaming stopped")


def on_close(_):
    """Ensure the scope is closed when the plot window exits."""
    if not scope_stopped:
        scope.stop()
    scope.close_unit()


def update(_):
    """Fetch new samples from the driver and extend the plot."""
    global sample_index

    if scope_stopped:
        return (line,)

    # Plotting raw ADC values so no scaling adjustments are needed.
    # Ensure the x-axis label matches the selected time units.
    ax.set_xlabel(f"Time ({x_unit_label})")

    # Request another block of samples. ``get_streaming_latest_values`` fills
    # ``stream_buffer`` starting at ``startIndex_`` and reports how many samples
    # were written.
    info.noOfSamples_ = BUFFER_SIZE
    data_info, _ = scope.get_streaming_latest_values([info])
    current = data_info[0]
    if VERIFY_BUFFER:
        print(f"startIndex={current.startIndex_} samples={current.noOfSamples_}")

    if current.noOfSamples_:
        start = current.startIndex_
        end = start + current.noOfSamples_
        if end <= BUFFER_SIZE:
            adc_slice = stream_buffer[start:end]
        else:
            end_wrap = end - BUFFER_SIZE
            adc_slice = np.concatenate(
                (stream_buffer[start:], stream_buffer[:end_wrap])
            )
        if VERIFY_BUFFER and len(adc_slice) != current.noOfSamples_:
            print(
                f"Warning: driver reported {current.noOfSamples_} samples "
                f"but slice length is {len(adc_slice)}"
            )

        # Plot raw ADC counts without conversion.
        y_slice = adc_slice.astype(np.float64)

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

    if SHOW_INDICATORS:
        end_time = sample_index * actual_interval * time_scale
        buffer_time = max(
            0, end_time - BUFFER_SIZE * actual_interval * time_scale
        )
        end_line.set_xdata(end_time)
        buffer_line.set_xdata(buffer_time)
        return line, end_line, buffer_line

    return (line,)


fig.canvas.mpl_connect("key_press_event", on_key)
fig.canvas.mpl_connect("close_event", on_close)

ani = FuncAnimation(fig, update, interval=20, cache_frame_data=False)
plt.show()

# Stop streaming and release the hardware when the plot closes.
