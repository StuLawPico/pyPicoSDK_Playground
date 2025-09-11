"""
Timebase calculation example for a PicoScope 6000E device

Description:
  Shows how to determine the correct timebase value for a specific
  sampling interval.

Requirements:
- PicoScope 6000E
- Python packages:
  (pip install) pypicosdk

Setup:
  - Connect any required probes to the oscilloscope
"""
from pypicosdk import ps6000a, CHANNEL, RANGE, SAMPLE_RATE, TIME_UNIT

# Variables
interval_s = 10E-9 # 10 us

# Open PicoScope 6000
scope = ps6000a()
scope.open_unit()

# Setup channels to make sure sample interval is accurate
scope.set_channel(CHANNEL.A, RANGE.V1)
scope.set_channel(CHANNEL.C, RANGE.mV100)

# Return suggested timebase and actual sample interval 
print(scope.sample_rate_to_timebase(100, unit=SAMPLE_RATE.MSPS))
print(scope.interval_to_timebase(0.01, unit=TIME_UNIT.US))
print(scope.get_nearest_sampling_interval(10E-9))
