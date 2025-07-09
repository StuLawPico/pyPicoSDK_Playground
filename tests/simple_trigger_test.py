import pypicosdk as psdk
from pypicosdk import CHANNEL, RANGE


def test_set_simple_trigger_auto_convert(monkeypatch):
    scope = psdk.ps6000a('pytest')
    scope.max_adc_value = 32000
    scope.range = {CHANNEL.A: RANGE.V1}

    called = {}

    def fake_call(name, *args):
        called['args'] = (name,) + args

    monkeypatch.setattr(scope, '_call_attr_function', fake_call)

    scope.set_simple_trigger(CHANNEL.A, threshold_mv=100, auto_trigger_ms=5)

    assert called['args'][0] == 'SetSimpleTrigger'
    # threshold converted to ADC counts
    assert called['args'][4] == int((100 / 1000) * 32000)
    # auto trigger converted to microseconds
    assert called['args'][-1] == 5000
