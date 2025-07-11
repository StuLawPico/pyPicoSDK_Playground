from pypicosdk import ps6000a, RANGE, COUPLING


def test_get_analogue_offset_limits_invocation():
    scope = ps6000a('pytest')
    called = {}

    def fake_call(name, *args):
        called['name'] = name
        called['args'] = args
        import ctypes
        max_ptr = ctypes.cast(args[3], ctypes.POINTER(ctypes.c_double))
        min_ptr = ctypes.cast(args[4], ctypes.POINTER(ctypes.c_double))
        max_ptr.contents.value = 1.2
        min_ptr.contents.value = -0.8
        return 0

    scope._call_attr_function = fake_call
    result = scope.get_analogue_offset_limits(RANGE.V1, COUPLING.DC)
    assert called['name'] == 'GetAnalogueOffsetLimits'
    assert result == {'maximum_voltage': 1.2, 'minimum_voltage': -0.8}

