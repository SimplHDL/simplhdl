# Siemens QuestaSim (`questasim`)

The `questasim` flow runs HDL simulations using Siemens QuestaSim's `qrun` front-end.

## Usage

```bash
simpl questasim [options]
```

## CLI Options

| Option                                         | Description                                                                                      |
| :--------------------------------------------- | :----------------------------------------------------------------------------------------------- |
| `--step {generate,compile,elaborate,simulate}` | Flow step to execute (defaults to full simulation).                                              |
| `-w`, `--wavedump [{wlf,vcd,evcd}]`            | Dump waveforms (defaults to `wlf` when flag is given without value).                             |
| `--gui [{vsim,visualizer}]`                    | Open simulation in GUI (`vsim` or `visualizer`; default controlled by `SIMPLHDL_QUESTASIM_GUI`). |
| `--debug`                                      | Enable full debug visibility (`+acc`, `-debugdb`, `-fsmdebug`).                                  |
| `--clean`                                      | Run `qrun -clean` in the build directory.                                                        |
| `--info`                                       | Print project information.                                                                       |
| `--seed INT`                                   | Random seed for SV and Cocotb (default `1`).                                                     |
| `--random-seed`                                | Generate a random seed.                                                                          |
| `--do COMMAND`                                 | Tcl `.do` file or command string to execute at simulation start.                                 |
| `--timescale STR`                              | Simulator timescale (default `1ns/1ps`).                                                         |
| `--qrun-args ARGS`                             | Extra arguments passed to `qrun`.                                                                |
| `--vlog-args ARGS`                             | Extra arguments passed to `vlog`.                                                                |
| `--vcom-args ARGS`                             | Extra arguments passed to `vcom`.                                                                |
| `--vopt-args ARGS`                             | Extra arguments passed to `vopt`.                                                                |
| `--vsim-args ARGS`                             | Extra arguments passed to `vsim`.                                                                |
