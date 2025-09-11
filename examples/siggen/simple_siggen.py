"""
Simple signal generator example for a PicoScope 6000E device

Description:
  Outputs a basic sine wave using the signal generator.

Requirements:
- PicoScope 6000E
- Python packages:
  (pip install) pypicosdk

Setup:
  - Connect the AWG output as required
"""

import pypicosdk as psdk

scope = psdk.ps6000a()
scope.open_unit()

# Setup signal generator
scope.set_siggen(frequency=1000, pk2pk=2, wave_type=psdk.WAVEFORM.SINE)
input("Return to continue... ")

scope.close_unit()

