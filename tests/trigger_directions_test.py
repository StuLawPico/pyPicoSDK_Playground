import pypicosdk as psdk
from pypicosdk import CHANNEL, THRESHOLD_MODE, TRIGGER_DIR


def test_set_trigger_channel_directions(monkeypatch):
    scope = psdk.ps6000a('pytest')

    captured = {}

    def fake_call(name, handle, dir_array, count):
        captured['direction'] = dir_array[0].direction_
        captured['mode'] = dir_array[0].thresholdMode_

    monkeypatch.setattr(scope, '_call_attr_function', fake_call)

    scope.set_trigger_channel_directions({CHANNEL.A: (TRIGGER_DIR.RISING, THRESHOLD_MODE.LEVEL)})

    assert captured['direction'] == TRIGGER_DIR.RISING
    assert captured['mode'] == THRESHOLD_MODE.LEVEL
