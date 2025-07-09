import pypicosdk as psdk


def test_set_advanced_trigger_order(monkeypatch):
    scope = psdk.ps6000a('pytest')
    calls = []

    monkeypatch.setattr(scope, 'set_trigger_channel_properties', lambda *a, **k: calls.append('properties'))
    monkeypatch.setattr(scope, 'set_trigger_channel_directions', lambda *a, **k: calls.append('directions'))
    monkeypatch.setattr(scope, 'set_trigger_channel_conditions', lambda *a, **k: calls.append('conditions'))

    scope.set_advanced_trigger([], {}, {})

    assert calls == ['properties', 'directions', 'conditions']
