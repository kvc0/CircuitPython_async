# CircuitPython_async
![Tests](https://github.com/WarriorOfWire/CircuitPython_async/actions/workflows/python-tests.yml/badge.svg)

## About
Pure Python cooperative multitasking implementation for the async/await language syntax.

Loosely modeled after CPython's standard `asyncio`; focused on CircuitPython.

Typically, when you need to wait around for something you have to choose between just doing time.sleep() and
having a hitch in your app OR manually interleaving tasks and tracking their state & timers.

`asynccp` interleaves your tasks at `await` points in the same general way as `asyncio` does on regular python.
Instead of blocking with `time.sleep()` you'll `await asynccp.delay()` to let the microcontroller work on other
things.

## Examples
### Plain synchronous loop task with async support
```python
import asynccp


async def read_some_sensor(self):
    pass


async def check_button(self):
    pass


async def update_display(self):
    pass


async def loop():
    await read_some_sensor()
    await check_button()
    await update_display()


def run():
    asynccp.add_task(loop())
    asynccp.run()


if __name__ == '__main__':
    run()
```

### Scheduled app instead of loop
```python
import asynccp
import asynccp.time.Duration as Duration

class App:
    def __init__(self):
        self.button_state = 0
        self.sensor_state = 0

    async def read_some_sensor(self):
        pass

    async def check_button(self):
        pass

    async def update_display(self):
        pass


def run():
    app = App()

    asynccp.schedule(frequency=Duration.of_seconds(5), coroutine_function=app.read_some_sensor)
    asynccp.schedule(frequency=80, coroutine_function=app.check_button)
    asynccp.schedule(frequency=15, coroutine_function=app.update_display)
    asynccp.run()


if __name__ == '__main__':
    run()
```

### Multiplex SPI bus without manual coordination
Using `asynccp.managed_resource.ManagedResource` you can share an SPI bus between concurrent tasks without explicit
coordination.

```python
def setup_spi():
    from asynccp.managed_resource import ManagedResource
    import digitalio
    import board
    # Configure the hardware
    spi = board.SPI()

    sensor_cs = digitalio.DigitalInOut(board.D4)
    sensor_cs.direction = digitalio.Direction.OUTPUT

    sdcard_cs = digitalio.DigitalInOut(board.D5)
    sdcard_cs.direction = digitalio.Direction.OUTPUT

    # Set up acquire/release workflow for the SPI bus
    def set_active(pin):
        pin.value = True

    def set_inactive(pin):
        pin.value = False

    # Configure the physical spi as a managed resource with callbacks that manage the CS pin
    managed_spi = ManagedResource(spi, on_acquire=set_active, on_release=set_inactive)

    # Get awaitable handles for each CS using this SPI bus
    sensor_handle = managed_spi.handle(pin=sensor_cs)
    sdcard_handle = managed_spi.handle(pin=sdcard_cs)

    return sensor_handle, sdcard_handle
```

And with these configured resource handles you can use them without checking whether anything is busy.  Things will
efficiently wait when they have to, and charge right on through when there's nothing using the bus currently.
```python
async def read_sensor(sensor_handle):
    async with sensor_handle as bus:
        await send_read_request_to_sensor(bus)
        # Consider a BME680 which needs a delay before reading the requested result.
        # Let's let something else use the bus while it's waiting
    await asynccp.delay(seconds=0.1)
    async with sensor_handle as bus:
        return await read_result_from_sensor(bus)

async def log_to_sdcard(sdcard_handle):
    async with sdcard_handle as bus:
        bytes_written = await write_to_sdcard(bus)

sensor_handle, sdcard_handle = setup_spi()
asynccp.schedule(Duration.of_milliseconds(123), read_sensor, sensor_handle)
sd_log_scheduled_task = asynccp.schedule(Duration.of_seconds(1.5), log_to_sdcard, sdcard_handle)
asynccp.run()
```

## Some toy example code
Uses [this library](https://github.com/WarriorOfWire/circuitpython-utilities/blob/master/cpy_rotary/README.md) for the rotary button

```python
import asynccp
from cpy_rotary import RotaryButton


# Some state.  Global state is not super cool but whatevs
reading_sensor = False


# Define the top-level workflows (you would have to write this stuff no matter what)
async def read_sensor():
    global reading_sensor
    reading_sensor = True
    try:
        i2c.send(payload)
        await asynccp.delay(1)  # Don't block your loading beach ball while the sensor is sensing.
        i2c.read(payload)  # if you have some buffered i2c thing
    finally:
        reading_sensor = False


async def animate_beach_ball():
    global reading_sensor
    if reading_sensor:
        set_animation_state()  # hopefully this is quick - if not, maybe there's something inside to `await`


async def read_from_3d_printer():
    pass


rotary = RotaryButton()


# ---------- asynccp wiring begins here ---------- #
# Schedule the workflows at whatever frequency makes sense
asynccp.schedule(Duration.of_milliseconds(100), coroutine_function=read_sensor)
asynccp.schedule(Duration.of_milliseconds(100), coroutine_function=animate_beach_ball)
asynccp.schedule(Duration.of_milliseconds(200), corouting_function=read_from_3d_printer)
asynccp.schedule(Duration.of_milliseconds(10), coroutine_function=rotary.loop)

# And let asynccp do while True
asynccp.run()
# ----------  asynccp wiring ends here  ---------- #
```


## Want to try it out on your microcontroller?
Cool!  The `async` and `await` keywords are supported in Circuitpython 6.0.  Unless you are from the future you will
need to update your microcontroller.  Also, it may be unavailable on your m0 microcontroller because of flash space.
