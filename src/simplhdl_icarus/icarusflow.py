from __future__ import annotations

import logging
import os
import shutil
from typing import TYPE_CHECKING

from simplhdl.plugin import SimulationFlow
from simplhdl.utils import sh

if TYPE_CHECKING:
    from argparse import Namespace
    from pathlib import Path

    from simplhdl import Project

logger = logging.getLogger(__name__)


class IcarusFlow(SimulationFlow):
    """Icarus Verilog simulation flow."""

    @classmethod
    def parse_args(self, subparsers) -> None:
        parser = subparsers.add_parser("icarus", help="Icarus HDL Simulation Flow")
        parser.add_argument(
            "--step",
            action="store",
            choices=["generate", "compile", "elaborate", "simulate"],
            default="simulate",
            help="flow step to run",
        )
        parser.add_argument(
            "-w",
            "--wavedump",
            nargs="?",
            const="vcd",
            choices=["vcd", "evcd"],
            help="Dump waveforms using vcd or evcd format",
        )
        parser.add_argument("--debug", action="store_true", help="Enable full debug capabilities")
        parser.add_argument("--gui", action="store_true", help="Open project in GtkWave GUI")
        parser.add_argument(
            "--seed",
            type=int,
            default=1,
            action="store",
            help="Seed to initialize random generator",
        )
        parser.add_argument(
            "--random-seed",
            action="store_true",
            help="Generate a random seed to initialize random generator",
        )
        parser.add_argument(
            "--do",
            metavar="COMMAND",
            action="store",
            help="Do command to start simulation",
        )
        parser.add_argument(
            "--timescale",
            default="1ns/1ps",
            action="store",
            help="Set the simulator timescale for ModelSim",
        )

    def __init__(self, name, args: Namespace, project: Project, builddir: Path):
        super().__init__(name, args, project, builddir)

    def generate(self):
        super().generate()

    def execute(self, step: str) -> None:
        self.run_hooks("pre")

        if step == "generate":
            return

        if step == "compile":
            sh(["make", "compile"], cwd=self.builddir, output=True)
            return

        if self.args.do:
            if Path(self.args.do).exists():
                os.environ["DO_CMD"] = f"-do {Path(self.args.do).resolve()}"
            else:
                os.environ["DO_CMD"] = f"-do '{self.args.do}'"

        if self.args.gui:
            command = ["make", "gui"]
        else:
            command = ["make", step]
        sh(command, cwd=self.builddir, output=True)
        if step == "simulate":
            self.run_hooks("post")

    def run_hooks(self, name):
        try:
            for command in self.project.hooks[name]:
                logger.info(f"Running {name} hook: {command}")
                sh(command.split(), cwd=self.builddir, output=True)
        except KeyError:
            # NOTE: Continue if no hook is registret
            pass

    def run(self) -> None:
        pass

    def is_tool_setup(self) -> None:
        if (shutil.which("iverilog") is None):
            raise Exception("Icarus is not setup correctly")
