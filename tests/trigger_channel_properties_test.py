import pypicosdk as psdk
from pypicosdk import CHANNEL, RANGE


def test_set_trigger_channel_properties(monkeypatch):
    scope = psdk.ps6000a('pytest')
    scope.max_adc_value = 32000
    scope.range = {CHANNEL.A: RANGE.V1}

    captured = {}

    def fake_call(name, handle, prop_array, count, aux, auto):
        captured['upper'] = prop_array[0].thresholdUpper_
        captured['lower'] = prop_array[0].thresholdLower_
        captured['auto'] = auto

    monkeypatch.setattr(scope, '_call_attr_function', fake_call)

    scope.set_trigger_channel_properties([
        {'channel': CHANNEL.A, 'threshold_upper': 100, 'threshold_lower': -100}
    ], auto_trigger_ms=2)

    assert captured['upper'] == int((100 / 1000) * 32000)
    assert captured['lower'] == int((-100 / 1000) * 32000)
    assert captured['auto'] == 2000
