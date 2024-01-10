from cocotb.triggers import ClockCycles, FallingEdge, RisingEdge
from pyuvm import ConfigDB, uvm_driver

__ALL__ = ["Driver"]


class Driver(uvm_driver):

    def build_phase(self):
        super().build_phase()
        self.vif = ConfigDB().get(None, '', 'alu_if')

    def end_of_elaboration_phase(self):
        super().end_of_elaboration_phase()
        self.vif.a.value = 0
        self.vif.b.value = 0
        self.vif.cmd.value = 0
        self.vif.valid.value = 0

    async def run_phase(self):
        await super().run_phase()
        await RisingEdge(self.vif.clock)
        if self.vif.reset.value == 1:
            await FallingEdge(self.vif.reset)
        await RisingEdge(self.vif.clock)
        while True:
            tr = await self.seq_item_port.get_next_item()
            rsp = await self.drive(tr)
            self.seq_item_port.item_done(rsp)

    async def drive(self, trans):
        if trans.delay > 0:
            await ClockCycles(self.vif.clock, trans.delay)
        self.vif.valid.value = 1
        self.vif.a.value = trans.a
        self.vif.b.value = trans.b
        self.vif.cmd.value = trans.cmd
        while not self.vif.ready.value:
            await RisingEdge(self.vif.clock)
        self.vif.valid.value = 0
