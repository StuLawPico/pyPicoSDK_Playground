"""
Breathing LEDs example for a PSOSPA device

Description:
  Demonstrates the LED channel identification on PSOSPA (3000E) devices by
  gradually varying LED brightness.

Requirements:
- PSOSPA (3000E) device
- Python packages:
  (pip install) pypicosdk

Setup:
  - Connect a PSOSPA device and ensure LEDs are visible
"""

import pypicosdk as psdk
import time

scope = psdk.psospa()
scope.open_unit()

scope.set_all_led_states('on')
scope.set_all_led_colours('blue')

brightness = 50
inc = 2

while True:
    scope.set_led_brightness(brightness)
    if brightness in [0, 100]:
        inc = -inc
    brightness += inc
    time.sleep(.1)
