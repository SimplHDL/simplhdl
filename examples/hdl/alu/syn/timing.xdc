create_clock -name clk -period 10.000 [get_ports clk_i]

set_input_delay 0 [get_ports * -filter {DIRECTION == IN && NAME !~ clk_i}]
set_output_delay 0 [get_ports * -filter {DIRECTION == OUT}]
