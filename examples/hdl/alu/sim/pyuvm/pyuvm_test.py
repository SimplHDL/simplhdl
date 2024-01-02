from cocotb import top as dut
from cocotb.triggers import Timer
from pyuvm import (
    ConfigDB,
    test,
    uvm_sequence,
    uvm_test,
    uvm_env,
)

from alu_vip import Agent as AluAgent, SequenceItem, AluIf, Command
from clock_vip import Agent as ClockAgent, ClockIf


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


class Env(uvm_env):

    clockAgent: ClockAgent
    aluAgent: AluAgent

    def build_phase(self):
        super().build_phase()
        self.clockAgent = ClockAgent.create('clockAgent', self)
        self.aluAgent = AluAgent.create('aluAgent', self)


class AluTest(uvm_test):

    env: Env

    def build_phase(self):
        super().build_phase()
        clockIf = ClockIf(
            clock=dut.clk_i,
            reset=dut.rst_i
        )
        aluIf = AluIf(
            clock=dut.clk_i,
            reset=dut.rst_i,
            a=dut.a_i,
            b=dut.b_i,
            x=dut.x_o,
            cmd=dut.cmd_i,
            ready=dut.ready_o,
            busy=dut.busy_o,
            valid=dut.valid_i
        )
        ConfigDB().set(None, '*', 'clock_if', clockIf)
        ConfigDB().set(None, '*', 'alu_if', aluIf)
        self.env = Env.create('env', self)

    def end_of_elaboration_phase(self):
        super().end_of_elaboration_phase()
        self.dut = ConfigDB().get(None, '', 'alu_if')
        self.sequencer = ConfigDB().get(None, '', 'alu_sequencer')

    async def run_phase(self):
        self.raise_objection()
        await super().run_phase()
        seq = AddSeq.create('seq')
        await seq.start(self.sequencer)
        await Timer(500, 'ns')
        self.drop_objection()


@test()
class TestSimple(AluTest):

    def end_of_elaboration_phase(self):
        super().end_of_elaboration_phase()
