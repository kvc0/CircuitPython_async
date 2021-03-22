import time


def _yield_once():
    """await the return value of this function to yield the processor"""
    class _CallMeNextTime:
        def __await__(self):
            # This is inside the scheduler where we know generator yield is the
            #   implementation of task switching in CircuitPython.  This throws
            #   control back out through user code and up to the scheduler's
            #   __iter__ stack which will see that we've suspended _current.
            # Don't yield in async methods; only await unless you're making a library.
            yield

    return _CallMeNextTime()


class Sleeper:
    def __init__(self, resume_time, task):
        self.task = task
        self._resume_time = resume_time

    def resume_time(self):
        return self._resume_time

    def __repr__(self):
        return '{{Sleeper remaining: {:.2f}, task: {} }}'.format(
            self.resume_time() - time.monotonic(),
            self.task
        )

    __str__ = __repr__


class Task:
    def __init__(self, coroutine):
        self.coroutine = coroutine

    def __repr__(self):
        return '{{Task {}}}'.format(self.coroutine)

    __str__ = __repr__


class TaskCanceledException(Exception):
    pass


class Loop:
    """
    It's your task host.  You run() it and it manages your main application loop.
    """

    def __init__(self, debug=False):
        self._tasks = []
        self._sleeping = []
        self._current = None
        if debug:
            self._debug = print
        else:
            self._debug = lambda *arg, **kwargs: None

    def add_task(self, awaitable_task):
        """
        Add a concurrent task (known as a coroutine, implemented as a generator in CircuitPython)
        Use:
          scheduler.add_task( my_async_method() )
        :param awaitable_task:  The coroutine to be concurrently driven to completion.
        """
        self._debug('adding task ', awaitable_task)
        self._tasks.append(Task(awaitable_task))

    async def sleep(self, seconds):
        """
        From within a coroutine, this suspends your call stack for some amount of time.

        NOTE:  Always `await` this!  You will have a bad time if you do not.

        :param seconds: Floating point; will wait at least this long to call your task again.
        """
        await self._sleep_until(time.monotonic() + seconds)

    def suspend(self):
        """
        For making library functions that suspend and then resume later on some condition
        E.g., a scope manager for SPI

        To use this you will stash the resumer somewhere to call from another coroutine, AND
        you will `await suspender` to pause this stack at the spot you choose.

        :returns (async_suspender, resumer)
        """
        assert self._current is not None, 'You can only suspend the current task if you are running the event loop.'
        suspended = self._current

        def resume():
            self._tasks.append(suspended)

        self._current = None
        return _yield_once(), resume

    def schedule(self, hz: float, coroutine_function, *args, **kwargs):
        """
        Describe how often a method should be called.

        Your event loop will call this coroutine on the hz schedule.
        Only up to 1 instance of your method will be alive at a time.

        This will use sleep() internally when there's nothing to do
        and scheduled, waiting functions consume no cpu so you should
        feel pretty good about using scheduled async functions.

        usage:
          async def main_loop:
            await your_code()
          get_loop().schedule(hz=100, coroutine_function=main_loop)
          get_loop().run()

        :param hz: How many times per second should the function run?
        :param coroutine_function: the async def function you want invoked on your schedule
        :param event_loop: An event loop that can .sleep() and .add_task.  Like BudgetEventLoop.
        """
        assert coroutine_function is not None, 'coroutine function must not be none'
        self._debug('scheduling ', coroutine_function, ' at ', hz, 'hz')

        async def schedule_at_rate(decorated_async_fn):
            seconds_per_invocation = 1 / hz
            target_run_time = time.monotonic()
            while True:
                iteration = decorated_async_fn(*args, **kwargs)
                self._debug('iteration ', iteration)
                await iteration
                # Try to reschedule for the next window without skew. If we're falling behind,
                # just go as fast as possible & schedule to run "now." If we catch back up again
                # we'll return to seconds_per_invocation without doing a bunch of catchup runs.
                target_run_time = target_run_time + seconds_per_invocation
                now = time.monotonic()
                if now <= target_run_time:
                    await self._sleep_until(target_run_time)
                else:
                    target_run_time = now

        self.add_task(schedule_at_rate(coroutine_function))

    def run(self):
        """
        Use:
            async def application_loop():
              pass

            def run():
              main_loop = Loop()
              loop.schedule(100, application_loop)
              loop.run()

            if __name__ == '__main__':
              run()
        The crucial StopIteration exception signifies the end of a coroutine in CircuitPython.
        Other Exceptions that reach the runner break out, stopping your app and showing a stack trace.
        """
        assert self._current is None, 'Loop can only be advanced by 1 stack frame at a time.'
        while self._tasks or self._sleeping:
            self._step()
        self._debug('Loop completed', self._tasks, self._sleeping)

    def _step(self):
        self._debug('stepping over ', len(self._tasks), ' tasks')
        for _ in range(len(self._tasks)):
            task = self._tasks.pop(0)
            self._run_task(task)
        # Consider each sleeping function at most once (avoids sleep(0) problems)
        for i in range(len(self._sleeping)):
            sleeper = self._sleeping[0]
            now = time.monotonic()
            if now >= sleeper.resume_time():
                self._sleeping.pop(0)
                self._run_task(sleeper.task)
            else:
                # We didn't pop the task and it wasn't time to run it.  Only later tasks past this one.
                break
        if len(self._tasks) == 0 and len(self._sleeping) > 0:
            next_sleeper = self._sleeping[0]
            sleep_seconds = next_sleeper.resume_time() - time.monotonic()
            if sleep_seconds > 0:
                # Give control to the system, there's nothing to be done right now,
                # and nothing else is scheduled to run for this long.
                # This is the real sleep. If/when interrupts are implemented this will likely need to change.
                self._debug('No active tasks.  Sleeping for ', sleep_seconds, 's. \n', self._sleeping)
                time.sleep(sleep_seconds)

    def _run_task(self, task: Task):
        """
        Runs a task and re-queues for the next loop if it is both (1) not complete and (2) not sleeping.
        """
        self._current = task
        try:
            task.coroutine.send(None)
            self._debug('current', self._current)
            # Sleep gate here, in case the current task suspended.
            # If a sleeping task re-suspends it will have already put itself in the sleeping queue.
            if self._current is not None:
                self._tasks.append(task)
        except StopIteration:
            # This task is all done.
            self._debug('task complete')
            pass
        finally:
            self._current = None

    async def _sleep_until(self, target_run_time):
        """
        From within a coroutine, sleeps until the target time.monotonic
        Returns the thing to await
        """
        assert self._current is not None, 'You can only sleep from within a task'
        self._sleeping.append(Sleeper(target_run_time, self._current))
        self._sleeping.sort(key=Sleeper.resume_time)  # heap would be better but hey.
        self._debug('sleeping ', self._current)
        self._current = None
        # Pretty subtle here.  This yields once, then it continues next time the task scheduler executes it.
        # The async function is parked at this point.
        await _yield_once()

