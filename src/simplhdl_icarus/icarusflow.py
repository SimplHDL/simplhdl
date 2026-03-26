from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Any

from jinja2 import Environment, FileSystemLoader, Template

from simplhdl import FileOrder
from simplhdl._compat import resources_files
from simplhdl.plugin import FlowError, FlowTools, SimulationFlow
from simplhdl.project.files import SystemVerilogFile, UsedIn, VerilogFile
from simplhdl.utils import escape, generate_from_template, sh

from .resources.templates import icarus as icarustemplates

if TYPE_CHECKING:
    from argparse import Namespace

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
            const="fst",
            choices=["vcd", "fst"],
            help="Dump waveforms using vcd or fst format",
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
            help="Set the simulator timescale",
        )

    def __init__(self, name, args: Namespace, project: Project, builddir: Path):
        super().__init__(name, args, project, builddir)
        self.templates = icarustemplates
        self.tools.add(FlowTools.ICARUS)

    def get_project_templates(self, environment) -> list[Template]:
        return [
            environment.get_template("Makefile.j2"),
            environment.get_template("simplhdl_iverilog_dump.v.j2"),
            environment.get_template("cmds.f.j2"),
            environment.get_template("sources.mk.j2"),
        ]

    def get_cocotb_templates(self, environment):
        if self.cocotb.enabled:
            return [
                environment.get_template("cocotb.mk.j2"),
            ]
        else:
            return []

    def get_globals(self) -> dict[str, Any]:
        globals = super().get_globals()
        globals["timescale"] = self.args.timescale
        globals["wavedump"] = self.args.wavedump
        globals["files"] = self.project.defaultDesign.files(
            order=FileOrder.COMPILE, type=(VerilogFile, SystemVerilogFile), usedin=UsedIn.SIMULATION
        )
        globals["iverilog_args"] = self.iverilog_args()
        globals["vvp_args"] = self.vvp_args()
        globals["defines"] = [f"+define+{k}={escape(v)}" for k, v in self.project.defines.items()]
        globals["parameters"] = [f"+parameter+{k}={escape(v)}" for k, v in self.project.parameters.items()]
        globals["waves"] = f"-{self.args.wavedump}" if self.args.wavedump else "-none"
        return globals

    def iverilog_args(self) -> str:
        args = ["-g2012"]
        return " ".join(args)

    def vvp_args(self) -> str:
        return ""

    def generate(self):
        templatedir = resources_files(self.templates)
        env = Environment(loader=FileSystemLoader(templatedir), trim_blocks=True)
        for template in self.get_project_templates(env) + self.get_cocotb_templates(env):
            generate_from_template(template, self.builddir, self.get_globals())

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
            # NOTE: Continue if no hook is registered
            pass

    def is_tool_setup(self) -> None:
        if shutil.which("iverilog") is None:
            raise FlowError("Icarus is not setup correctly")
