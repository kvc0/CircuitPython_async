# tasko
This is a pure Python concurrency implementation for the async/await language syntax.


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

### You can make a context manager that wraps your SPI bus.
Maybe you have 2 displays, an SD card and 4 sensors on your bus
with naught to tell them apart but a CS pin for each.  You can have each thing that needs to use the bus `async with shared_spi as spi:`
and worry less about scheduling the perfect times to interact with SPI.

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
tasko.schedule(hz=10,  coroutine_function=read_sensor)
tasko.schedule(hz=10,  coroutine_function=animate_beach_ball)
tasko.schedule(hz=5,   corouting_function=read_from_3d_printer)
tasko.schedule(hz=100, coroutine_function=rotary.loop)

# And let tasko do while True
tasko.run()
# ----------  Tasko wiring ends here  ---------- #
```
