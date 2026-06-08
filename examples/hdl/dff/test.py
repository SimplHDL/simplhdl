from __future__ import annotations

import cocotb
from cocotb.triggers import Timer


@cocotb.test()
async def test_dff(dut):
    dut.c.value = 0
    dut.d.value = 0
    await Timer(10, unit="ns")
    assert dut.q.value == 0

    dut.d.value = 1
    await Timer(10, unit="ns")
    assert dut.q.value == 0

    dut.c.value = 1
    await Timer(10, unit="ns")
    assert dut.q.value == 1

    dut.d.value = 0
    await Timer(10, unit="ns")
    assert dut.q.value == 1

    dut.c.value = 0
    await Timer(10, unit="ns")
    assert dut.q.value == 1
