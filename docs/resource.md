# Resources

## Control Protocol

The most informative resource I've found is the [Control Protocol](https://cdn.sparkfun.com/assets/parts/1/2/2/7/5/Laser_Dust_Sensor_Control_Protocol_V1.3.pdf)
which outlines a presumably complete set of various commands you can send to the SDS011.  It provides information on 
which byte-level data must be sent, and what will be returned.

## Datasheet

The [SDS011 Data Sheet](https://cdn-reichelt.de/documents/datenblatt/X200/SDS011-DATASHEET.pdf) provides some good 
high-level information about how to interact with the device, but only includes protocol details about how to read from 
the device.  It also includes lots of hardware information about the device.

## EPA AQI

[Technical Spec for Reporting the EPA AQI](https://www.airnow.gov/sites/default/files/2020-05/aqi-technical-assistance-document-sept2018.pdf)

## Other Implementations

There are several other tools and libraries available for the SDS011.

* [sds011](https://pypi.org/project/sds011/) - Python library for interacting with the device, including a database
storage option, and a socket server.
* [simple-sds011](https://pypi.org/project/simple-sds011/) - A minimal library for reading samples from a SDS011.
* [py-sds011](https://pypi.org/project/py-sds011/) - Python 3 interface to the SDS011
* [pysds011](https://pypi.org/project/pysds011/) - Python library and command line tool for interacting with the SDS011.
* [monitor-air-quality](https://pypi.org/project/monitor-air-quality/) - A command line tool for interacting with the 
SDS011.