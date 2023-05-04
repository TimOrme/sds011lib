"""Byte constants for the SDS011 device."""
from enum import Enum


# Message head constant
HEAD = b"\xaa"
# Message tail constant
TAIL = b"\xab"

# ID to send if the command should be issued to all sensor IDs.
ALL_SENSOR_ID = b"\xff\xff"

# The submit type
SUBMIT_TYPE = b"\xb4"


class ResponseType(Enum):
    """Response types for commands.

    GENERAL_RESPONSE is for all commands except query.
    QUERY_RESPONSE only applies to the query command.
    """

    GENERAL_RESPONSE = b"\xc5"
    # Query command has its own response type.
    QUERY_RESPONSE = b"\xc0"


class Command(Enum):
    """Possible commands for the device."""

    SET_REPORTING_MODE = b"\x02"
    QUERY = b"\x04"
    SET_DEVICE_ID = b"\x05"
    SET_SLEEP = b"\x06"
    SET_WORKING_PERIOD = b"\x08"
    CHECK_FIRMWARE_VERSION = b"\x07"


class OperationType(Enum):
    """Operation type for many commands.

    Many commands have two modes, one for setting a value, and another for retrieving.
    """

    QUERY = b"\x00"
    SET_MODE = b"\x01"


class ReportingMode(Enum):
    """Reporting mode for the device.

    ACTIVE mode means that the device is constantly returning read data from the device, and won't respond correctly
    to other query requests.

    QUERYING mode means that the device won't return read data unless explicitly asked for it.
    """

    ACTIVE = b"\x00"
    QUERYING = b"\x01"


class SleepState(Enum):
    """State of the device, either wake or sleep."""

    SLEEP = b"\x00"
    WAKE = b"\x01"
