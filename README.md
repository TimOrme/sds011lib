# sds011lib

`sds011lib` is a fully-typed, nearly-complete, python3 library for interacting with the SDS011 Air Quality Sensor.

The full documentation is available at https://timorme.github.io/sds011lib/

## Installation

```commandline
pip install sds011lib
```

## Quickstart

```python
from sds011lib import SDS011QueryReader
from serial import Serial

# Setup a query-mode reader on /dev/ttyUSB0 
sensor = SDS011QueryReader(ser_dev=Serial('/dev/ttyUSB0', timeout=2))

# Read some data!
aqi = sensor.query()
print(aqi.pm25)
print(aqi.pm10)

# Put the device to sleep
sensor.sleep()

# Wake it back up
sensor.wake()
```