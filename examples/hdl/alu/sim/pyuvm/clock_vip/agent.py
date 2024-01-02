import logging

from cocotb import start_soon
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles
from pyuvm import ConfigDB, uvm_agent

__ALL__ = ['Agent']


logger = logging.getLogger(__name__)


class Agent(uvm_agent):

    def build_phase(self):
        super().build_phase()
        self.vif = ConfigDB().get(None, "", 'clock_if')

    def end_of_elaboration_phase(self):
        super().end_of_elaboration_phase()
        self.vif.clock.setimmediatevalue(0)
        self.vif.reset.setimmediatevalue(1)

    async def run_phase(self):
        await super().run_phase()
        start_soon(Clock(self.vif.clock, 10, units='ns').start())
        await ClockCycles(self.vif.clock, 5)
        self.vif.reset.value = 0
