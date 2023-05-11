"""Nova PM SDS011 Reader module.

Device: https://www.amazon.com/SDS011-Quality-Detection-Conditioning-Monitor/dp/B07FSDMRR5

Spec: https://cdn.sparkfun.com/assets/parts/1/2/2/7/5/Laser_Dust_Sensor_Control_Protocol_V1.3.pdf
Spec: https://cdn-reichelt.de/documents/datenblatt/X200/SDS011-DATASHEET.pdf
"""

import time

import serial

from .responses import (
    QueryResponse,
    ReportingModeResponse,
    SleepWakeReadResponse,
    DeviceIdResponse,
    CheckFirmwareResponse,
    WorkingPeriodReadResponse,
)
from . import constants as con
from .exceptions import (
    IncompleteReadException,
    IncorrectCommandException,
    IncorrectCommandCodeException,
)

from typing import Protocol, Union, Optional, runtime_checkable


@runtime_checkable
class SerialLike(Protocol):
    """A serial-like device."""

    def read(self, size: int) -> bytes:
        """Read data from the device."""
        pass

    def write(self, data: bytes) -> Optional[int]:
        """Write data from the device."""
        pass

    def open(self) -> None:
        """Open a connection to the device."""
        pass

    def close(self) -> None:
        """Close a connection to the device."""
        pass


class SDS011Reader:
    """NOVA PM SDS011 Reader."""

    def __init__(self, ser_dev: Union[str, SerialLike], send_command_sleep: int = 1):
        """Create a basic device.

        This is mostly a low level implementation. For practical purposes, most users will want to use the
        SDS011QueryReader or SDS011ActiveReader.  This implementation would only be useful for very special cases, and
        serves as the base class for the other reader implementations anyways.

        Args:
            ser_dev: A path to a serial device, or an instance of serial.Serial.
            send_command_sleep: The number of seconds to sleep after sending a command to the device.
        """
        if isinstance(ser_dev, str):
            self.ser: SerialLike = serial.Serial(ser_dev, timeout=2)
        elif isinstance(ser_dev, SerialLike):
            self.ser = ser_dev
        else:
            raise AttributeError("ser_dev must be a string or Serial-like object.")
        self.send_command_sleep = send_command_sleep

    def request_data(self, device_id: bytes = con.ALL_SENSOR_ID) -> None:
        """Submit a request to the device to return pollutant data."""
        cmd = con.Command.QUERY.value + (b"\x00" * 12) + device_id
        self._send_command(cmd)

    def query_data(self) -> QueryResponse:
        """Query the device for pollutant data.

        Returns:
            Pollutant data from the device.

        """
        return QueryResponse(self._read_response())

    def request_reporting_mode(self, device_id: bytes = con.ALL_SENSOR_ID) -> None:
        """Submit a request to the device to return the current reporting mode."""
        cmd = (
            con.Command.SET_REPORTING_MODE.value
            + con.OperationType.QUERY.value
            + con.ReportingMode.ACTIVE.value
            + (b"\x00" * 10)
            + device_id
        )
        self._send_command(cmd)

    def query_reporting_mode(self) -> ReportingModeResponse:
        """Get the current reporting mode of the device.

        Returns:
            The current reporting mode of the device.

        """
        return ReportingModeResponse(self._read_response())

    def set_active_mode(self) -> None:
        """Set the reporting mode to active."""
        self._set_reporting_mode(con.ReportingMode.ACTIVE)
        try:
            self.query_reporting_mode()
        except IncorrectCommandException:
            pass
        except IncompleteReadException:
            pass

    def set_query_mode(self) -> None:
        """Set the reporting mode to querying."""
        self._set_reporting_mode(con.ReportingMode.QUERYING)
        try:
            self.query_reporting_mode()
        except IncorrectCommandException:
            pass
        except IncompleteReadException:
            pass
        except IncorrectCommandCodeException:
            pass

    def _set_reporting_mode(
        self, reporting_mode: con.ReportingMode, device_id: bytes = con.ALL_SENSOR_ID
    ) -> None:
        """Set the reporting mode, either ACTIVE or QUERYING.

        ACTIVE mode means the device will always return a Query command response when data is asked for, regardless of
        what command was sent.

        QUERYING mode means the device will only return responses to submitted commands, even for Query commands.

        ACTIVE mode is the factory default, but generally, QUERYING mode is preferrable for the longevity of the device.

        Args:
            reporting_mode: The reporting mode to set.
            device_id: The device ID to set reporting mode on.
        """
        cmd = (
            con.Command.SET_REPORTING_MODE.value
            + con.OperationType.SET_MODE.value
            + reporting_mode.value
            + (b"\x00" * 10)
            + device_id
        )
        self._send_command(cmd)
        # Switching between reporting modes is finicky; resetting the serial connection seems to address issues.
        self.ser.close()
        self.ser.open()

    def request_sleep_state(self, device_id: bytes = con.ALL_SENSOR_ID) -> None:
        """Submit a request to get the current sleep state."""
        cmd = (
            con.Command.SET_SLEEP.value
            + con.OperationType.QUERY.value
            + b"\x00"
            + (b"\x00" * 10)
            + device_id
        )
        self._send_command(cmd)

    def query_sleep_state(self) -> SleepWakeReadResponse:
        """Get the current sleep state.

        Returns:
            The current sleep state of the device.
        """
        return SleepWakeReadResponse(self._read_response())

    def set_sleep_state(
        self, sleep_state: con.SleepState, device_id: bytes = con.ALL_SENSOR_ID
    ) -> None:
        """Set the sleep state, either wake or sleep.

        Args:
            sleep_state: The sleep state to set, either SleepState.WAKE or SleepState.SLEEP
            device_id: The device ID to sleep or wake.
        """
        cmd = (
            con.Command.SET_SLEEP.value
            + con.OperationType.SET_MODE.value
            + sleep_state.value
            + (b"\x00" * 10)
            + device_id
        )
        self._send_command(cmd)

    def sleep(self, device_id: bytes = con.ALL_SENSOR_ID) -> None:
        """Put the device to sleep, turning off fan and diode."""
        self.set_sleep_state(con.SleepState.SLEEP, device_id)

    def wake(self, device_id: bytes = con.ALL_SENSOR_ID) -> None:
        """Wake the device up to start reading, turning on fan and diode."""
        self.set_sleep_state(con.SleepState.WAKE, device_id)

    def safe_wake(self, device_id: bytes = con.ALL_SENSOR_ID) -> None:
        """Wake the device up, if you don't know what mode its in.

        This operates as a fire-and-forget, even in query mode.  You shouldn't have to (and can't) query for a response
        after this command.
        """
        self.wake(device_id=device_id)
        # If we were in query mode, this would flush out the response.  If in active mode, this would be return read
        # data, but we don't care.
        self.ser.read(10)

    def set_device_id(
        self, device_id: bytes, target_device_id: bytes = con.ALL_SENSOR_ID
    ) -> None:
        """Set the device ID.

        Args:
            device_id: The new device ID to set.
            target_device_id: The target device ID to set the new device ID on.

        """
        if len(device_id) != 2 or len(target_device_id) != 2:
            raise AttributeError(
                f"Device ID must be 4 bytes, found {len(device_id)}, and {len(target_device_id)}"
            )
        cmd = (
            con.Command.SET_DEVICE_ID.value
            + (b"\x00" * 10)
            + device_id
            + target_device_id
        )
        self._send_command(cmd)

    def query_device_id(self) -> DeviceIdResponse:
        """Retrieve the current device ID.

        Returns:
            The current device ID.

        """
        return DeviceIdResponse(self._read_response())

    def request_working_period(self, device_id: bytes = con.ALL_SENSOR_ID) -> None:
        """Submit a request to retrieve the current working period for the device."""
        cmd = (
            con.Command.SET_WORKING_PERIOD.value
            + con.OperationType.QUERY.value
            + (b"\x00" * 11)
            + device_id
        )
        self._send_command(cmd)

    def query_working_period(self) -> WorkingPeriodReadResponse:
        """Retrieve the current working period for the device.

        Returns:
            The current working period set for the device.

        """
        return WorkingPeriodReadResponse(self._read_response())

    def set_working_period(
        self, working_period: int, device_id: bytes = con.ALL_SENSOR_ID
    ) -> None:
        """Set the working period for the device.

        Working period must be between 0 and 30.

        0 means the device will read continuously.
        Any value 1-30 means the device will wake and read for 30 seconds every n*60-30 seconds.

        Args:
            working_period: A value 0-30 to set as the new working period
            device_id: The device ID to set the working period for.
        """
        if 0 >= working_period >= 30:
            raise AttributeError("Working period must be between 0 and 30")
        cmd = (
            con.Command.SET_WORKING_PERIOD.value
            + con.OperationType.SET_MODE.value
            + bytes([working_period])
            + (b"\x00" * 10)
            + device_id
        )
        self._send_command(cmd)

    def request_firmware_version(self, device_id: bytes = con.ALL_SENSOR_ID) -> None:
        """Submit a request to retrieve the firmware version from the device."""
        cmd = con.Command.CHECK_FIRMWARE_VERSION.value + (b"\x00" * 12) + device_id
        self._send_command(cmd)

    def query_firmware_version(self) -> CheckFirmwareResponse:
        """Retrieve the firmware version from the device.

        Returns:
            The firmware version from the device.

        """
        return CheckFirmwareResponse(self._read_response())

    def _send_command(self, cmd: bytes) -> None:
        """Send a command to the device as bytes.

        Manages all the wrapper needed to send data to the device, including checksum.

        Args:
            cmd: The data payload to send to the device.

        Raises:
              AttributeError: If the command length is not equal to 15.

        """
        head = con.HEAD + con.SUBMIT_TYPE
        full_command = head + cmd + bytes([self._cmd_checksum(cmd)]) + con.TAIL
        if len(full_command) != 19:
            raise Exception(f"Command length must be 19, but was {len(full_command)}")
        self.ser.write(full_command)
        time.sleep(self.send_command_sleep)

    def _read_response(self) -> bytes:
        """Read a response from the device.

        Responses from the device should always be 10 bytes in length.

        Returns:
            Bytes from the device.

        Raises:
            IncompleteReadException: If the number of bytes read is not 10.

        """
        result = self.ser.read(10)
        if len(result) != 10:
            raise IncompleteReadException(len(result))
        return result

    def _cmd_checksum(self, data: bytes) -> int:
        """Generate a checksum for the data bytes of a command.

        Args:
            data: The data bytes of write command.

        Returns:
            An integer checksum of the bytes passed.

        """
        if len(data) != 15:
            raise AttributeError("Invalid checksum length.")
        return sum(d for d in data) % 256


class SDS011QueryReader:
    """Reader working in query mode."""

    def __init__(self, ser_dev: Union[str, SerialLike], send_command_sleep: int = 1):
        """Create a reader which operates exclusively in query mode.

        Args:
            ser_dev: A path to a serial device, or an instance of serial.Serial.
            send_command_sleep: The number of seconds to sleep after sending a command to the device.
        """
        self.base_reader = SDS011Reader(
            ser_dev=ser_dev, send_command_sleep=send_command_sleep
        )
        self.base_reader.safe_wake(device_id=con.ALL_SENSOR_ID)
        self.base_reader.set_query_mode()

    def query(self, device_id: bytes = con.ALL_SENSOR_ID) -> QueryResponse:
        """Query the device for pollutant data.

        Args:
            device_id: The device ID to get pollutant data for.

        Returns:
            The latest pollutant data.

        """
        self.base_reader.request_data(device_id=device_id)
        return self.base_reader.query_data()

    def get_reporting_mode(
        self, device_id: bytes = con.ALL_SENSOR_ID
    ) -> ReportingModeResponse:
        """Get the current reporting mode of the device.

        Args:
            device_id: The device ID to get the reporting mode for.

        Returns:
            The current reporting mode of the device.

        """
        self.base_reader.request_reporting_mode(device_id=device_id)
        return self.base_reader.query_reporting_mode()

    def get_sleep_state(
        self, device_id: bytes = con.ALL_SENSOR_ID
    ) -> SleepWakeReadResponse:
        """Get the current sleep state.

        Args:
            device_id: The device ID to get the sleep state for.

        Returns:
            The current sleep state of the device.
        """
        self.base_reader.request_sleep_state(device_id=device_id)
        return self.base_reader.query_sleep_state()

    def sleep(self, device_id: bytes = con.ALL_SENSOR_ID) -> SleepWakeReadResponse:
        """Put the device to sleep, turning off fan and diode.

        Args:
            device_id: The device ID to put to sleep.

        Returns:
            The new sleep state of the device.
        """
        self.base_reader.sleep(device_id=device_id)
        return self.base_reader.query_sleep_state()

    def wake(self, device_id: bytes = con.ALL_SENSOR_ID) -> SleepWakeReadResponse:
        """Wake the device up to start reading, turning on the fan and diode.

        Args:
            device_id: The device ID to wake up.


        Returns:
            The new sleep state of the device.
        """
        self.base_reader.wake(device_id=device_id)
        return self.base_reader.query_sleep_state()

    def set_device_id(
        self, device_id: bytes, target_device_id: bytes = con.ALL_SENSOR_ID
    ) -> DeviceIdResponse:
        """Set the device ID.

        Args:
            device_id: The new, 4-byte device ID to set.
            target_device_id: The target device ID.

        Returns:
            A response with the new device ID.
        """
        self.base_reader.set_device_id(
            device_id=device_id, target_device_id=target_device_id
        )
        return self.base_reader.query_device_id()

    def get_working_period(
        self, device_id: bytes = con.ALL_SENSOR_ID
    ) -> WorkingPeriodReadResponse:
        """Retrieve the current working period for the device.

        Args:
            device_id: The device ID to get the working period for.

        Returns:
            A response with the current working period.
        """
        self.base_reader.request_working_period(device_id=device_id)
        return self.base_reader.query_working_period()

    def set_working_period(
        self, working_period: int, device_id: bytes = con.ALL_SENSOR_ID
    ) -> WorkingPeriodReadResponse:
        """Set the working period for the device.

        Working period must be between 0 and 30.

        0 means the device will read continuously.
        Any value 1-30 means the device will wake and read for 30 seconds every n*60-30 seconds.

        Args:
            working_period: A value 0-30 to set as the new working period
            device_id: The device ID to set the working period for.

        Returns:
            A response with the new working period

        """
        self.base_reader.set_working_period(
            working_period=working_period, device_id=device_id
        )
        return self.base_reader.query_working_period()

    def get_firmware_version(
        self, device_id: bytes = con.ALL_SENSOR_ID
    ) -> CheckFirmwareResponse:
        """Retrieve the firmware version from the device.

        Args:
            device_id: The device ID to retrieve firmware version for.

        Returns:
            The firmware version of the device

        """
        self.base_reader.request_firmware_version(device_id=device_id)
        return self.base_reader.query_firmware_version()


class SDS011ActiveReader:
    """Active Mode Reader.

    Use with caution! Active mode is unpredictable.  Query mode is much preferred.
    """

    def __init__(self, ser_dev: Union[str, SerialLike], send_command_sleep: int = 2):
        """Create a reader which operates exclusively in active mode.

        Args:
            ser_dev: A path to a serial device, or an instance of serial.Serial.
            send_command_sleep: The number of seconds to sleep after sending a command to the device.
        """
        self.base_reader = SDS011Reader(
            ser_dev=ser_dev, send_command_sleep=send_command_sleep
        )
        self.ser_dev: SerialLike = self.base_reader.ser
        self.base_reader.safe_wake()
        self.base_reader.set_active_mode()

    def query(self) -> QueryResponse:
        """Query the device for pollutant data.

        Returns:
            The latest pollutant data.

        """
        return self.base_reader.query_data()

    def sleep(self, device_id: bytes = con.ALL_SENSOR_ID) -> None:
        """Put the device to sleep, turning off fan and diode.

        Args:
            device_id: The device ID to put to sleep.
        """
        self.base_reader.sleep(device_id)

        # Sleep seems to behave very strangely in active mode.  It continually outputs data for old commands for quite
        # a while before eventually having nothing to report.  This forces it to "drain" whatever it was doing before
        # returning, but also feels quite dangerous.
        while len(self.ser_dev.read(10)) == 10:
            pass

    def wake(self, device_id: bytes = con.ALL_SENSOR_ID) -> None:
        """Wake the device up to start reading, turning on the fan and diode.

        Args:
            device_id: The device ID to wake up.
        """
        self.base_reader.wake(device_id)
        self.ser_dev.read(10)

    def set_device_id(
        self, device_id: bytes, target_device_id: bytes = con.ALL_SENSOR_ID
    ) -> None:
        """Set the device ID.

        Args:
            device_id: The new, 4-byte device ID to set.
            target_device_id: The target device ID.

        Returns:
            A response with the new device ID.
        """
        self.base_reader.set_device_id(device_id, target_device_id)
        self.ser_dev.read(10)

    def set_working_period(
        self, working_period: int, device_id: bytes = con.ALL_SENSOR_ID
    ) -> None:
        """Set the working period for the device.

        Working period must be between 0 and 30.

        0 means the device will read continuously.
        Any value 1-30 means the device will wake and read for 30 seconds every n*60-30 seconds.

        Args:
            working_period: A value 0-30 to set as the new working period
            device_id: The device ID to set the working period for.

        Returns:
            A response with the new working period
        """
        self.base_reader.set_working_period(working_period, device_id)
        self.ser_dev.read(10)
