# tasko
This is a pure Python concurrency implementation for the async/await language syntax.

![Tests](https://github.com/WarriorOfWire/tasko/actions/workflows/python-tests.yml/badge.svg)


## Loop
*`while True`, redefined.*

* lets you schedule tasks that may take a long time without making special state machines for them.
* supports non-blocking sleep() for tasks.
* calls `time.sleep()` for a microcontroller-friendly lower power sleep when there's nothing to do.

[Loop Source](tasko/loop.py)


## What can I do with this

### You can make your entire app asynchronous.

Your tasks could look like:
* Set `reading_sensor` to True
  * Send a message over I2C to a sensor telling it to do an environment sample and sleep 1 second (takes 1 second to read)
  * Update in-memory state of your current sensor reading and sleep for 10 seconds.
* Update "loading" beach ball displayio animation 10 times per second while `reading_sensor`
* Read status updates from a 3d printer 5 times per second.
* Read a rotary button 100 times per second.

### You can use a context manager that wraps your SPI bus.
Using `tasko.managed_resource.ManagedResource` you can share an SPI bus between concurrent tasks without explicit
coordination.

```python
def setup_spi():
    from tasko.managed_resource import ManagedResource
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
        # Or, if you're a library author consider taking the handle as an arg
        # so you can acquire, send, release, --> sleep <--, acquire, read, release
        # rather than holding the spi for the whole operation
        await send_and_read_from_sensor(bus)

async def log_to_sdcard(sdcard_handle):
    async with sdcard_handle as bus:
        bytes_written = await write_to_sdcard(bus)

    # You can update the frequency of the task based on whatever you want
    # to focus your processor time on what currently matters.
    # stop() and start() can help you toggle whole aspects of your application.
    if bytes_written == 0:
        sd_log_scheduled_task.change_rate(Duration.of_seconds(10))
    else:
        sd_log_scheduled_task.change_rate(Duration.of_milliseconds(100))

sensor_handle, sdcard_handle = setup_spi()
tasko.schedule(Duration.of_seconds(1), read_sensor, sensor_handle)
sd_log_scheduled_task = tasko.schedule(Duration.of_seconds(10), log_to_sdcard, sdcard_handle)
tasko.run()
```

### You can run something later
```python
pending_sensor = False

async def read_sensor():
    read_bme680(board.SPI)

async def read_button():
    nonlocal pending_sensor
    was_pressed = check_if_button_was_pressed()

    if was_pressed and not pending_sensor:
        # Read the sensor a second later, you can show UI or something beforehand,
        # or you could tell the BME680 to warm up its VOC sensor without waiting for it.
        # You'll still be checking the button at 100hz in the meantime.
        tasko.run_later(seconds_to_delay=1, read_sensor())

def run():
    tasko.schedule(Duration.of_milliseconds(10), read_button)
    tasko.run()

if __name__ == '__main__':
    run()
```

### You can do a lot more than this
Any time you are faced with needing to wait around for something you might be tempted to add state to some class and inspect
it up in your main loop(), or "pulse" through your app every loop() to move state forward.

You could instead consider `await`ing the condition you need to be fulfilled; be it time or something else.

## Some toy example code
Uses [this library](https://github.com/WarriorOfWire/circuitpython-utilities/blob/master/cpy_rotary/README.md) for the rotary button

```python
import tasko
from cpy_rotary import RotaryButton


# Some state.  Global state is not super cool but whatevs
reading_sensor = False


# Define the top-level workflows (you would have to write this stuff no matter what)
async def read_sensor():
    global reading_sensor
    reading_sensor = True
    try:
        i2c.send(payload)
        await tasko.sleep(1)  # Don't block your loading beach ball while the sensor is sensing.
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


# ---------- Tasko wiring begins here ---------- #
# Schedule the workflows at whatever frequency makes sense
tasko.schedule(Duration.of_milliseconds(100), coroutine_function=read_sensor)
tasko.schedule(Duration.of_milliseconds(100), coroutine_function=animate_beach_ball)
tasko.schedule(Duration.of_milliseconds(200), corouting_function=read_from_3d_printer)
tasko.schedule(Duration.of_milliseconds(10), coroutine_function=rotary.loop)

# And let tasko do while True
tasko.run()
# ----------  Tasko wiring ends here  ---------- #
```


## Want to try it out on your microcontroller?
Cool!  The `async` and `await` keywords are supported in Circuitpython 6.0.  Unless you are from the future you will
need to update your microcontroller.  Also, it may be unavailable on your m0 microcontroller because of flash space.
