# Aldec Riviera-PRO (`rivierapro`)

The `rivierapro` flow generates Makefiles to compile, elaborate, and simulate HDL designs with Aldec Riviera-PRO.

## Usage

```bash
simpl rivierapro [options]
```

## CLI Options

| Option                                | Description                                         |
| :------------------------------------ | :-------------------------------------------------- |
| `--step {compile,elaborate,simulate}` | Flow step to execute (default: `simulate`).         |
| `-w`, `--wave`                        | Dump waveforms.                                     |
| `--gui`                               | Open simulation in the Riviera-PRO GUI.             |
| `--seed INT`                          | Random seed (default `1`).                          |
| `--random-seed`                       | Generate a random seed.                             |
| `--do COMMAND`                        | `.do` script or command string to start simulation. |
| `--timescale STR`                     | Simulator timescale (default `1ns/1ps`).            |
| `--vlog-args ARGS`                    | Extra arguments for `vlog`.                         |
| `--vcom-args ARGS`                    | Extra arguments for `vcom`.                         |
| `--vopt-args ARGS`                    | Extra arguments for `vopt`.                         |
| `--vmap-args ARGS`                    | Extra arguments for `vmap`.                         |
| `--vsim-args ARGS`                    | Extra arguments for `vsim`.                         |
