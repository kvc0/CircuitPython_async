from .loop import Loop


__global_event_loop = None


def get_loop():
    """Returns the singleton event loop"""
    global __global_event_loop
    if __global_event_loop is None:
        __global_event_loop = Loop()
    return __global_event_loop


add_task = get_loop().add_task
schedule = get_loop().schedule
sleep = get_loop().sleep
suspend = get_loop().suspend

run = get_loop().run
