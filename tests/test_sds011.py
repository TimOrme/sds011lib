"""Tests for SDS011 readers.

Note that tests can run against both an emulated software reader, and a hardware device.  The emulator runs
significantly faster, but obviously isn't 100% guaranteed to behave exactly like a real device.

If you have a device attached, and want to run tests against it, you can set an environment variable with your test run,
like:

TEST_DEVICE=/dev/ttyUSB0 pytest tests/

If `TEST_DEVICE` isn't set, tests will only run against the emulator.
"""
import pytest

from sds011lib import SDS011Reader, SDS011ActiveReader, SDS011QueryReader
from sds011lib._constants import ReportingMode, SleepState
from sds011lib.exceptions import (
    IncompleteReadException,
    ChecksumFailedException,
    IncorrectWrapperException,
    MissingResponseException,
)
from .serial_emulator import Sds011SerialEmulator
from typing import Generator, List
from unittest.mock import Mock, patch
from serial import Serial
import os


def pm25_in_range(pm25: float) -> bool:
    return 999.9 >= pm25 >= 0.0


def pm10_in_range(pm10: float) -> bool:
    return 999.9 >= pm10 >= 0.0


def get_reader_fixtures() -> List[str]:
    fixtures = ["emulated_reader"]
    if os.getenv("TEST_DEVICE", None):
        fixtures.append("integrated_reader")
    return fixtures


class TestBaseReader:
    @pytest.fixture
    def reader(self, request):  # type: ignore
        return request.getfixturevalue(request.param)

    @pytest.fixture
    def integrated_reader(self) -> Generator[SDS011Reader, None, None]:
        # If you want to run these tests an integration you can replace the emulator here with a real serial device.
        ser_dev = Serial(os.getenv("TEST_DEVICE"), timeout=2, baudrate=9600)
        reader = SDS011Reader(ser_dev=ser_dev)

        # ser_dev = Sds011SerialEmulator()
        # reader = SDS011Reader(ser_dev=ser_dev, send_command_sleep=0)

        reader.wake()
        reader.set_active_mode()
        reader.set_working_period(0)

        # Clear everything so the reader acts as if the above commands weren't sent.
        ser_dev.reset_input_buffer()

        yield reader
        # Sleep the reader at the end so its not left on.
        reader.sleep()
        ser_dev.close()

    @pytest.fixture
    def emulated_reader(self) -> SDS011Reader:
        ser_dev = Sds011SerialEmulator()
        reader = SDS011Reader(ser_dev=ser_dev, send_command_sleep=0)
        return reader

    @patch("serial.Serial")
    def test_string_constructor(self, serial_constructor: Mock) -> None:
        # Test that we can construct a serial device from a string.
        SDS011Reader("/dev/some_fake_dev")
        serial_constructor.assert_called_with("/dev/some_fake_dev", timeout=2)

    @pytest.mark.parametrize("reader", get_reader_fixtures(), indirect=True)
    def test_hammer_reporting_mode(self, reader: SDS011Reader) -> None:
        # Switch the modes
        reader.set_query_mode()
        reader.set_active_mode()

        # Set again in active mode
        reader.set_active_mode()

        # set it in query mode twice
        reader.set_query_mode()
        reader.set_query_mode()

        reader.request_reporting_mode()
        assert reader.query_reporting_mode().state == ReportingMode.QUERYING

    @pytest.mark.parametrize("reader", get_reader_fixtures(), indirect=True)
    def test_hammer_sleep_query_mode(self, reader: SDS011Reader) -> None:
        reader.set_query_mode()
        reader.sleep()
        result = reader.query_sleep_state()
        assert result.state == SleepState.SLEEP

        reader.wake()
        reader.request_sleep_state()
        assert reader.query_sleep_state().state == SleepState.WAKE
        reader.set_query_mode()
        reader.request_sleep_state()
        result = reader.query_sleep_state()
        assert result.state == SleepState.WAKE

    @pytest.mark.parametrize("reader", get_reader_fixtures(), indirect=True)
    def test_hammer_sleep_active_mode(self, reader: SDS011Reader) -> None:
        reader.set_active_mode()
        reader.sleep()

        reader.wake()
        reader.set_active_mode()
        result = reader.query_data()
        assert result.pm25 > 0.0

    @pytest.mark.parametrize("reader", get_reader_fixtures(), indirect=True)
    def test_queries_in_sleep_mode_are_incomplete(self, reader: SDS011Reader) -> None:
        # Device can't be asked anything in sleep mode.
        reader.set_query_mode()
        reader.sleep()
        assert reader.query_sleep_state().state == SleepState.SLEEP

        reader.request_reporting_mode()
        with pytest.raises(IncompleteReadException):
            reader.query_reporting_mode()

        reader.request_working_period()
        with pytest.raises(IncompleteReadException):
            reader.query_working_period()

    @pytest.mark.parametrize("reader", get_reader_fixtures(), indirect=True)
    def test_values_changed_sleep_mode_arent_persisted(
        self, reader: SDS011Reader
    ) -> None:
        # Device can't set values while its asleep.
        reader.set_query_mode()
        reader.sleep()
        assert reader.query_sleep_state().state == SleepState.SLEEP

        reader.set_working_period(20)

        reader.wake()
        assert reader.query_sleep_state().state == SleepState.WAKE

        reader.request_working_period()
        assert reader.query_working_period().interval == 0

    @pytest.mark.parametrize("reader", get_reader_fixtures(), indirect=True)
    def test_buffer_is_first_command(self, reader: SDS011Reader) -> None:
        reader.set_query_mode()

        # In query mode, once a command has been issued, subsequent commands should be effectively ignored, until the
        # buffer is read.
        reader.request_sleep_state()
        reader.request_firmware_version()
        reader.request_working_period()

        # We should still only get sleep state since its first
        result = reader.query_sleep_state()
        assert result.state == SleepState.WAKE

    @pytest.mark.parametrize("reader", get_reader_fixtures(), indirect=True)
    def test_get_reporting_mode_query(self, reader: SDS011Reader) -> None:
        reader.set_query_mode()
        reader.request_reporting_mode()
        result = reader.query_reporting_mode()
        assert result.state == ReportingMode.QUERYING

    @pytest.mark.parametrize("reader", get_reader_fixtures(), indirect=True)
    def test_get_reporting_mode_active(self, reader: SDS011Reader) -> None:
        reader.set_active_mode()
        result = reader.query_reporting_mode()
        assert result.state == ReportingMode.ACTIVE

    @pytest.mark.parametrize("reader", get_reader_fixtures(), indirect=True)
    def test_query_active_mode(self, reader: SDS011Reader) -> None:
        reader.set_active_mode()
        result = reader.query_data()
        assert pm25_in_range(result.pm25)
        assert pm10_in_range(result.pm10)

    @pytest.mark.parametrize("reader", get_reader_fixtures(), indirect=True)
    def test_query_query_mode(self, reader: SDS011Reader) -> None:
        reader.set_query_mode()
        reader.request_data()
        result = reader.query_data()
        assert pm25_in_range(result.pm25)
        assert pm10_in_range(result.pm10)

    def test_query_emulated(self) -> None:
        # Since the emulator always returns the same values, this lets us assert that the result is an exact number,
        # instead of a range.  Its possible that we might have a bug if all we do is check range, since we might be
        # checking the wrong byte data.
        ser_dev = Sds011SerialEmulator()
        reader = SDS011Reader(ser_dev=ser_dev, send_command_sleep=0)
        reader.set_query_mode()
        reader.request_data()
        result = reader.query_data()
        assert result.pm25 == 432.5
        assert result.pm10 == 531.1

    @pytest.mark.parametrize("reader", get_reader_fixtures(), indirect=True)
    def test_set_device_id_query_mode(self, reader: SDS011Reader) -> None:
        new_device_id = b"\xbb\xaa"
        reader.set_query_mode()
        reader.set_device_id(new_device_id)
        result = reader.query_device_id()
        assert result.device_id == new_device_id

        # Verify other commands also report correct ID
        reader.request_data()
        result2 = reader.query_data()
        assert result2.device_id == new_device_id

    @pytest.mark.parametrize("reader", get_reader_fixtures(), indirect=True)
    def test_set_device_id_wrong_size(self, reader: SDS011Reader) -> None:
        reader.set_query_mode()
        with pytest.raises(AttributeError):
            reader.set_device_id(b"\xbb\xaa\x42")

        with pytest.raises(AttributeError):
            reader.set_device_id(b"\xbb")

    @pytest.mark.parametrize("reader", get_reader_fixtures(), indirect=True)
    def test_sleep_query_mode(self, reader: SDS011Reader) -> None:
        reader.set_query_mode()
        reader.sleep()
        result = reader.query_sleep_state()
        assert result.state == SleepState.SLEEP

    @pytest.mark.parametrize("reader", get_reader_fixtures(), indirect=True)
    def test_sleep_active_mode(self, reader: SDS011Reader) -> None:
        reader.set_active_mode()
        reader.sleep()

    @pytest.mark.parametrize("reader", get_reader_fixtures(), indirect=True)
    def test_wake_query_mode(self, reader: SDS011Reader) -> None:
        reader.set_query_mode()
        reader.wake()
        result = reader.query_sleep_state()
        assert result.state == SleepState.WAKE

    @pytest.mark.parametrize("reader", get_reader_fixtures(), indirect=True)
    def test_wake_active_mode(self, reader: SDS011Reader) -> None:
        reader.set_active_mode()
        reader.wake()

    @pytest.mark.parametrize("reader", get_reader_fixtures(), indirect=True)
    def test_get_sleep_state_query_mode(self, reader: SDS011Reader) -> None:
        reader.set_query_mode()
        reader.wake()
        result = reader.query_sleep_state()
        assert result.state == SleepState.WAKE

    @pytest.mark.parametrize("reader", get_reader_fixtures(), indirect=True)
    def test_get_sleep_state_active_mode(self, reader: SDS011Reader) -> None:
        reader.set_active_mode()
        reader.wake()
        result = reader.query_sleep_state()
        assert result.state == SleepState.WAKE

    @pytest.mark.parametrize("reader", get_reader_fixtures(), indirect=True)
    def test_set_working_period_query_mode(self, reader: SDS011Reader) -> None:
        reader.set_query_mode()
        reader.set_working_period(10)
        result = reader.query_working_period()
        assert result.interval == 10

    @pytest.mark.parametrize("reader", get_reader_fixtures(), indirect=True)
    def test_set_working_period_active_mode(self, reader: SDS011Reader) -> None:
        reader.set_active_mode()
        reader.set_working_period(10)

    @pytest.mark.parametrize("reader", get_reader_fixtures(), indirect=True)
    def test_set_working_period_invalid_setting(self, reader: SDS011Reader) -> None:
        reader.set_query_mode()
        with pytest.raises(AttributeError):
            reader.set_working_period(40)

        with pytest.raises(AttributeError):
            reader.set_working_period(-1)

    @pytest.mark.parametrize("reader", get_reader_fixtures(), indirect=True)
    def test_get_working_period_query_mode(self, reader: SDS011Reader) -> None:
        reader.set_query_mode()
        reader.set_working_period(10)
        result = reader.query_working_period()
        assert result.interval == 10

    @pytest.mark.parametrize("reader", get_reader_fixtures(), indirect=True)
    def test_get_working_period_active_mode(self, reader: SDS011Reader) -> None:
        reader.set_active_mode()
        reader.set_working_period(10)
        result = reader.query_working_period()
        assert result.interval == 10

    @pytest.mark.parametrize("reader", get_reader_fixtures(), indirect=True)
    def test_get_firmware_version_query_mode(self, reader: SDS011Reader) -> None:
        reader.set_query_mode()
        reader.request_firmware_version()
        result = reader.query_firmware_version()
        assert 99 >= result.year >= 0
        assert 12 >= result.month >= 1
        assert 31 >= result.day >= 1

    @pytest.mark.parametrize("reader", get_reader_fixtures(), indirect=True)
    def test_get_firmware_version_active_mode(self, reader: SDS011Reader) -> None:
        reader.set_active_mode()
        reader.request_firmware_version()
        result = reader.query_firmware_version()
        assert 99 >= result.year >= 0
        assert 12 >= result.month >= 1
        assert 31 >= result.day >= 1

    @pytest.mark.parametrize("reader", get_reader_fixtures(), indirect=True)
    def test_throws_if_missing_response(self, reader: SDS011Reader) -> None:
        # Set query mode just to make it easier.
        reader.set_query_mode()
        reader.request_reporting_mode()
        # flush the device just in case stuff from active mode is leftover
        reader.ser.close()
        reader.ser.open()
        # Set the max loop to three
        reader.max_loop_count = 3

        # Send 3 commands to set device ID, filling up the response buffer.
        for i in range(0, 4):
            reader.set_device_id(b"\xaa\xbb")

        # Send a data command
        reader.request_data()

        # Command should be 4 back.
        with pytest.raises(MissingResponseException):
            reader.query_data()

    def test_raises_if_not_serial_or_string(self) -> None:
        with pytest.raises(AttributeError):
            SDS011Reader(1234)  # type: ignore

    def test_bad_checksum(self) -> None:
        ser_dev = Mock(spec=Serial)
        ser_dev.read.side_effect = [b"\xaa\x01\x01\x01\x01\x01\x01\x01\x03\xab"]
        reader = SDS011Reader(ser_dev=ser_dev, send_command_sleep=0)

        with pytest.raises(ChecksumFailedException):
            reader.query_data()

    def test_bad_wrapper_head(self) -> None:
        ser_dev = Mock(spec=Serial)
        # Set the head to be the wrong value
        ser_dev.read.side_effect = [b"\xab\x01\x01\x01\x01\x01\x01\x01\x03\xab"]
        reader = SDS011Reader(ser_dev=ser_dev, send_command_sleep=0)

        with pytest.raises(IncorrectWrapperException):
            reader.query_data()

    def test_bad_wrapper_tail(self) -> None:
        ser_dev = Mock(spec=Serial)
        # Set the tail to be the wrong value
        ser_dev.read.side_effect = [b"\xaa\x01\x01\x01\x01\x01\x01\x01\x03\xac"]
        reader = SDS011Reader(ser_dev=ser_dev, send_command_sleep=0)

        with pytest.raises(IncorrectWrapperException):
            reader.query_data()

    def test_incomplete_read(self) -> None:
        ser_dev = Mock(spec=Serial)
        # Give back less than 10 bytes
        ser_dev.read.side_effect = [b"\xaa\x01\x01\x01\x01\x01"]
        reader = SDS011Reader(ser_dev=ser_dev, send_command_sleep=0)

        with pytest.raises(IncompleteReadException):
            reader.query_data()

    def test_set_active_mode_ignores_incomplete_reads(self) -> None:
        ser_dev = Mock(spec=Serial)
        # Give back less than 10 bytes
        ser_dev.read.side_effect = [b"\xaa\x01\x01\x01\x01\x01"]
        reader = SDS011Reader(ser_dev=ser_dev, send_command_sleep=0)

        try:
            reader.set_active_mode()
        except Exception:
            pytest.fail("Unexpected exception")

    def test_set_query_mode_ignores_incomplete_reads(self) -> None:
        ser_dev = Mock(spec=Serial)
        # Give back less than 10 bytes
        ser_dev.read.side_effect = [b"\xaa\x01\x01\x01\x01\x01"]
        reader = SDS011Reader(ser_dev=ser_dev, send_command_sleep=0)

        try:
            reader.set_query_mode()
        except Exception:
            pytest.fail("Unexpected exception")

    def test_set_query_mode_ignores_incorrect_command(self) -> None:
        ser_dev = Mock(spec=Serial)
        # Give a query mode command instead
        ser_dev.read.side_effect = [b"\xaa\xc0\x01\x01\x01\x01\x01\x01\x06\xab"]
        reader = SDS011Reader(ser_dev=ser_dev, send_command_sleep=0)

        try:
            reader.set_query_mode()
        except Exception:
            pytest.fail("Unexpected exception")


class TestActiveModeReader:
    @pytest.fixture
    def reader(self, request):  # type: ignore
        return request.getfixturevalue(request.param)

    @pytest.fixture
    def integrated_reader(self) -> Generator[SDS011ActiveReader, None, None]:
        # If you want to run these tests an integration you can replace the emulator here with a real serial device.
        ser_dev = Serial(os.getenv("TEST_DEVICE"), timeout=2, baudrate=9600)
        reader = SDS011ActiveReader(ser_dev=ser_dev, send_command_sleep=5)

        # ser_dev = Sds011SerialEmulator()
        # reader = SDS011ActiveReader(ser_dev=ser_dev, send_command_sleep=0)
        reader.set_working_period(0)
        reader.set_device_id(b"\xaa\xaa")

        yield reader
        try:
            # Sleep the reader at the end so its not left on.
            reader.sleep()
        except IncompleteReadException:
            # Can't re-sleep if were already asleep.
            pass
        ser_dev.close()

    @pytest.fixture
    def emulated_reader(self) -> SDS011ActiveReader:
        ser_dev = Sds011SerialEmulator()
        reader = SDS011ActiveReader(ser_dev=ser_dev, send_command_sleep=0)
        return reader

    @pytest.mark.parametrize("reader", get_reader_fixtures(), indirect=True)
    def test_query(self, reader: SDS011ActiveReader) -> None:
        result = reader.query()
        assert pm25_in_range(result.pm25)
        assert pm10_in_range(result.pm10)

    @pytest.mark.parametrize("reader", get_reader_fixtures(), indirect=True)
    def test_query_sleep_mode(self, reader: SDS011ActiveReader) -> None:
        reader.sleep()

        with pytest.raises(IncompleteReadException):
            reader.query()

    @pytest.mark.parametrize("reader", get_reader_fixtures(), indirect=True)
    def test_wake(self, reader: SDS011ActiveReader) -> None:
        reader.sleep()
        with pytest.raises(IncompleteReadException):
            reader.query()
        reader.wake()

        # Make sure we can read again.
        result = reader.query()
        assert pm25_in_range(result.pm25)
        assert pm10_in_range(result.pm10)

    @pytest.mark.parametrize("reader", get_reader_fixtures(), indirect=True)
    def test_set_working_period(self, reader: SDS011ActiveReader) -> None:
        result = reader.set_working_period(20)
        assert result.interval == 20

    @pytest.mark.parametrize("reader", get_reader_fixtures(), indirect=True)
    def test_set_device_id(self, reader: SDS011ActiveReader) -> None:
        result = reader.set_device_id(b"\x12\x23")

        assert result.device_id == b"\x12\x23"

        # Check that other response have the value as well.
        result2 = reader.query()
        assert result2.device_id == b"\x12\x23"


class TestQueryModeReader:
    @pytest.fixture
    def reader(self, request):  # type: ignore
        return request.getfixturevalue(request.param)

    @pytest.fixture
    def integrated_reader(self) -> Generator[SDS011QueryReader, None, None]:
        # If you want to run these tests an integration you can replace the emulator here with a real serial device.
        ser_dev = Serial(os.getenv("TEST_DEVICE"), timeout=2, baudrate=9600)
        reader = SDS011QueryReader(ser_dev=ser_dev)

        # ser_dev = Sds011SerialEmulator()
        # reader = SDS011QueryReader(ser_dev=ser_dev, send_command_sleep=0)
        reader.set_working_period(0)

        yield reader
        # Sleep the reader at the end so its not left on.
        reader.base_reader.sleep()
        ser_dev.close()

    @pytest.fixture
    def emulated_reader(self) -> SDS011QueryReader:
        ser_dev = Sds011SerialEmulator()
        reader = SDS011QueryReader(ser_dev=ser_dev, send_command_sleep=0)
        return reader

    @pytest.mark.parametrize("reader", get_reader_fixtures(), indirect=True)
    def test_query(self, reader: SDS011QueryReader) -> None:
        result = reader.query()
        assert pm25_in_range(result.pm25)
        assert pm10_in_range(result.pm10)

    @pytest.mark.parametrize("reader", get_reader_fixtures(), indirect=True)
    def test_query_sleep_mode(self, reader: SDS011QueryReader) -> None:
        reader.sleep()

        with pytest.raises(IncompleteReadException):
            reader.query()

    @pytest.mark.parametrize("reader", get_reader_fixtures(), indirect=True)
    def test_wake(self, reader: SDS011QueryReader) -> None:
        reader.sleep()
        with pytest.raises(IncompleteReadException):
            reader.query()
        result = reader.wake()
        assert result.state == SleepState.WAKE

        result2 = reader.query()
        assert pm25_in_range(result2.pm25)
        assert pm10_in_range(result2.pm10)

    @pytest.mark.parametrize("reader", get_reader_fixtures(), indirect=True)
    def test_get_sleep_state(self, reader: SDS011QueryReader) -> None:
        result = reader.sleep()
        assert result.state == SleepState.SLEEP

        result = reader.wake()
        assert result.state == SleepState.WAKE

        result = reader.get_sleep_state()
        assert result.state == SleepState.WAKE

        # Make sure we can read again.
        result2 = reader.query()
        assert pm25_in_range(result2.pm25)
        assert pm10_in_range(result2.pm10)

    @pytest.mark.parametrize("reader", get_reader_fixtures(), indirect=True)
    def test_get_reporting_mode(self, reader: SDS011QueryReader) -> None:
        result = reader.get_reporting_mode()
        assert result.state == ReportingMode.QUERYING

    @pytest.mark.parametrize("reader", get_reader_fixtures(), indirect=True)
    def test_set_working_period(self, reader: SDS011QueryReader) -> None:
        result = reader.set_working_period(20)
        assert result.interval == 20

    @pytest.mark.parametrize("reader", get_reader_fixtures(), indirect=True)
    def test_get_working_period(self, reader: SDS011QueryReader) -> None:
        reader.set_working_period(20)
        result = reader.get_working_period()
        assert result.interval == 20

    @pytest.mark.parametrize("reader", get_reader_fixtures(), indirect=True)
    def test_set_device_id(self, reader: SDS011QueryReader) -> None:
        result = reader.set_device_id(b"\x12\x23")
        assert result.device_id == b"\x12\x23"

        # We can't really do much here to validate that this is working.  Just ensure that we can still query after.
        result2 = reader.query()
        assert result2.device_id == b"\x12\x23"

    @pytest.mark.parametrize("reader", get_reader_fixtures(), indirect=True)
    def test_get_firmware_version(self, reader: SDS011QueryReader) -> None:
        result = reader.get_firmware_version()
        assert 99 >= result.year >= 0
        assert 12 >= result.month >= 1
        assert 31 >= result.day >= 1
