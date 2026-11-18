# Synopsys VCS (`vcs`)

The `vcs` flow generates Makefiles and `synopsys_sim.setup` to compile (`vlogan`, `vhdlan`), elaborate (`vcs`), and
simulate (`simv`) designs with Synopsys VCS.

## Usage

```bash
simpl vcs [options]
```

## CLI Options

| Option                                      | Description                                                                                          |
| :------------------------------------------ | :--------------------------------------------------------------------------------------------------- |
| `-s`, `--step {compile,elaborate,simulate}` | Flow step to execute (default: `simulate`).                                                          |
| `-w`, `--wavedump [{vpd,evcd,fsdb}]`        | Dump waveforms (`vpd`, `evcd`, or `fsdb`).                                                           |
| `--gui`                                     | Open simulation in DVE or Verdi (uses Verdi if `VERDI_HOME` or `SNPS_SIM_DEFAULT_GUI=verdi` is set). |
| `--seed SEED`                               | Random seed (default `1`).                                                                           |
| `--random-seed`                             | Generate a random seed.                                                                              |
| `--timescale STR`                           | Simulator timescale (default `1ns/1ps`).                                                             |
| `--vlogan-args ARGS`                        | Extra arguments for `vlogan`.                                                                        |
| `--vhdlan-args ARGS`                        | Extra arguments for `vhdlan`.                                                                        |
| `--vcs-args ARGS`                           | Extra arguments for `vcs`.                                                                           |
| `--simv-args ARGS`                          | Extra arguments for `simv`.                                                                          |
