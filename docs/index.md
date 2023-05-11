# Introduction

`sds011lib` is a fully-typed, nearly-complete, python3 library for interacting with the SDS011 Air Quality Sensor.

## Installation

`sds011lib` requires Python3.6+.

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

## Examples

### Reading From The Device

```python
from sds011lib import SDS011QueryReader
import serial

# Create a query mode reader.
reader = SDS011QueryReader(ser_dev=serial.Serial('/dev/ttyUSB0', timeout=2))

# Query the device
result = reader.query()

# Print out the PM values
print(f"PM 2.5: {result.pm25}")
print(f"PM 10: {result.pm10}")
```

### Sleeping/Waking The Device

```python
from sds011lib import SDS011QueryReader
import serial

# Create a query mode reader.
reader = SDS011QueryReader(ser_dev=serial.Serial('/dev/ttyUSB0', timeout=2))

# Put the device to sleep.
reader.sleep()

# Do something....

# Wake the device back up
reader.wake()

# You can also check the device sleep state
result = reader.get_sleep_state()
print(result.state)
```

### Set The Working Period

```python
from sds011lib import SDS011QueryReader
import serial

# Create a query mode reader.
reader = SDS011QueryReader(ser_dev=serial.Serial('/dev/ttyUSB0', timeout=2))

# Set the working period to every 2 minutes
reader.set_working_period(2)

# Query for some data
data = reader.query()

# Check the current working period
result = reader.get_working_period()
print(result.interval)

# Set the device to work continuously
reader.set_working_period(0)
```

### Set The Device ID

```python
from sds011lib import SDS011QueryReader
import serial

# Create a query mode reader.
reader = SDS011QueryReader(ser_dev=serial.Serial('/dev/ttyUSB0', timeout=2))

# Set the ID
reader.set_device_id(b"\xC1\x4B")

# Query again
result = reader.query()

# See that the device ID is set
print(result.device_id)
```