# sds011lib

![Main](https://github.com/TimOrme/sds011lib/actions/workflows/main.yml/badge.svg)

`sds011lib` is a fully-typed, nearly-complete, python 3.8+ library for interacting with the SDS011 Air Quality Sensor.

The SDS011 is a small, low-cost sensor created by www.inovafitness.com, used to measure particulate matter in the air.  It 
can measure both PM 2.5 and PM10 values simultaneously, and connects to devices over a serial port, or via USB with an
included adaptor.

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
sensor = SDS011QueryReader('/dev/ttyUSB0')

# Read some data!
aqi = sensor.query()
print(aqi.pm25)
print(aqi.pm10)

# Put the device to sleep
sensor.sleep()

# Wake it back up
sensor.wake()
```