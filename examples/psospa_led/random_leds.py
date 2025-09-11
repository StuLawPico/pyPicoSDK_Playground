"""
Random LED colors example for a PSOSPA device

Description:
  Demonstrates setting random LED colours on PSOSPA (3000E) devices.

Requirements:
- PSOSPA (3000E) device
- Python packages:
  (pip install) pypicosdk numpy

Setup:
  - Connect a PSOSPA device and ensure LEDs are visible
"""

import pypicosdk as psdk
import time
from numpy.random import randint

scope = psdk.psospa()
scope.open_unit()

scope.set_all_led_states('on')

led_list = ['A', 'B', 'C', 'D', 'AUX', 'AWG']

while True:
    random_values = randint(0, 360, size=6)
    scope.set_led_colours(
        led_list, 
        randint(0, 360, size=6), 
        [100]*6,
    )
    time.sleep(1)
