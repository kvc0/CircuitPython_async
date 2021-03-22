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
