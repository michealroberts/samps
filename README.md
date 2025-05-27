# samps

A hypermodern, type-safe, zero-dependency Python library for serial port I/O access.

## Installation

```bash
pip install samps
```

or

using your preferred environment / package manager of choice, e.g., `poetry`, `conda` or `uv`:

```bash
poetry add samps
```

```bash
conda install samps
```

```bash
uv add samps
```

## Usage

The general usage of this library is to create a serial connection to the device you want to communicate with.

You'll need to know the serial port name and the baudrate of the device you want to communicate with, this is usually found in the device's documentation.

Once you have the serial port name and baudrate, you can create a `SerialCommonInterface` (or `SerialAsyncCommonInterface`) object and use it to communicate with the device as follows:

```python
from samps import SerialCommonInterface as Serial

serial = Serial(port="/dev/tty.usbserial-0001", baudrate=9600)

serial.open()

print(["Serial Port Is Open?", "Yes" if serial.is_open() else "No"])

line = serial.readline()

print(line.decode("utf-8").strip())

serial.close()

print(["Serial Port Closed"])
```

or, using a context manager:

```python
from samps import SerialCommonInterface as Serial

with Serial(port="/dev/tty.usbserial-0001", baudrate=9600) as serial:
    print(["Serial Port Is Open?", "Yes" if serial.is_open() else "No"])

    line = serial.readline()

    print(line.decode("utf-8").strip())

print(["Serial Port Closed"])
```

The library also provides an asynchronous interface for serial communication, which can be used in an `asyncio` event loop. 

Here's an example of how to use the asynchronous interface:

```python
from samps import SerialAsyncCommonInterface as Serial

async with Serial(port="/dev/tty.usbserial-0001", baudrate=9600) as serial:
    print(["Serial Port Is Open?", "Yes" if serial.is_open() else "No"])

    line = await serial.readline()

    print(line.decode("utf-8").strip())

print(["Serial Port Closed"])
```

## Milestones

- [x] Implement SerialCommonInterface for POSIX systems
- [x] Implement SerialAsyncCommonInterface for POSIX systems
- [ ] Implement SerialCommonInterface for Windows systems
- [ ] Implement SerialAsyncCommonInterface for Windows systems
- [x] Implement SerialCommonInterface for MacOS systems
- [x] Implement SerialAsyncCommonInterface for MacOS systems
- [ ] Implement SerialOverTCP (e.g., telnet RFC 2217)
- [ ] Documentation

## Contributing

Contributions are welcome! Please read the [CONTRIBUTING.md](CONTRIBUTING.md) file for details on how to contribute to this project.

### License

This project is licensed under the terms of the MIT license.


