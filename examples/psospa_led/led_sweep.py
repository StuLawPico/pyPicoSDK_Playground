"""
LED sweep example for a PSOSPA device

Description:
  Cycles the LED channel identification on PSOSPA (3000E) devices.

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

scope.set_all_led_states('off')
scope.set_all_led_colours('red')

led_list = ['A', 'B', 'C', 'D', 'AUX', 'AWG']
sweep = ['off'] * 6
n_sweep = 1
sweep_inc = 1

while True:
    sweep[n_sweep] = 'on'
    scope.set_led_states(led_list, sweep)
    time.sleep(.1)
    sweep[n_sweep] = 'off'
    if n_sweep in [0, 5]:
        sweep_inc = -sweep_inc
    n_sweep += sweep_inc
