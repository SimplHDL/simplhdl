__ALL__ = ['ClockIf']


class ClockIf:

    def __init__(self, clock, reset):
        self.clock = clock
        self.reset = reset
