"""Response objects for SDS011.

Creates and validates typed classes from binary responses from the device.
"""
from .constants import (
    HEAD,
    TAIL,
    Command,
    ResponseType,
    SleepState,
    OperationType,
    ReportingMode,
)
from .exceptions import (
    ChecksumFailedException,
    IncorrectCommandException,
    IncorrectCommandCodeException,
    IncorrectWrapperException,
    IncompleteReadException,
)


class ReadResponse:
    """Generic read response object for responses from SDS011.

    Attributes:
        head: The header bytes from the response
        cmd_id: The command ID from the response
        data: The data packet bytes from the response.
        device_id: The device ID from the response
        checksum: The returned checksum for the response
        tail: The tail bytes from the response
        expected_command_code: The expected command code
        expected_response_type: The expected response type, either GENERAL or QUERY.
    """

    def __init__(
        self,
        data: bytes,
        command_code: Command,
        response_type: ResponseType = ResponseType.GENERAL_RESPONSE,
    ):
        """Create a read response."""
        if len(data) != 10:
            raise IncompleteReadException()

        self.head: bytes = data[0:1]
        self.cmd_id: bytes = data[1:2]
        self.data: bytes = data[2:8]
        self.device_id: bytes = data[6:8]
        self.checksum: int = data[8]
        self.tail: bytes = data[9:10]
        self.expected_command_code: Command = command_code
        self.expected_response_type: ResponseType = response_type
        # Check it!
        self._verify()

    def _verify(self) -> None:
        """Verify the read data."""
        if self.head != HEAD:
            raise IncorrectWrapperException()
        if self.tail != TAIL:
            raise IncorrectWrapperException()
        if self.checksum != self._calc_checksum():
            raise ChecksumFailedException(
                expected=self.checksum, actual=self._calc_checksum()
            )
        if self.cmd_id != self.expected_response_type.value:
            raise IncorrectCommandException(
                expected=self.expected_response_type.value, actual=self.cmd_id
            )

        # Query responses don't validate the command code
        if (
            self.expected_response_type != ResponseType.QUERY_RESPONSE
            and bytes([self.data[0]]) != self.expected_command_code.value
        ):
            raise IncorrectCommandCodeException(
                expected=self.expected_command_code.value, actual=self.data[0:1]
            )

    def _calc_checksum(self) -> int:
        """Calculate the checksum for the read data."""
        return sum(d for d in self.data) % 256


class QueryResponse(ReadResponse):
    """A query read response.

    Attributes:
        pm25: The PM2.5 reading from the device
        pm10: The PM10 reading from the device.
    """

    def __init__(self, data: bytes):
        """Create a query read response."""
        super().__init__(
            data, command_code=Command.QUERY, response_type=ResponseType.QUERY_RESPONSE
        )

        self.pm25: float = int.from_bytes(data[2:4], byteorder="little") / 10
        self.pm10: float = int.from_bytes(data[4:6], byteorder="little") / 10


class ReportingModeResponse(ReadResponse):
    """Reporting mode response.

    Attributes:
        operation_type: The operation type the response is for, either QUERY or SET_MODE.
        state: The current reporting mode, either ACTIVE or QUERYING
    """

    def __init__(self, data: bytes):
        """Create a reporting mode response."""
        super().__init__(data, command_code=Command.SET_REPORTING_MODE)
        self.operation_type: OperationType = OperationType(self.data[1:2])
        self.state: ReportingMode = ReportingMode(self.data[2:3])


class DeviceIdResponse(ReadResponse):
    """Device ID response.

    Attributes:
        device_id (bytes): The 4 byte device ID.
    """

    def __init__(self, data: bytes):
        """Create a device ID response."""
        super().__init__(data, command_code=Command.SET_DEVICE_ID)


class SleepWakeReadResponse(ReadResponse):
    """Sleep/Wake Response.

    Attributes:
        operation_type: The operation type the response is for, either QUERY or SET_MODE.
        state: The current sleep state, either WAKE or SLEEP.

    """

    def __init__(self, data: bytes):
        """Create a sleep/wake response."""
        super().__init__(data, command_code=Command.SET_SLEEP)
        self.operation_type: OperationType = OperationType(self.data[1:2])
        self.state: SleepState = SleepState(self.data[2:3])


class WorkingPeriodReadResponse(ReadResponse):
    """Working period response.

    Attributes:
        operation_type: The operation type the response is for, either QUERY or SET_MODE.
        interval: The working period interval, 0-30.  0 Indicates continuous reading.
    """

    def __init__(self, data: bytes):
        """Create a working period response."""
        super().__init__(data, command_code=Command.SET_WORKING_PERIOD)
        self.operation_type: OperationType = OperationType(self.data[1:2])
        self.interval: int = self.data[2]


class CheckFirmwareResponse(ReadResponse):
    """Response containing the firmware version.

    Attributes:
        year: The two-digit year of the firmware release.
        month: The month of the firmware release.
        day: The day of the firmware release.
    """

    def __init__(self, data: bytes):
        """Create a firmware response."""
        super().__init__(data, command_code=Command.CHECK_FIRMWARE_VERSION)
        self.year: int = self.data[1]
        self.month: int = self.data[2]
        self.day: int = self.data[3]
