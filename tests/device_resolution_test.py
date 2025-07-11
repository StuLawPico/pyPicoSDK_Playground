from pypicosdk import ps6000a, RESOLUTION


def test_set_device_resolution_invocation():
    scope = ps6000a('pytest')
    called = {}

    def fake_call(name, *args):
        called['name'] = name
        called['args'] = args
        return 0

    scope._call_attr_function = fake_call
    scope._get_adc_limits = lambda: (1, 2)
    scope.set_device_resolution(RESOLUTION._12BIT)
    assert called['name'] == 'SetDeviceResolution'
    assert scope.resolution == RESOLUTION._12BIT
    assert scope.min_adc_value == 1
    assert scope.max_adc_value == 2

