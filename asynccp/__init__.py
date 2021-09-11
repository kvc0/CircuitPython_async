from .loop import Loop

# Enable logging by setting builtins.asynccp_logging = True before importing the first time.
#
# import builtins
# builtins.asynccp_logging = True
# import asynccp

__global_event_loop = None

try:
    global asynccp_logging
    if asynccp_logging:
        print('Enabling asynccp instrumentation')
except NameError:
    # Set False by default to skip debug logging
    asynccp_logging = False


def get_loop(debug=asynccp_logging):
    """Returns the singleton event loop"""
    global __global_event_loop
    if __global_event_loop is None:
        __global_event_loop = Loop(debug=debug)
    return __global_event_loop


add_task = get_loop().add_task
run_later = get_loop().run_later
schedule = get_loop().schedule
schedule_later = get_loop().schedule_later
delay = get_loop().delay
suspend = get_loop().suspend

run = get_loop().run
