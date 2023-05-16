from sds011lib._constants import (
    HEAD,
    TAIL,
    Command,
    ReportingMode,
    OperationType,
    ResponseType,
    SleepState,
)
from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass(frozen=True)
class WriteData:
    """Simple wrapper for parsed write data."""

    raw_data: bytes
    raw_body_data: bytes
    command: Command


class Sds011SerialEmulator:
    """Emulated SDS011 Serial Port.

    Behaves like the device itself, except is a bit more predictable in ACTIVE mode.
    """

    def __init__(self) -> None:
        """Create the emulator.

        Initializes to factory defaults.
        """
        super().__init__()
        self.response_buffer = b""
        self.query_mode = ReportingMode.ACTIVE
        self.device_id = b"\x01\x01"
        self.sleep_state = SleepState.WAKE
        self.working_period = bytes([0])
        self.firmware_year = bytes([1])
        self.firmware_month = bytes([2])
        self.firmware_day = bytes([3])
        self.last_command_time: datetime = datetime.now()

    def open(self) -> None:
        """No-op open."""
        pass

    def close(self) -> None:
        """Resets response buffer."""
        self.response_buffer = b""

    def read(self, size: int = 1) -> bytes:
        """Read from the emulator."""
        if (
            len(self.response_buffer) == 0
            and self.query_mode == ReportingMode.ACTIVE
            and self.sleep_state == SleepState.WAKE
        ):
            # If were in active mode, and there's nothing else in there, throw some fake reads in.
            self._inject_active_mode_reads()

        response = self.response_buffer[0:size]
        self.response_buffer = self.response_buffer[size:]
        return response

    def _generate_read(self, response_type: ResponseType, cmd: bytes) -> bytes:
        """Generate a read command, with wrapper and checksum."""
        cmd_and_id = cmd + self.device_id
        return (
            HEAD + response_type.value + cmd_and_id + read_checksum(cmd_and_id) + TAIL
        )

    def write(self, data: bytes) -> Optional[int]:
        """Write to the emulator."""
        last_write = parse_write_data(data)

        if (
            self.sleep_state == SleepState.SLEEP
            and last_write.command != Command.SET_SLEEP
        ):
            # Device ignores commands in sleep mode, unless its a sleep command
            return len(data)

        if last_write.command == Command.SET_REPORTING_MODE:
            operation_type = OperationType(last_write.raw_body_data[1:2])
            if operation_type == OperationType.SET_MODE:
                new_reporting_mode = ReportingMode(last_write.raw_body_data[2:3])
                self._add_to_response_buffer(
                    self._get_reporting_mode_response(
                        new_reporting_mode, operation_type
                    )
                )
                self.query_mode = new_reporting_mode
            else:
                self._add_to_response_buffer(
                    self._get_reporting_mode_response(self.query_mode, operation_type)
                )
        elif last_write.command == Command.QUERY:
            self._add_to_response_buffer(self._get_query_response())
        elif last_write.command == Command.SET_DEVICE_ID:
            self.device_id = last_write.raw_body_data[11:13]
            self._add_to_response_buffer(self._get_device_id_response())
        elif last_write.command == Command.SET_SLEEP:
            operation_type = OperationType(last_write.raw_body_data[1:2])
            if operation_type == OperationType.SET_MODE:
                new_sleep_state = SleepState(last_write.raw_body_data[2:3])
                self._add_to_response_buffer(
                    self._set_sleep_response(new_sleep_state, operation_type)
                )
                self.sleep_state = new_sleep_state
            else:
                self._add_to_response_buffer(
                    self._set_sleep_response(self.sleep_state, operation_type)
                )
        elif last_write.command == Command.SET_WORKING_PERIOD:
            operation_type = OperationType(last_write.raw_body_data[1:2])
            if operation_type == OperationType.SET_MODE:
                new_working_period = last_write.raw_body_data[2:3]
                self._add_to_response_buffer(
                    self._get_working_period_response(
                        new_working_period, operation_type
                    )
                )
                self.working_period = new_working_period
            else:
                self._add_to_response_buffer(
                    self._get_working_period_response(
                        self.working_period, operation_type
                    )
                )
        elif last_write.command == Command.CHECK_FIRMWARE_VERSION:
            self._add_to_response_buffer(self._check_firmware_response())
        return len(data)

    def _get_query_response(self) -> bytes:
        return self._generate_read(ResponseType.QUERY_RESPONSE, b"\xE5\x10\xBF\x14")

    def _add_to_response_buffer(self, data: bytes) -> None:
        if self.query_mode == ReportingMode.ACTIVE:
            self._inject_active_mode_reads()
        self.response_buffer += data

    def _inject_active_mode_reads(self) -> None:
        """Inject reads when were in active mode.

        Always injects at least one read, but tries to inject more if there hasn't been a command in a while.
        """
        now = datetime.now()
        seconds_since_last_command = (now - self.last_command_time).seconds
        for x in range(0, max(seconds_since_last_command, 1)):
            self.response_buffer += self._get_query_response()

    def _get_reporting_mode_response(
        self, reporting_mode: ReportingMode, operation_type: OperationType
    ) -> bytes:
        return self._generate_read(
            ResponseType.GENERAL_RESPONSE,
            Command.SET_REPORTING_MODE.value
            + operation_type.value
            + reporting_mode.value
            + b"\x00",
        )

    def _get_device_id_response(self) -> bytes:
        return self._generate_read(
            ResponseType.GENERAL_RESPONSE, Command.SET_DEVICE_ID.value + (b"\x00" * 3)
        )

    def _set_sleep_response(
        self, sleep_state: SleepState, operation_type: OperationType
    ) -> bytes:
        return self._generate_read(
            ResponseType.GENERAL_RESPONSE,
            Command.SET_SLEEP.value
            + operation_type.value
            + sleep_state.value
            + b"\x00",
        )

    def _get_working_period_response(
        self, working_period: bytes, operation_type: OperationType
    ) -> bytes:
        return self._generate_read(
            ResponseType.GENERAL_RESPONSE,
            Command.SET_WORKING_PERIOD.value
            + operation_type.value
            + working_period
            + b"\x00",
        )

    def _check_firmware_response(self) -> bytes:
        return self._generate_read(
            ResponseType.GENERAL_RESPONSE,
            Command.CHECK_FIRMWARE_VERSION.value
            + self.firmware_year
            + self.firmware_month
            + self.firmware_day,
        )


def read_checksum(data: bytes) -> bytes:
    """Generate a checksum for the data bytes of a command."""
    if len(data) != 6:
        raise AttributeError("Invalid checksum length.")
    return bytes([sum(d for d in data) % 256])


def parse_write_data(data: bytes) -> WriteData:
    """Parse write data from the emulator into a neater wrapper."""
    if len(data) != 19:
        raise AttributeError("Data is wrong size.")
    return WriteData(
        raw_data=data, raw_body_data=data[2:15], command=Command(data[2:3])
    )
