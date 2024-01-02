from pyuvm import uvm_monitor

__ALL__ = ['Monitor']


class Monitor(uvm_monitor):

    def build_phase(self):
        super().build_phase()
