# AMD / Xilinx Xsim (`xsim`)

The `xsim` flow compiles (`xvlog`, `xvhdl`), elaborates (`xelab`), and simulates (`xsim`) HDL designs using the Vivado
Xsim simulator.

## Usage

```bash
simpl xsim [options]
```

## CLI Options

| Option                                      | Description                                 |
| :------------------------------------------ | :------------------------------------------ |
| `-s`, `--step {compile,elaborate,simulate}` | Flow step to execute (default: `simulate`). |
| `-w`, `--wave`                              | Dump waveforms.                             |
| `--gui`                                     | Open project in the Xsim GUI.               |
| `--seed SEED`                               | Random seed (default `1`).                  |
| `--random-seed`                             | Generate a random seed.                     |
| `--timescale STR`                           | Simulator timescale (default `1ns/1ps`).    |
| `--xvlog-args ARGS`                         | Extra arguments for `xvlog`.                |
| `--xvhdl-args ARGS`                         | Extra arguments for `xvhdl`.                |
| `--xelab-args ARGS`                         | Extra arguments for `xelab`.                |
| `--xsim-args ARGS`                          | Extra arguments for `xsim`.                 |
