import ctypes
import pypicosdk as psdk
from pypicosdk import PICO_TIME_UNIT


def test_get_values_trigger_time_offset_bulk(monkeypatch):
    scope = psdk.ps6000a('pytest')

    def fake_call(name, handle, times_ptr, units_ptr, first, last):
        t_arr = ctypes.cast(times_ptr, ctypes.POINTER(ctypes.c_int64))
        u_arr = ctypes.cast(units_ptr, ctypes.POINTER(ctypes.c_int32))
        t_arr[0] = 10
        t_arr[1] = 20
        u_arr[0] = PICO_TIME_UNIT.NS
        u_arr[1] = PICO_TIME_UNIT.US

    monkeypatch.setattr(scope, '_call_attr_function', fake_call)

    offsets = scope.get_values_trigger_time_offset_bulk(0, 1)

    assert offsets == [(10, PICO_TIME_UNIT.NS), (20, PICO_TIME_UNIT.US)]
