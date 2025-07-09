import ctypes
import pypicosdk as psdk


def test_get_trigger_info(monkeypatch):
    scope = psdk.ps6000a('pytest')

    def fake_call(name, handle, info_ptr, first, count):
        arr = ctypes.cast(info_ptr, ctypes.POINTER(psdk.PICO_TRIGGER_INFO))
        arr[0].status_ = 1
        arr[0].segmentIndex_ = first
        arr[0].triggerIndex_ = 0
        arr[0].triggerTime_ = 1.23
        arr[0].timeUnits_ = 3
        arr[0].missedTriggers_ = 0
        arr[0].timeStampCounter_ = 42

    monkeypatch.setattr(scope, '_call_attr_function', fake_call)

    info = scope.get_trigger_info(0, 1)

    assert info.triggerTime_ == 1.23
    assert info.timeUnits_ == 3
