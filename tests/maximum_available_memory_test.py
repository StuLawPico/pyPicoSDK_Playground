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

from pypicosdk import ps6000a, RESOLUTION


def test_get_maximum_available_memory_invocation():
    scope = ps6000a('pytest')
    called = {}

    def fake_call(name, *args):
        called['name'] = name
        called['args'] = args
        # simulate SDK writing to the output pointer
        import ctypes
        ptr = ctypes.cast(args[1], ctypes.POINTER(ctypes.c_uint64))
        ptr.contents.value = 1234
        return 0

    scope._call_attr_function = fake_call
    scope.resolution = RESOLUTION._12BIT
    result = scope.get_maximum_available_memory()
    assert called['name'] == 'GetMaximumAvailableMemory'
    assert result == 1234
