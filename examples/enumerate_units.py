"""
Enumerate units example for PicoScope devices

Description:
  Enumerates all supported PicoScope units and prints the number of
  detected devices along with their serial numbers.

Requirements:
- Python packages:
  (pip install) pypicosdk

Setup:
  - Connect any supported PicoScope devices
"""

import pypicosdk as psdk

# Enumerate units and print the results
n_units, unit_list = psdk.get_all_enumerated_units()
print(f"Number of units: {n_units}")
for serial in unit_list:
    print(f"Serial number: {serial}")