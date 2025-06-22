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

from pypicosdk import ps6000a, RANGE, CHANNEL


def test_mv_to_adc():
    scope = ps6000a('pytest')
    scope.max_adc_value = 32000
    assert scope.mv_to_adc(5.0, RANGE.V1) == 160


def test_adc_to_mv():
    scope = ps6000a('pytest')
    scope.max_adc_value = 32000
    assert scope.adc_to_mv(160, RANGE.V1) == 5.0


def test_buffer_adc_to_mv():
    scope = ps6000a('pytest')
    scope.max_adc_value = 32000
    scope.range = {CHANNEL.A: RANGE.V10}
    assert scope.buffer_adc_to_mv([160, 250, 1550], CHANNEL.A) == [50.0, 78.125, 484.375]


def test_channels_buffer_adc_to_mv():
    scope = ps6000a('pytest')
    scope.max_adc_value = 32000
    scope.range = {CHANNEL.A: RANGE.V10, CHANNEL.B: RANGE.V1}
    assert scope.channels_buffer_adc_to_mv({
        CHANNEL.A: [160, 250, 1550],
        CHANNEL.B: [100, 2500, 6000, 23]
    }) == {
        CHANNEL.A: [50.0, 78.125, 484.375],
        CHANNEL.B: [3.125, 78.125, 187.5, 0.71875]
    }


def test_probe_scale_conversion():
    scope = ps6000a('pytest')
    scope.max_adc_value = 32000
    scope.probe_scale = {CHANNEL.A: 10}
    assert scope.mv_to_adc(50.0, RANGE.V1, channel=CHANNEL.A) == 160
    assert scope.adc_to_mv(160, RANGE.V1, channel=CHANNEL.A) == 50.0



