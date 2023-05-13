"""Response objects for SDS011.

Creates and validates typed classes from binary responses from the device.
"""
from ._constants import (
    SleepState,
    OperationType,
    ReportingMode,
)

from dataclasses import dataclass


@dataclass(frozen=True)
class QueryResponse:
    """A query read response.

    Attributes:
        pm25: The PM2.5 reading from the device
        pm10: The PM10 reading from the device.
    """

    pm25: float
    pm10: float
    device_id: bytes


@dataclass(frozen=True)
class ReportingModeResponse:
    """Reporting mode response.

    Attributes:
        operation_type: The operation type the response is for, either QUERY or SET_MODE.
        state: The current reporting mode, either ACTIVE or QUERYING
    """

    operation_type: OperationType
    state: ReportingMode


@dataclass(frozen=True)
class DeviceIdResponse:
    """Device ID response.

    Attributes:
        device_id (bytes): The 4 byte device ID.
    """

    device_id: bytes


@dataclass(frozen=True)
class SleepWakeReadResponse:
    """Sleep/Wake Response.

    Attributes:
        operation_type: The operation type the response is for, either QUERY or SET_MODE.
        state: The current sleep state, either WAKE or SLEEP.

    """

    operation_type: OperationType
    state: SleepState


@dataclass(frozen=True)
class WorkingPeriodReadResponse:
    """Working period response.

    Attributes:
        operation_type: The operation type the response is for, either QUERY or SET_MODE.
        interval: The working period interval, 0-30.  0 Indicates continuous reading.
    """

    operation_type: OperationType
    interval: int


@dataclass(frozen=True)
class CheckFirmwareResponse:
    """Response containing the firmware version.

    Attributes:
        year: The two-digit year of the firmware release.
        month: The month of the firmware release.
        day: The day of the firmware release.
    """

    year: int
    month: int
    day: int
