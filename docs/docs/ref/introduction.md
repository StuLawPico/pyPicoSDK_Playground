# Introduction

Each picoSDK class is built from a common class (PicoScopeBase) and a specific sub-class (ps####a).
This allows each PicoScope to have shared, common functions (such as opening the unit) and hardware-specific capabilities like power source selection on certain models.

## Example style
To make the API easy to follow, examples use inline arguments rather than
setup variables. You can of course store values in variables first if that
makes your code clearer.

## C PicoSDK (ctypes)
This wrapper is built over the C DLL drivers from Pico Technology. 
Therefore most basic python functions (such as `run_block()`) have a counterpart in the C library (e.g. `ps6000aRunBlockMode()`). 
These python functions parse the variables through the DLL's using the `ctypes` package to talk directly to the unit. 
For reference on these DLL's and their C implementation, go to [https://www.picotech.com/downloads/documentation](https://www.picotech.com/downloads/documentation) and look for your PicoScope Programmer's Guide.

## FAQ's
### Does my PicoScope use ps6000a() or ps6000()?
The PicoScope (A) drivers are the latest generation of drivers from Pico Technology. If you have a PicoScope with a letter designation higher than the following, you will need to use the (A) class and drivers:

 - PicoScope 3000**D**
 - PicoScope 6000**E**

[Click here to see the current support for these wrappers.](../dev/current.md)
