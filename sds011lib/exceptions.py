"""All exception classes for the SDS011."""


class Sds011Exception(Exception):
    """Base exception for SDS011 device."""

    pass


class ChecksumFailedException(Sds011Exception):
    """Thrown if the checksum value in a response is incorrect.

    This indicates some corruption of the response.

    Attributes:
        expected: The expected checksum
        actual: The actual checksum
    """

    def __init__(self, expected: int, actual: int):
        """Create exception."""
        super().__init__()
        self.expected: int = expected
        self.actual: int = actual


class IncorrectCommandException(Sds011Exception):
    """Thrown if the command ID in a response is incorrect.

    Attributes:
        expected: The expected command id as bytes
        actual: The actual command id as bytes.
    """

    def __init__(self, expected: bytes, actual: bytes):
        """Create exception."""
        super().__init__(f"Expected command {expected!r}, found {actual!r}")
        self.expected: bytes = expected
        self.actual: bytes = actual


class IncorrectCommandCodeException(Sds011Exception):
    """Thrown if the command code in a response is incorrect.

    Attributes:
        expected: The expected command code as bytes
        actual: The actual command code as bytes.
    """

    def __init__(self, expected: bytes, actual: bytes):
        """Create exception."""
        super().__init__(f"Expected code {expected!r}, found {actual!r}")
        self.expected: bytes = expected
        self.actual: bytes = actual


class IncorrectWrapperException(Sds011Exception):
    """Thrown if the wrapper of a response (either HEAD or TAIL) is incorrect.

    This indicates some corruption of the response.
    """

    pass


class IncompleteReadException(Sds011Exception):
    """Thrown if the device didn't return complete data when asking for a response.

    Responses must be 10 bytes total.  If the device doesn't respond with a complete 10 bytes, it can mean that either
    1) The device is in sleep mode or 2) The device is in query mode, and nothing was requested.
    """

    pass


class InvalidDeviceIdException(Sds011Exception):
    """Thrown if the trying to set the device ID on an invalid device.

    This occurs if you try and send to a device ID that doesn't exist.
    """

    pass
