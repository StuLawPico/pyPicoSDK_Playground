import sys
import os

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, repo_root)
if 'pypicosdk' in sys.modules:
    del sys.modules['pypicosdk']
if 'pypicosdk.constants' in sys.modules:
    del sys.modules['pypicosdk.constants']
if 'pypicosdk.pypicosdk' in sys.modules:
    del sys.modules['pypicosdk.pypicosdk']

from pypicosdk import ps6000a, CHANNEL, RANGE
from pypicosdk.constants import (
    PICO_TRIGGER_STATE,
    PICO_THRESHOLD_DIRECTION,
    PICO_THRESHOLD_MODE,
)


def test_set_advanced_trigger_invocation():
    scope = ps6000a('pytest')
    calls = []

    def fake_call(name, *args):
        calls.append((name, args))
        return 0

    scope._call_attr_function = fake_call
    scope.max_adc_value = 32000
    scope.range = {CHANNEL.A: RANGE.V1}

    scope.set_advanced_trigger(
        channel=CHANNEL.A,
        state=PICO_TRIGGER_STATE.TRUE,
        direction=PICO_THRESHOLD_DIRECTION.PICO_RISING,
        threshold_mode=PICO_THRESHOLD_MODE.PICO_LEVEL,
        threshold_upper_mv=500,
        threshold_lower_mv=-500,
        auto_trigger_ms=2,
    )

    assert calls[0][0] == 'SetTriggerChannelConditions'
    assert calls[1][0] == 'SetTriggerChannelDirections'
    assert calls[2][0] == 'SetTriggerChannelProperties'
    assert calls[2][1][-1].value == 2000

