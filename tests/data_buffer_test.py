import ctypes
from pypicosdk import ps6000a, CHANNEL, RANGE


def test_set_data_buffer_returns_ctypes(monkeypatch):
    scope = ps6000a("pytest")
    scope.range = {CHANNEL.A: RANGE.V1}
    monkeypatch.setattr(scope, "_call_attr_function", lambda *a, **k: 0)
    buf = scope.set_data_buffer(CHANNEL.A, 10)
    assert isinstance(buf, ctypes.Array)
    assert buf._type_ is ctypes.c_int16
    assert len(buf) == 10


def test_set_data_buffer_for_enabled_channels_returns_ctypes(monkeypatch):
    scope = ps6000a("pytest")
    scope.range = {CHANNEL.A: RANGE.V1, CHANNEL.B: RANGE.V1}
    monkeypatch.setattr(scope, "_call_attr_function", lambda *a, **k: 0)
    buffers = scope.set_data_buffer_for_enabled_channels(5)
    assert set(buffers.keys()) == {CHANNEL.A, CHANNEL.B}
    assert all(isinstance(b, ctypes.Array) for b in buffers.values())
    assert all(b._type_ is ctypes.c_int16 for b in buffers.values())
