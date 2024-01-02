from pyuvm import ConfigDB, uvm_agent, uvm_active_passive_enum
from .driver import Driver
from .monitor import Monitor
from .sequencer import Sequencer

__ALL__ = ['Agent']


class Agent(uvm_agent):

    monitor: Monitor
    driver: Driver
    sequencer: Sequencer

    def build_phase(self):
        super().build_phase()
        self.monitor = Monitor.create('monitor', self)
        if self.is_active == uvm_active_passive_enum.UVM_ACTIVE:
            self.sequencer = Sequencer.create('sequencer', self)
            self.driver = Driver.create('driver', self)
            ConfigDB().set(None, '*', 'alu_sequencer', self.sequencer)

    def connect_phase(self):
        super().connect_phase()
        if self.is_active == uvm_active_passive_enum.UVM_ACTIVE:
            self.driver.seq_item_port.connect(self.sequencer.seq_item_export)
