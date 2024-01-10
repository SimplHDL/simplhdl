from pyuvm import uvm_sequence
from alu_vip import SequenceItem, Command

__ALL__ = ['AddSeq', 'SubSeq', 'MulSeq']


class BaseSequence(uvm_sequence):

    tr: uvm_sequence = None

    async def body(self):
        await super().body()
        if self.tr is None:
            self.tr = SequenceItem('tr')
        await self.start_item(self.tr)
        self.tr.randomize()
        await self.finish_item(self.tr)


class AddSeq(BaseSequence):
    async def body(self):
        self.tr = SequenceItem('tr', cmd=Command.ADD)
        await super().body()


class SubSeq(BaseSequence):
    async def body(self):
        self.tr = SequenceItem('tr', cmd=Command.SUB)
        await super().body()


class MulSeq(BaseSequence):
    async def body(self):
        self.tr = SequenceItem('tr', cmd=Command.MUL)
        await super().body()
