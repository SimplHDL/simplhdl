Plugins
=======

There are three kinds of plugins to extend SimplHDL.

1. Parsers
2. Generators
3. Flows


Parsers
-------

Parsers are plugins for parsing project specifications. Parser plugins are
essential for extending SimplHDL to understand specifications from different
projects. Most design teams have there own way for specifying source files,
parameters etc. A few project specifications parsers for simular open source
project are already implemented and ready to use. But if you project uses its
own propiritary format a parser for that is neccesary.

- HDLMake
- FuseSoc
- Edalize


Generators
----------

Generator are plugins that takes an input source and generates output. This
output is added to the generic project model so the output is accessible for
the different simulation and implementation flows. Typpically the output is
Verilog or VHDL, but it can also be complete IPs with constraints and parameters.
One limitation is that Generator cannot be chained together, meaning one
generators output cannot be used as input to a second generator.

- Chisel
- SystemRDL
- IPXact


Flow
----

Flows are plugins that typically add support for a specific EDA tool. It can
however also support multiple EDA tool if such a flow is desired. A few of the
essential EDA tools for simulation and for FPGA development are already
implemented. The lack of ASIC implementation tools is obvious, but they are
harder to come by.

- Vivado
- Quartus
- QuestaSim
- Xsim
- Vcs
- Riviera Pro
