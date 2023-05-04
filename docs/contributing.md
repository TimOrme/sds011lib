# Contributing

## Toolset

To start developing, you'll need to install the following tools:

- [Python 3.9+](https://www.python.org/) - For API Code
- [poetry](https://python-poetry.org/) - For python package management
- [justfile](https://github.com/casey/just) - For builds

Optionally, we have [pre-commit](https://pre-commit.com/) hooks available as well.  To install hooks, just run
`pre-commit install` and then linters and autoformatting will be applied automatically on commit.

## Quickstart

To build the project, and install all dev-dependencies, run:

```commandline
just build
```

To run tests for the project, run:

```commandline
just test
```

To manually run lint checks on the code, run:

```commandline
just lint
```

To run auto-formatters, run:

```commandline
just format
```

## Testing Against The Emulator

In the testing folder, tests run against an emulated serial device that _mostly_ should behave like an SDS011 device. 
This can be extremely helpful for running unit tests without an actual device (such as in our automated builds.)  This 
is the default behavior, and you can find this in the test setups like so:

```python
import pytests
from typing import Generator
from tests.serial_emulator import Sds011SerialEmulator
from sds011lib import SDS011Reader

class TestBaseReader:
    @pytest.fixture
    def reader(self) -> Generator[SDS011Reader, None, None]:
        # Set up the reader to use the serial emulator
        ser_dev = Sds011SerialEmulator()
        reader = SDS011Reader(ser_dev=ser_dev, send_command_sleep=0)
        yield reader
```

## Testing Against A Real Device

It can also be helpful to run tests integrated against an actual device.  Fortunately, switching to do that is simple. 
Just replace the emulator with an actual Serial object instead:

```python
import pytests
import serial
from typing import Generator
from sds011lib import SDS011Reader

class TestBaseReader:
    @pytest.fixture
    def reader(self) -> Generator[SDS011Reader, None, None]:
        # Set up the reader to use a device attached on /dev/ttyUSB0
        ser_dev = serial.Serial('/dev/ttyUSB0', timeout=2, baudrate=9600)
        reader = SDS011Reader(ser_dev=ser_dev, send_command_sleep=0)
        yield reader
```

## Submitting a PR

The main branch is locked, but you can open a PR on the repo.  Build checks must pass, and changes approved by a code
owner, before merging.
