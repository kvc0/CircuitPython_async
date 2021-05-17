import time
from unittest import TestCase

from tasko import Loop


class TestBudgetScheduler(TestCase):
    def test_add_task(self):
        loop = Loop()
        ran = False

        async def foo():
            nonlocal ran
            ran = True
        loop.add_task(foo())
        loop._step()
        self.assertTrue(ran)

    def test_sleep(self):
        loop = Loop()
        complete = False

        async def foo():
            nonlocal complete
            await loop.sleep(0.1)
            complete = True
        loop.add_task(foo())
        start = time.monotonic()
        while not complete and time.monotonic() - start < 1:
            loop._step()
        self.assertTrue(complete)

    def test_schedule_rate(self):
        # Checks a bunch of scheduled tasks to make sure they hit their target fixed rate schedule.
        # Pathological scheduling sees these tasks barge in front of others all the time. Many run
        # at a fairly high frequency.
        #
        # 98 tasks => 15khz throughput tested.
        #   Works reliably on macbook pro; microcontroller throughput will be.. somewhat less.

        loop = Loop(debug=False)
        duration = 1  # Seconds to run the scheduler. (try with 10s if you suspect scheduler drift)
        tasks = 96    # How many tasks (higher indexes count faster. 96th task => 293hz)

        counters = []
        for i in range(tasks):
            async def f(_i):
                counters[_i] += 1

            counters.append(0)

            loop.schedule(3 * (i + 1) + 5, f, i)

        start = time.monotonic()
        while time.monotonic() - start < duration:
            loop._step()

        expected_tps = 0
        actual_tps = 0
        # Assert that all the tasks hit their scheduled count, at least within +-5 iterations.
        for i in range(len(counters)):
            self.assertAlmostEqual(duration * (3*(i+1) + 5), counters[i], delta=5)
            expected_tps += (3*(i+1) + 5)
            actual_tps += counters[i]
        actual_tps /= duration
        print('expected tps:', expected_tps, 'actual:', actual_tps)
    
    def test_schedule_later(self):
        control_ticks = 0
        deferred_ticks = 0
        deferred_ticked = False
        loop = Loop(debug=False)

        async def deferred_task():
            nonlocal deferred_ticked, deferred_ticks
            deferred_ticks = deferred_ticks + 1
            deferred_ticked = True

        async def control_ticker():
            nonlocal control_ticks
            control_ticks = control_ticks + 1

        loop.schedule(10, control_ticker)
        loop.schedule_later(1, deferred_task)

        while True:
            loop._step()
            if deferred_ticked:
                break

        self.assertEqual(deferred_ticks, 1)
        self.assertAlmostEqual(control_ticks, 10, delta=1)
