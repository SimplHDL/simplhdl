from cocotb.triggers import RisingEdge, FallingEdge
from pyuvm import ConfigDB, uvm_monitor, uvm_analysis_port
from .sequenceitem import SequenceItem

__ALL__ = ['Monitor']


class Monitor(uvm_monitor):

    def build_phase(self):
        super().build_phase()
        self.vif = ConfigDB().get(None, '', 'alu_if')
        self.ap = uvm_analysis_port("ap", self)

    async def run_phase(self):
        await super().run_phase()
        await RisingEdge(self.vif.clock)
        if self.vif.reset.value == 1:
            await FallingEdge(self.vif.reset)
#        while True:
#            await RisingEdge(self.vif.clock)
#            tr = SequenceItem.create("tr")
#            while self.vif.valid.value == 0:
#                await RisingEdge(self.vif.clock)
#            tr.a.value = self.vif.a.value
#            tr.b.value = self.vif.b.value
#            tr.cmd.value = self.vif.cmd.value
#            while self.vif.ready.value == 0:
#                await RisingEdge(self.vif.clock)
#            tr.x = self.vif.x.value
#            self.ap.write(tr)
