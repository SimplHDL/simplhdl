# Lint & Encrypt Flows

## Lint Flow (`simpl lint`)

The `lint` flow runs static analysis and style checks across HDL and Python verification files in the project:

- **SystemVerilog / Verilog**: Verible (`verible-verilog-lint` / `verible-verilog-format`)
- **VHDL**: VHDL Style Guide (`vsg`)
- **Python**: `flake8` / `black`

```bash
# Lint all project files
simpl lint

# Auto-fix formatting issues in-place
simpl lint --fix

# Lint specific files only
simpl lint -f rtl/alu.sv rtl/add.sv
```

### Linter Configuration Environment Variables

- `SIMPLHDL_VERIBLE_CONFIG`: Path to custom Verible rules file.
- `SIMPLHDL_VSG_CONFIG`: Path to custom VSG configuration file.
- `SIMPLHDL_FLAKE8_CONFIG`: Path to custom Flake8 configuration file.

---

## Encrypt Flow (`simpl encrypt`)

The `encrypt` flow encrypts HDL source files (`HdlFile` with `encrypt=True`, which is the default for `.sv`, `.v`,
`.vh`, `.svh`, `.vhd`) for multi-vendor IP delivery using `encrypt_1735` (Quartus IEEE-1735 encryption tool).

```bash
# Encrypt project HDL files into _build/encrypt/
simpl encrypt

# Encrypt for specific tool vendors
simpl encrypt --vendors mentor synopsys cadence

# Place encrypted files (.svp, .vp, .vhdp) next to source files
simpl encrypt --inplace
```

Supported vendors: `cadence`, `mentor`, `synopsys`, `spyglass`, `dsim`, `veloce`, `dcfcf`.
