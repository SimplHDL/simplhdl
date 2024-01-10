import pyuvm
from test.test import AluTest


@pyuvm.test()
class TestSimple(AluTest):
    def end_of_elaboration_phase(self):
        super().end_of_elaboration_phase()
