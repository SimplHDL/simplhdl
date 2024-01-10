from pyuvm import uvm_env
from clock_vip import Agent as ClockAgent
from alu_vip import Agent as AluAgent


class Env(uvm_env):

    clockAgent: ClockAgent
    aluAgent: AluAgent

    def build_phase(self):
        super().build_phase()
        self.clockAgent = ClockAgent.create('clockAgent', self)
        self.aluAgent = AluAgent.create('aluAgent', self)
