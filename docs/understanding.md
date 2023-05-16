# Understanding the SDS011

!!! warning "Caveat Emptor"

    Much of this understanding comes from reverse-engineering the device.  There are some cases where the SDS011 behaves
    in "unexpected" ways, but these might just be my misunderstanding of it's intended usage.  Without more official
    documentation, it's hard to know if the explanations outlined here are actually correct. 

The SDS011 is a small, low-cost sensor created by www.inovafitness.com, used to measure particulate matter in the air.  It 
can measure both PM 2.5 and PM10 values simultaneously, and connects to devices over a serial port, or via USB with an
included adaptor.

Because of its size and cost, it is often used on DIY projects with the [Raspberry Pi](https://www.raspberrypi.org/), 
or [Arduino](https://www.arduino.cc/) boards, though it can be used on many other devices as well. 

## Features

### Pollutants

The SDS011 measures both small [PM2.5](https://en.wikipedia.org/wiki/PM2.5) particles, and larger 
[PM10](https://en.wikipedia.org/wiki/PM10) particles, with a range of 0.0-999.9 μg / m<sup>3</sup>.

These pollutants can be used in part to calculate the [EPA AQI](https://www.airnow.gov/aqi/aqi-basics/).

### Reporting Modes

The SDS011 can report in both `ACTIVE` and `QUERYING` mode, with `ACTIVE` being the factory default.

In `ACTIVE` mode, the device will always respond with pollutant data, regardless of what other commands are sent to it.
It constantly responds with this data, though there are [caveats](#writing-in-active-mode) to this functionality.

In `QUERYING` mode, the device operates in a request/response model, where a request is written to the device, and then 
it writes a response to it's output.  In this mode, pollutant data must specifically be asked for. 

### Working Period

You can set the SDS011 to work continuously, reading all the time, or you can set it to turn on periodically and read 
for 30 seconds.  The device allows you to set the period between work between 0 and 30 minutes. As an example, if you 
set the working period to 10, the device would wake up every ten minutes, read for 30 seconds, and then turn itself off.

Setting the working period to 0 makes the device work continuously.

### Sleep/Wake

You can also manually turn the device on and off, by setting it to sleep or wake.  This can be helpful if you want to 
manually control the device to get reads, or if you need to have a working period longer than 30 minutes.  Note that in
sleep mode, the device still draws some power; just the fan and diode are turned off.

### Device IDs

The SDS011 has a 4 byte device ID, which _seems_ to help support cases where you have multiple devices attached to a single 
port, though I haven't actually tried to set this up.  Every command that the SDS011 accepts can take a target device ID,
or you can send commands to target *all* devices by passing `\xFF\xFF` as the device ID. 

## Suggested Operation

The SDS011 ships with two modes of operation: `ACTIVE` and `QUERYING`.  `QUERYING` mode, though not the factory default,
seems to be much more predictable in its behavior, is generally easier to use, has a more complete feature-set, and 
likely can help extend the lifetime of the device.  As such, I recommend using `QUERYING` mode.

It is also recommended to use either the [working period](#working-period) functionality, or to manually put the device
to sleep when not in use.  Generally, continuously reading doesn't give meaningful differentiation of reads when 
compared to intermittent but frequent reading.

Lastly, it's usually good to give the device at least 15 seconds to warm up after waking before taking any read data. 
This gives the fan some time to flush out any air in the device, and pull in a more meaningful external air from the 
outside.

## Device Lifetime

The SDS011 datasheet indicates that it has a lifetime of about 8000 hours, or a little less than a year of constant use.
An easy way to extend the life of your device is to turn it on intermittently rather than constantly.  There are two
ways to do this, either via setting the [working period](#working-period), or by manually putting the device to 
[sleep](#sleepwake) when it's not in use, and waking it when needed.  By reading for even just a few minutes spread 
throughout an hour, you can extend the lifetime of the device to multiple years. 

## Quirks

### Sending Commands in Active Mode

When in active mode, you can send commands to the device.  However, because the device is essentially constantly 
changing its response buffer to be pollutant data, you can't simply just read the latest data from the device, since the
latest data might be pollutant data instead of the response to your command.  The implementation of the 
`SDS011ActiveReader` handles this for you, but it's good to be aware of.

### Serial Connections in Active Mode

Because active mode is constantly sending back data over the serial port, it's best to not leave the connection open, 
since, unless you're reading from it constantly, the device will continually fill the response buffer with pollutant 
data.  Leaving this data there, might make you inadvertently read old data from the response buffer instead of the 
latest.  Instead, it's best to open and close the serial connection when executing queries and commands, so that you're
guaranteed to have recent data.  Again, the implementation of `SDS011ActiveReader` manages this for you, but something 
to keep in mind.

### Delayed Responses to Sending Commands

When sending commands to the device, it typically takes about a second for the device to write a response back to the 
serial port.  As such, all the readers are configured by default to have a 1 second sleep after a command is sent, so 
that the device has time to respond, and you don't receive errors when trying to read results back.

You can try and configure this to tune it if you'd like:

```python
from sds011lib import SDS011ActiveReader
import serial
# Create a query mode reader, with a 2 second sleep instead 
# of 1 after a command is sent. 
reader = SDS011ActiveReader('/dev/ttyUSB0', send_command_sleep=2)
```