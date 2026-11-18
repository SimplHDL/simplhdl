# Siemens ModelSim (`modelsim`)

The `modelsim` flow generates incremental Makefiles per fileset and runs HDL simulations using Siemens ModelSim (`vlog`,
`vcom`, `vopt`, `vsim`).

## Usage

```bash
simpl modelsim [options]
```

## CLI Options

| Option                                         | Description                                    |
| :--------------------------------------------- | :--------------------------------------------- |
| `--step {generate,compile,elaborate,simulate}` | Flow step to execute (default: `simulate`).    |
| `-w`, `--wavedump [{wlf,vcd,evcd}]`            | Dump waveforms (`wlf`, `vcd`, or `evcd`).      |
| `--gui`                                        | Open simulation in the ModelSim GUI.           |
| `--debug`                                      | Enable full debug capabilities.                |
| `--seed INT`                                   | Random seed (default `1`).                     |
| `--random-seed`                                | Generate a random seed.                        |
| `--do COMMAND`                                 | `.do` file or command string to run in `vsim`. |
| `--timescale STR`                              | Default Verilog timescale (`1ns/1ps`).         |
| `--vlog-args ARGS`                             | Extra arguments for `vlog`.                    |
| `--vcom-args ARGS`                             | Extra arguments for `vcom`.                    |
| `--vopt-args ARGS`                             | Extra arguments for `vopt`.                    |
| `--vmap-args ARGS`                             | Extra arguments for `vmap`.                    |
| `--vsim-args ARGS`                             | Extra arguments for `vsim`.                    |
