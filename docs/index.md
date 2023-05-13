# Introduction

`sds011lib` is a fully-typed, nearly-complete, python 3.8+ library for interacting with the SDS011 Air Quality Sensor.

The SDS011 is a small, low-cost sensor created by www.inovafitness.com, used to measure particulate matter in the air.  It 
can measure both PM 2.5 and PM10 values simultaneously, and connects to devices over a serial port, or via USB with an
included adaptor.

## Installation

`sds011lib` requires Python3.8+.

```commandline
pip install sds011lib
```

## Quickstart

```python
from sds011lib import SDS011QueryReader

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

## Examples

### Reading From The Device

```python
from sds011lib import SDS011QueryReader

# Create a query mode reader.
reader = SDS011QueryReader('/dev/ttyUSB0')

# Query the device
result = reader.query()

# Print out the PM values
print(f"PM 2.5: {result.pm25}")
print(f"PM 10: {result.pm10}")
```

### Sleeping/Waking The Device

```python
from sds011lib import SDS011QueryReader

# Create a query mode reader.
reader = SDS011QueryReader('/dev/ttyUSB0')

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

# Create a query mode reader.
reader = SDS011QueryReader('/dev/ttyUSB0')

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

# Create a query mode reader.
reader = SDS011QueryReader('/dev/ttyUSB0')

# Set the ID
reader.set_device_id(b"\xC1\x4B")

# Query again
result = reader.query()

# See that the device ID is set
print(result.device_id)
```