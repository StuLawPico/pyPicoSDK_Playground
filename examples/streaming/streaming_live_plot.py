"""
Streaming live plot example for a PicoScope 6000E device

Description:
  Displays single-channel streaming data using a matplotlib animation. The
  StreamingScope class runs the streaming loop in a separate thread.

Requirements:
- PicoScope 6000E
- Python packages:
  (pip install) matplotlib numpy pypicosdk

Setup:
  - Connect Channel A to the signal source

Downsampling:
    This streaming example uses AGGREGATE downsampling. Two buffers
    (MIN and MAX) are returned for each group of samples. The midpoint
    is calculated and displayed.

    Using other downsampling methods will return a single buffer.
"""

import threading
import numpy as np

from matplotlib import pyplot as plt
from matplotlib.animation import FuncAnimation

import pypicosdk as psdk
from pypicosdk.streaming import StreamingScope

# Capture configuration
SAMPLES = 10_000
INTERVAL = 1
UNIT = psdk.TIME_UNIT.US
CHANNEL = psdk.CHANNEL.A

# Downsample data using min/max aggregate
RATIO = 100
RATIO_MODE = psdk.RATIO_MODE.AGGREGATE

# Setup classe objects
scope = psdk.ps6000a()
stream = StreamingScope(scope)


def setup_pyplot():
    """Sets up pyplot with empty data"""
    fig = plt.figure()
    axis = plt.axes(xlim=(0, SAMPLES),
                    ylim=(-scope.min_adc_value, scope.max_adc_value))
    # Initialize with numpy array of zeros
    x = np.arange(SAMPLES)
    line, = axis.plot(x, np.zeros_like(x), lw=2)
    return fig, line


def setup_scope():
    """Setup PicoScope and get scope class"""
    scope.open_unit()
    scope.set_siggen(frequency=10, pk2pk=1.6,
                     wave_type=psdk.WAVEFORM.TRIANGLE)
    scope.set_channel(channel=psdk.CHANNEL.A, range=psdk.RANGE.V1)
    scope.set_simple_trigger(channel=psdk.CHANNEL.A, threshold_mv=0)


def streaming_thread():
    """Streaming thread"""
    stream.start_streaming_while()


def get_data():
    """Get data from streaming class based on ratio mode"""
    # If AGGREGATE ratio mode, find midpoint
    if RATIO_MODE == psdk.RATIO_MODE.AGGREGATE:
        return (stream.buffer[0] + stream.buffer[1]) / 2
    return stream.buffer


def animate(_frame, line):
    """pyplot animation thread"""
    line.set_ydata(get_data())
    return [line]


def main():
    """Main function"""
    setup_scope()
    fig, line = setup_pyplot()

    stream.config_streaming(CHANNEL, SAMPLES, INTERVAL, UNIT, ratio=RATIO, ratio_mode=RATIO_MODE)

    th = threading.Thread(target=streaming_thread)
    th.start()

    _ = FuncAnimation(fig, animate, frames=500, fargs=(line,), interval=20, blit=True)
    plt.show()

    stream.stop()
    th.join()

    scope.close_unit()


if __name__ == '__main__':
    main()
