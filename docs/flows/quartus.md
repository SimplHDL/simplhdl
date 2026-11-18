# Intel Quartus (`quartus`)

The `quartus` flow implements FPGA designs using Intel Quartus Prime (`quartus_sh` / `quartus`). SimplHDL also provides
`quartus-dse` (Design Space Explorer) and `quartus-export`.

## Usage

```bash
simpl quartus [options]
```

## CLI Options

| Option                                                        | Description                                 |
| :------------------------------------------------------------ | :------------------------------------------ |
| `-s`, `--step {project,elaborate,implement,finalize,compile}` | Flow step to execute (default: `compile`).  |
| `--gui`                                                       | Open project in the Quartus GUI.            |
| `--archive {project,project-service-request,project-source}`  | Archive Quartus project to `<project>.qar`. |

## Working with Intel Quartus IPs

`QuartusGenerator` copies and unpacks Quartus IP and Platform Designer (`.qsys`) files into `_build/<flow>/ips/` and
`_build/<flow>/qsys/` so Quartus and `qsys-generate` never pollute the source tree:

1. **Single `.ip` or `.qsys` file**: Copied to the build folder (rendered with Jinja2 if templated). During simulation,
   `qsys-generate --simulation=VERILOG` is invoked automatically if the `.spd` file is not yet generated.
2. **`.ip` file with generated directory**: Both the `.ip` file and its companion directory are copied to `_build/` with
   MD5 change tracking.
3. **Zipped IP / Qsys archives (`.ip.zip`, `.qsys.zip`)**: Extracted into the build folder on first run or when the MD5
   checksum changes. Archiving generated IP outputs into `.ip.zip` or `.qsys.zip` (optionally tracked with Git LFS)
   keeps repositories clean and speeds up simulation setup.
