import pypicosdk as psdk
from pypicosdk import CHANNEL, TRIGGER_STATE


def test_set_trigger_channel_conditions(monkeypatch):
    scope = psdk.ps6000a('pytest')

    captured = {}

    def fake_call(name, handle, cond_array, count, action):
        captured['state'] = cond_array[0].condition_
        captured['action'] = action

    monkeypatch.setattr(scope, '_call_attr_function', fake_call)

    scope.set_trigger_channel_conditions({CHANNEL.A: TRIGGER_STATE.TRUE})

    assert captured['state'] == TRIGGER_STATE.TRUE
    assert captured['action']
