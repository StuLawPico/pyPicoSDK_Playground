import pytest
from pypicosdk import ps6000a


def test_waiting_for_data_buffers_is_ignored():
    scope = ps6000a('pytest')
    # should not raise for PICO_WAITING_FOR_DATA_BUFFERS
    scope._error_handler(407)
