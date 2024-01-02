from enum import IntEnum
from random import choice, randint

from pyuvm import uvm_sequence_item

__ALL__ = ['Command', 'SequenceItem']


class Command(IntEnum):
    ADD = 0
    SUB = 1
    MUL = 2


class SequenceItem(uvm_sequence_item):

    def __init__(self, name, cmd=None, a=None, b=None, delay=None):
        super().__init__(name)
        self.a = a
        self.b = b
        self.cmd = cmd
        self.x = None
        self.delay = None

    def randomize(self):
        if self.a is None:
            self.a = randint(0, 255)
        if self.b is None:
            self.b = randint(0, 255)
        if self.cmd is None:
            self.cmd = choice(list(Command))
        if self.delay is None:
            self.delay = randint(0, 8)

    def __eq__(self, others):
        return (
            self.a == others.a and
            self.b == others.b and
            self.cmd == others.cmd
        )

    def __str__(self):
        return f'{self.get_name()} | a:{self.a}'
