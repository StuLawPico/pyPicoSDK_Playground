import ctypes
import numpy as np
from .base import PicoScopeBase
from .constants import (
    CHANNEL,
    RANGE,
    COUPLING,
    BANDWIDTH_CH,
    DATA_TYPE,
    RATIO_MODE,
    ACTION,
    WAVEFORM,
    TRIGGER_DIR,
    TRIGGER_STATE,
    THRESHOLD_MODE,
    THRESHOLD_DIRECTION,
    CONDITIONS_INFO,
    RESOLUTION,
    TIME_UNIT,
)

class ps6000a(PicoScopeBase):
    """PicoScope 6000 (A) API specific functions"""
    def __init__(self, *args, **kwargs):
        """Create a PicoScope 6000A instance and load its SDK library."""
        super().__init__("ps6000a", *args, **kwargs)


    def open_unit(self, serial_number: str | None = None, resolution: RESOLUTION = RESOLUTION._8BIT) -> None:
        """
        Open PicoScope unit.

        Args:
                serial_number (str, optional): Serial number of device.
                resolution (RESOLUTION, optional): Resolution of device.
        """
        super()._open_unit(serial_number, resolution)
        self.min_adc_value, self.max_adc_value =super()._get_adc_limits()
    
    def get_timebase(self, timebase:int, samples:int, segment:int=0) -> None:
        """
        This function calculates the sampling rate and maximum number of 
        samples for a given timebase under the specified conditions.

        Args:
                timebase (int): Selected timebase multiplier (refer to programmer's guide).
                samples (int): Number of samples.
                segment (int, optional): The index of the memory segment to use.

        Returns:
                dict: Returns interval (ns) and max samples as a dictionary.
        """

        return super()._get_timebase(timebase, samples, segment)
    
    def set_channel(self, channel:CHANNEL, range:RANGE, enabled=True, coupling:COUPLING=COUPLING.DC, 
                    offset:float=0.0, bandwidth=BANDWIDTH_CH.FULL) -> None:
        """
        Enable/disable a channel and specify certain variables i.e. range, coupling, offset, etc.
        
        For the ps6000a drivers, this combines _set_channel_on/off to a single function. 
        Set channel on/off by adding enabled=True/False

        Args:
                channel (CHANNEL): Channel to setup.
                range (RANGE): Voltage range of channel.
                enabled (bool, optional): Enable or disable channel.
                coupling (COUPLING, optional): AC/DC/DC 50 Ohm coupling of selected channel.
                offset (int, optional): Analog offset in volts (V) of selected channel.
                bandwidth (BANDWIDTH_CH, optional): Bandwidth of channel (selected models).
        """
        if enabled:
            super()._set_channel_on(channel, range, coupling, offset, bandwidth)
        else:
            super()._set_channel_off(channel)

    def set_simple_trigger(self, channel, threshold_mv, enable=True, direction=TRIGGER_DIR.RISING, delay=0, auto_trigger_ms=5_000):
        """
        Sets up a simple trigger from a specified channel and threshold in mV

        Args:
            channel (int): The input channel to apply the trigger to.
            threshold_mv (float): Trigger threshold level in millivolts.
            enable (bool, optional): Enables or disables the trigger. 
            direction (TRIGGER_DIR, optional): Trigger direction (e.g., TRIGGER_DIR.RISING, TRIGGER_DIR.FALLING). 
            delay (int, optional): Delay in samples after the trigger condition is met before starting capture. 
            auto_trigger_ms (int, optional): Timeout in milliseconds after which data capture proceeds even if no trigger occurs. 
        """
        auto_trigger_us = auto_trigger_ms * 1000
        return super().set_simple_trigger(channel, threshold_mv, enable, direction, delay, auto_trigger_us)

    def set_trigger_channel_properties(self, properties, aux_output_enable=0, auto_trigger_ms=0):
        """Wrapper converting auto-trigger from ms to µs."""

        auto_trigger_us = auto_trigger_ms * 1000
        return super().set_trigger_channel_properties(properties, aux_output_enable, auto_trigger_us)

    def set_advanced_trigger(self, properties, directions, conditions, aux_output_enable=0, auto_trigger_ms=0, action=CONDITIONS_INFO.CLEAR_CONDITIONS | CONDITIONS_INFO.ADD_CONDITION):
        """Configure an advanced trigger using millisecond units."""

        auto_trigger_us = auto_trigger_ms * 1000
        super().set_advanced_trigger(properties, directions, conditions, aux_output_enable, auto_trigger_us, action)
    
    def set_data_buffer(
        self,
        channel: CHANNEL,
        samples: int,
        segment: int = 0,
        datatype: DATA_TYPE = DATA_TYPE.INT16_T,
        ratio_mode: RATIO_MODE = RATIO_MODE.RAW,
        action: ACTION = ACTION.CLEAR_ALL | ACTION.ADD,
    ) -> ctypes.Array:
        """Assign a single data buffer for ``get_values`` results.

        Args:
            channel (CHANNEL): Channel you want to use with the buffer.
            samples (int): Number of samples/length of the buffer.
            segment (int, optional): Location of the buffer.
            datatype (DATA_TYPE, optional): C datatype of the data.
            ratio_mode (RATIO_MODE, optional): Down-sampling mode.
            action (ACTION, optional): Method to use when creating a buffer.

        Returns:
            ctypes.Array: Array that will be populated when ``get_values`` is
            called.
        """

        return super()._set_data_buffer_ps6000a(
            channel, samples, segment, datatype, ratio_mode, action
        )

    def set_data_buffers(
        self,
        channel: CHANNEL,
        samples: int,
        segment: int = 0,
        datatype: DATA_TYPE = DATA_TYPE.INT16_T,
        ratio_mode: RATIO_MODE = RATIO_MODE.AGGREGATE,
        action: ACTION = ACTION.CLEAR_ALL | ACTION.ADD,
    ) -> tuple[ctypes.Array, ctypes.Array]:
        """Configure both maximum and minimum data buffers for a channel.

        Use this when downsampling in aggregation mode or requesting
        post-capture aggregated values.

        Args:
            channel (CHANNEL): Channel you want to use with the buffers.
            samples (int): Number of samples/length of each buffer.
            segment (int, optional): Memory segment index for the buffers.
            datatype (DATA_TYPE, optional): C datatype of the data stored in the
                buffers.
            ratio_mode (RATIO_MODE, optional): Downsampling mode. Typically
                ``RATIO_MODE.AGGREGATE`` when both buffers are required.
            action (ACTION, optional): Method used when creating or updating the
                buffers.

        Returns:
            tuple[ctypes.Array, ctypes.Array]: ``(buffer_max, buffer_min)`` that
            will be populated when :meth:`get_values` is called.
        """

        return super()._set_data_buffers_ps6000a(
            channel,
            samples,
            segment,
            datatype,
            ratio_mode,
            action,
        )
    
    def set_data_buffer_for_enabled_channels(
        self,
        samples: int,
        segment: int = 0,
        datatype: DATA_TYPE = DATA_TYPE.INT16_T,
        ratio_mode: RATIO_MODE = RATIO_MODE.RAW,
    ) -> dict:
        """Create buffers for all currently enabled channels.

        Args:
            samples (int): The sample buffer size to allocate.
            segment (int): The memory segment index.
            datatype (DATA_TYPE): The data type used for the buffer.
            ratio_mode (RATIO_MODE): The ratio mode (e.g., RAW, AVERAGE).

        Returns:
            dict: Mapping of each channel to its associated ctypes array buffer.
        """

        super()._set_data_buffer_ps6000a(0, 0, 0, 0, 0, ACTION.CLEAR_ALL)
        channels_buffer = {}
        for channel in self.range:
            channels_buffer[channel] = super()._set_data_buffer_ps6000a(
                channel,
                samples,
                segment,
                datatype,
                ratio_mode,
                action=ACTION.ADD,
            )
        return channels_buffer
    
    def set_siggen(self, frequency:float, pk2pk:float, wave_type:WAVEFORM, offset:float=0.0, duty:float=50) -> dict:
        """Configures and applies the signal generator settings.

        Sets up the signal generator with the specified waveform type, frequency,
        amplitude (peak-to-peak), offset, and duty cycle.

        Args:
            frequency (float): Signal frequency in hertz (Hz).
            pk2pk (float): Peak-to-peak voltage in volts (V).
            wave_type (WAVEFORM): Waveform type (e.g., WAVEFORM.SINE, WAVEFORM.SQUARE).
            offset (float, optional): Voltage offset in volts (V).
            duty (int or float, optional): Duty cycle as a percentage (0–100).

        Returns:
            dict: Returns dictionary of the actual achieved values.
        """
        self._siggen_set_waveform(wave_type)
        self._siggen_set_range(pk2pk, offset)
        self._siggen_set_frequency(frequency)
        self._siggen_set_duty_cycle(duty)
        return self._siggen_apply()

    def run_simple_block_capture(
        self,
        timebase: int,
        samples: int,
        segment: int = 0,
        start_index: int = 0,
        datatype: DATA_TYPE = DATA_TYPE.INT16_T,
        ratio: int = 0,
        ratio_mode: RATIO_MODE = RATIO_MODE.RAW,
        pre_trig_percent: int = 50,
        time_unit: TIME_UNIT | None = TIME_UNIT.NS,
    ) -> tuple[dict, "np.ndarray"]:
        """Performs a complete single block capture using current channel and trigger configuration.

        This function sets up data buffers for all enabled channels, starts a block capture,
        and retrieves the values once the device is ready. It is a simplified interface 
        for common block capture use cases.

        Args:
            timebase (int): Timebase value determining the sample interval (refer to PicoSDK guide).
            samples (int): Total number of samples to capture.
            segment (int, optional): Memory segment index to use.
            start_index (int, optional): Starting index in the buffer.
            datatype (DATA_TYPE, optional): Data type to use for the capture buffer.
            ratio (int, optional): Downsampling ratio.
            ratio_mode (RATIO_MODE, optional): Downsampling mode.
            pre_trig_percent (int, optional): Percentage of samples to capture before the trigger.
            time_unit (TIME_UNIT | None, optional): Units for the returned time axis.
                ``None`` selects a sensible unit automatically.

        Returns:
            dict: Mapping of each enabled channel to a numpy array of captured values in mV.
            numpy.ndarray: Time axis (x-axis) of timestamps for the sample data.

        Examples:
            >>> scope.set_channel(CHANNEL.A, RANGE.V1)
            >>> scope.set_simple_trigger(CHANNEL.A, threshold_mv=500)
            >>> buffers = scope.run_simple_block_capture(timebase=3, samples=1000)
        """
        # Setup data buffer for enabled channels
        channels_buffer = self.set_data_buffer_for_enabled_channels(samples, segment, datatype, ratio_mode)

        # Start block capture
        self.run_block_capture(timebase, samples, pre_trig_percent, segment)

        # Get values from PicoScope (returning actual samples for time_axis)
        actual_samples = self.get_values(samples, start_index, segment, ratio, ratio_mode)

        # Convert from ADC to mV values and into numpy arrays
        channels_buffer = {
            ch: np.asarray(self.buffer_adc_to_mv(buf, ch), dtype=float)
            for ch, buf in channels_buffer.items()
        }

        # Generate the time axis based on actual samples and timebase
        time_axis = np.asarray(self.get_time_axis(timebase, actual_samples, time_unit), dtype=float)

        return channels_buffer, time_axis

    def run_simple_rapid_block_capture(
        self,
        timebase: int,
        samples: int,
        n_captures: int,
        start_index: int = 0,
        datatype: DATA_TYPE = DATA_TYPE.INT16_T,
        ratio: int = 0,
        ratio_mode: RATIO_MODE = RATIO_MODE.RAW,
        pre_trig_percent: int = 50,
        time_unit: TIME_UNIT | None = TIME_UNIT.NS,
    ) -> tuple[list[dict], "np.ndarray"]:
        """Perform a rapid block capture using the current configuration.

        Args:
            timebase (int): Timebase determining sample interval.
            samples (int): Samples per capture.
            n_captures (int): Number of captures to perform.
            start_index (int, optional): Starting index in each buffer.
            datatype (DATA_TYPE, optional): Buffer data type.
            ratio (int, optional): Downsampling ratio.
            ratio_mode (RATIO_MODE, optional): Downsampling mode.
            pre_trig_percent (int, optional): Percentage of pre-trigger samples.
            time_unit (TIME_UNIT | None, optional): Unit of the returned time axis.

        Returns:
            list[dict]: List of channel buffers per capture in mV.
            numpy.ndarray: Time axis for the captured samples.
        """

        self.memory_segments(n_captures)
        self.set_no_of_captures(n_captures)

        segment_buffers = [
            self.set_data_buffer_for_enabled_channels(samples, seg, datatype, ratio_mode)
            for seg in range(n_captures)
        ]

        self.run_block_capture(timebase, samples, pre_trig_percent, segment=0)

        actual_samples = self.get_values_bulk(
            start_index,
            samples,
            0,
            n_captures - 1,
            ratio,
            ratio_mode,
        )

        segment_buffers = [
            {
                ch: np.asarray(self.buffer_adc_to_mv(buf, ch), dtype=float)
                for ch, buf in seg_buf.items()
            }
            for seg_buf in segment_buffers
        ]

        time_axis = np.asarray(self.get_time_axis(timebase, actual_samples, time_unit), dtype=float)

        return segment_buffers, time_axis


# Public API exports for this module
__all__ = ["ps6000a"]
