# Icarus Verilog (`icarus`)

The `icarus` flow compiles and runs Verilog/SystemVerilog simulations using Icarus Verilog (`iverilog` / `vvp`) and
supports viewing waveforms in GTKWave.

## Usage

```bash
simpl icarus [options]
```

## CLI Options

| Option                                         | Description                                        |
| :--------------------------------------------- | :------------------------------------------------- |
| `--step {generate,compile,elaborate,simulate}` | Flow step to execute (default: `simulate`).        |
| `-w`, `--wavedump [{vcd,fst}]`                 | Dump waveforms in `fst` (default) or `vcd` format. |
| `--gui`                                        | Open waveforms in GTKWave.                         |
| `--debug`                                      | Enable full debug capabilities.                    |
| `--seed INT`                                   | Random seed (default `1`).                         |
| `--random-seed`                                | Generate a random seed.                            |
| `--do COMMAND`                                 | Command to start simulation.                       |
| `--timescale STR`                              | Simulator timescale (default `1ns/1ps`).           |
