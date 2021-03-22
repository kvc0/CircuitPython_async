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
        # Assert that all the tasks hit their scheduled count, at least within +-2 iterations.
        for i in range(len(counters)):
            self.assertAlmostEqual(duration * (3*(i+1) + 5), counters[i], delta=2)
            expected_tps += (3*(i+1) + 5)
            actual_tps += counters[i]
        actual_tps /= duration
        print('expected tps:', expected_tps, 'actual:', actual_tps)
