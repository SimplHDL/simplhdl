from cocotb import top as dut
from cocotb.triggers import Timer
from pyuvm import (
    ConfigDB,
    test,
    uvm_test,
)

from alu_vip import AluIf
from clock_vip import ClockIf
from .env import Env
from .seq_lib import AddSeq


class AluTest(uvm_test):

    def build_phase(self):
        super().build_phase()
        self.env = Env.create('env', self)
        clockIf = ClockIf(
            clock=dut.clk_i,
            reset=dut.rst_i
        )
        self.aluIf = AluIf(
            clock=dut.clk_i,
            reset=dut.rst_i,
            a=dut.a_i,
            b=dut.b_i,
            x=dut.x_o,
            cmd=dut.cmd_i,
            ready=dut.ready_o,
            valid=dut.valid_i
        )
        ConfigDB().set(None, '*', 'clock_if', clockIf)
        ConfigDB().set(None, '*', 'alu_if', self.aluIf)

    def connect_phase(self):
        super().connect_phase()
        self.dut = self.aluIf

    def end_of_elaboration_phase(self):
        super().end_of_elaboration_phase()
        self.sequencer = ConfigDB().get(None, '', 'alu_sequencer')

    async def run_phase(self):
        self.raise_objection()
        await super().run_phase()
        for _ in range(10):
            seq = AddSeq.create('seq')
            await seq.start(self.sequencer)
        await Timer(500, 'ns')
        self.drop_objection()
