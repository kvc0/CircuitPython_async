
class Duration:
    @staticmethod
    def of_hours(count):
        return Duration(count * 60 * 60 * 1000000000)

    @staticmethod
    def of_minutes(count):
        return Duration(count * 60 * 1000000000)

    @staticmethod
    def of_seconds(count):
        return Duration(count * 1000000000)

    @staticmethod
    def of_milliseconds(count):
        return Duration(count * 1000000)

    @staticmethod
    def of_microseconds(count):
        return Duration(count)

    def __init__(self, nanoseconds):
        self._nanoseconds = int(nanoseconds)

    def __add__(self, other):
        return Duration(self._nanoseconds + other._nanoseconds)

    def __sub__(self, other):
        return Duration(self._nanoseconds - other._nanoseconds)

    def __neg__(self):
        return Duration(-1 * self._nanoseconds)

    def as_frequency(self):
        """returns this duration as a frequency interval in HZ"""
        return 1000000000.0 / self._nanoseconds

    def as_seconds(self):
        return self._nanoseconds / 1000000000.0

    def as_milliseconds(self):
        return self._nanoseconds / 1000000.0

    def as_microseconds(self):
        return self._nanoseconds / 1000.0

    def as_nanoseconds(self):
        return self._nanoseconds
